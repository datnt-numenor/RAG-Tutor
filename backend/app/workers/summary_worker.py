"""Background document summary task.

Summary generation is intentionally outside the critical ingest path so a
document becomes searchable as soon as chunks and embeddings are persisted.
"""
from __future__ import annotations

from time import perf_counter

import structlog

from app.core.database import get_supabase_admin
from app.services.document_summary_service import get_document_summary_service
from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="workers.summarize_document")
def summarize_document(version_id: str) -> None:
    db = get_supabase_admin()
    started = perf_counter()

    version_res = (
        db.table("document_versions")
        .select("id, original_filename, status")
        .eq("id", version_id)
        .maybe_single()
        .execute()
    )
    version = version_res.data
    if not version or version.get("status") != "ready":
        return

    db.table("document_versions").update(
        {"summary_status": "processing"}
    ).eq("id", version_id).execute()

    try:
        chunks_res = (
            db.table("chunks")
            .select("content, section_title, chunk_index")
            .eq("document_version_id", version_id)
            .order("chunk_index")
            .execute()
        )

        summary = get_document_summary_service().summarize(
            filename=version["original_filename"],
            chunks=chunks_res.data or [],
        )

        db.table("document_versions").update(
            {
                "summary": summary,
                "summary_status": "ready",
            }
        ).eq("id", version_id).execute()

        logger.info(
            "document_summary_complete",
            version_id=version_id,
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
    except Exception as exc:
        db.table("document_versions").update(
            {
                "summary": None,
                "summary_status": "error",
            }
        ).eq("id", version_id).execute()

        logger.warning(
            "document_summary_failed",
            version_id=version_id,
            error=exc.__class__.__name__,
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
