"""Celery app configuration for RAGTutor background jobs."""
from __future__ import annotations

import structlog
from celery import Celery
from celery.signals import worker_ready

from app.core.config import get_settings

logger = structlog.get_logger()


def make_celery() -> Celery:
    settings = get_settings()
    app = Celery(
        "ragtutor",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=[
            "app.workers.ingest_worker",
            "app.workers.delete_worker",
            "app.workers.summary_worker",
        ],
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="Asia/Ho_Chi_Minh",
        enable_utc=True,
        task_track_started=True,
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
    )
    return app


celery_app = make_celery()


@worker_ready.connect
def preload_embedding_model(**_: object) -> None:
    """Warm the embedding model once when the worker starts."""
    try:
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()
        logger.info(
            "embedding_model_preloaded",
            model=service.model_name,
            batch_size=service.batch_size,
        )
    except Exception as exc:
        # Do not prevent the worker from starting; a later ingest task can retry
        # the model load and surface the actual failure through the job status.
        logger.warning(
            "embedding_model_preload_failed",
            error=exc.__class__.__name__,
        )
