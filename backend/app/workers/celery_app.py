"""Celery app configuration for RAGTutor background jobs."""
from __future__ import annotations

from celery import Celery

from app.core.config import get_settings


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
