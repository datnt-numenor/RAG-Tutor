"""Ingest worker — Celery task for document ingestion pipeline."""
from __future__ import annotations

from app.services.ingest_service import IngestService
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, max_retries=2, name="workers.ingest_document")
def ingest_document(self, document_id: str, version_id: str, job_id: str) -> None:
    try:
        IngestService().run(
            document_id=document_id,
            version_id=version_id,
            job_id=job_id,
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=min(60, 5 * (2 ** self.request.retries)))
