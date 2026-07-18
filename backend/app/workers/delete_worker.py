"""Delete worker — Celery task for permanent document deletion pipeline."""
from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(bind=True, max_retries=5, name="workers.delete_document")
def delete_document(self, document_id: str, job_id: str) -> None:
    """
    Stages: exclude → cancel_ingest → storage → derived_data → document → done
    Idempotent: each stage checks if already done before proceeding.
    TODO: implement in Milestone 2
    """
    raise NotImplementedError("Implement in Milestone 2")
