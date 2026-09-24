"""Delete worker — Celery task for permanent document deletion pipeline."""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.database import get_supabase_admin
from app.workers.celery_app import celery_app


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@celery_app.task(bind=True, max_retries=4, name="workers.delete_document")
def delete_document(self, document_id: str, job_id: str) -> None:
    """
    Idempotent stages:
    exclude -> cancel_ingest -> storage -> derived_data -> document -> done
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

        # If a retry arrives after the document row is already gone,
        # deletion is already effectively complete.
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

        # chunks are ON DELETE CASCADE through document/document_version FKs.
        # Explicit delete makes the stage idempotent and releases vector data
        # before the document row is removed.
        db.table("chunks").delete().eq("document_id", document_id).execute()

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
