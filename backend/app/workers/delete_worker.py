"""Delete worker — Celery task for permanent document deletion pipeline."""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.database import get_supabase_admin
from app.workers.celery_app import celery_app


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mark_deleted_chat_citations(
    db,
    project_id: str,
    document_id: str,
) -> None:
    """Keep chat history but mark citations whose source document is gone."""
    sessions = (
        db.table("chat_sessions")
        .select("id")
        .eq("project_id", project_id)
        .execute()
    ).data
    session_ids = [row["id"] for row in sessions]
    if not session_ids:
        return

    messages = (
        db.table("chat_messages")
        .select("id, citations")
        .in_("session_id", session_ids)
        .not_.is_("citations", "null")
        .execute()
    ).data

    for message in messages:
        citations = message.get("citations")
        if not isinstance(citations, list):
            continue

        changed = False
        updated_citations = []
        for citation in citations:
            if not isinstance(citation, dict):
                updated_citations.append(citation)
                continue

            updated = dict(citation)
            if str(updated.get("document_id") or "") == document_id:
                updated["source_deleted"] = True
                # Preserve filename/page snapshot, but remove live identifiers
                # that can no longer be opened after permanent deletion.
                updated["chunk_id"] = None
                updated["document_version_id"] = None
                changed = True
            updated_citations.append(updated)

        if changed:
            db.table("chat_messages").update({
                "citations": updated_citations,
            }).eq("id", message["id"]).execute()


def _capture_impacted_derived_ids(
    db,
    document_id: str,
) -> tuple[list[str], set[str], set[str]]:
    """Capture chunk/question/topic IDs before chunk cascades remove source links."""
    chunks = (
        db.table("chunks")
        .select("id")
        .eq("document_id", document_id)
        .execute()
    ).data
    chunk_ids = [row["id"] for row in chunks]
    if not chunk_ids:
        return [], set(), set()

    question_links = (
        db.table("question_sources")
        .select("question_id")
        .in_("chunk_id", chunk_ids)
        .execute()
    ).data
    topic_links = (
        db.table("topic_sources")
        .select("topic_id")
        .in_("chunk_id", chunk_ids)
        .execute()
    ).data

    return (
        chunk_ids,
        {row["question_id"] for row in question_links},
        {row["topic_id"] for row in topic_links},
    )


def _retire_orphaned_questions(db, question_ids: set[str]) -> None:
    for question_id in question_ids:
        remaining = (
            db.table("question_sources")
            .select("chunk_id", count="exact")
            .eq("question_id", question_id)
            .limit(1)
            .execute()
        )
        if (remaining.count or 0) == 0:
            db.table("questions").update({
                "status": "retired",
            }).eq("id", question_id).execute()


def _remove_orphaned_topics(db, topic_ids: set[str]) -> None:
    for topic_id in topic_ids:
        remaining = (
            db.table("topic_sources")
            .select("chunk_id", count="exact")
            .eq("topic_id", topic_id)
            .limit(1)
            .execute()
        )
        if (remaining.count or 0) == 0:
            # Schedules retain their history because topic_id is ON DELETE SET NULL.
            db.table("topics").delete().eq("id", topic_id).execute()


@celery_app.task(bind=True, max_retries=4, name="workers.delete_document")
def delete_document(self, document_id: str, job_id: str) -> None:
    """
    Idempotent stages:
    exclude -> cancel_ingest -> storage -> derived_data -> document -> done

    Historical chat/quiz records are preserved:
    - chat citations become source_deleted snapshots;
    - quiz_attempt snapshots remain untouched;
    - questions with no remaining source chunks become retired.
    """
    db = get_supabase_admin()

    try:
        job_res = (
            db.table("document_jobs")
            .select("attempt_count, max_attempts, project_id")
            .eq("id", job_id)
            .single()
            .execute()
        )
        job = job_res.data
        project_id = job["project_id"]
        next_attempt = int(job.get("attempt_count") or 0) + 1
        max_attempts = int(job.get("max_attempts") or 5)

        if next_attempt > max_attempts:
            raise RuntimeError(
                f"Delete job exceeded max attempts ({max_attempts})"
            )

        db.table("document_jobs").update({
            "status": "running",
            "stage": "exclude",
            "attempt_count": next_attempt,
            "progress_current": 1,
            "progress_total": 5,
            "last_error": None,
            "updated_at": _now(),
        }).eq("id", job_id).execute()

        document_res = (
            db.table("documents")
            .select("id, project_id, status")
            .eq("id", document_id)
            .maybe_single()
            .execute()
        )

        if not document_res.data:
            db.table("document_jobs").update({
                "status": "succeeded",
                "stage": "done",
                "progress_current": 5,
                "progress_total": 5,
                "updated_at": _now(),
            }).eq("id", job_id).execute()
            return

        db.table("documents").update({
            "status": "deleting",
            "active_version_id": None,
            "updated_at": _now(),
        }).eq("id", document_id).execute()

        db.table("document_jobs").update({
            "stage": "cancel_ingest",
            "progress_current": 2,
            "updated_at": _now(),
        }).eq("id", job_id).execute()

        db.table("document_jobs").update({
            "status": "cancelled",
            "last_error": "Cancelled because document deletion was requested",
            "updated_at": _now(),
        }).eq("document_id", document_id).eq(
            "job_type", "ingest"
        ).in_("status", ["queued", "running"]).execute()

        versions = (
            db.table("document_versions")
            .select("storage_path")
            .eq("document_id", document_id)
            .execute()
        )

        db.table("document_jobs").update({
            "stage": "storage",
            "progress_current": 3,
            "updated_at": _now(),
        }).eq("id", job_id).execute()

        paths = [
            row["storage_path"]
            for row in versions.data
            if row.get("storage_path")
        ]
        if paths:
            db.storage.from_("documents").remove(paths)

        db.table("document_jobs").update({
            "stage": "derived_data",
            "progress_current": 4,
            "updated_at": _now(),
        }).eq("id", job_id).execute()

        _mark_deleted_chat_citations(db, project_id, document_id)
        _, impacted_question_ids, impacted_topic_ids = (
            _capture_impacted_derived_ids(db, document_id)
        )

        # Explicitly removing vector rows releases storage before deleting
        # document/version records. Source-link FKs cascade from chunks.
        db.table("chunks").delete().eq("document_id", document_id).execute()

        _retire_orphaned_questions(db, impacted_question_ids)
        _remove_orphaned_topics(db, impacted_topic_ids)

        db.table("document_jobs").update({
            "stage": "document",
            "progress_current": 5,
            "updated_at": _now(),
        }).eq("id", job_id).execute()

        db.table("documents").delete().eq("id", document_id).execute()

        db.table("document_jobs").update({
            "status": "succeeded",
            "stage": "done",
            "progress_current": 5,
            "progress_total": 5,
            "last_error": None,
            "updated_at": _now(),
        }).eq("id", job_id).execute()

    except Exception as exc:
        db.table("document_jobs").update({
            "status": "failed",
            "last_error": str(exc)[:2000],
            "updated_at": _now(),
        }).eq("id", job_id).execute()

        if self.request.retries < self.max_retries:
            raise self.retry(
                exc=exc,
                countdown=min(120, 5 * (2 ** self.request.retries)),
            )
        raise
