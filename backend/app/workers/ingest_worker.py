"""Ingest worker — Celery task for document ingestion pipeline."""
from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, name="workers.ingest_document")
def ingest_document(self, document_id: str, version_id: str, job_id: str) -> None:
    """
    Stages: store → extract → chunk → embed → summarize → activate
    TODO: implement IngestService.run() in Milestone 2
    """
    raise NotImplementedError("Implement in Milestone 2")
