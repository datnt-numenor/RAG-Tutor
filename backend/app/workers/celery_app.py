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
        # Do not acknowledge jobs before they finish. If a worker process is
        # killed (for example by a memory limit during model startup), Celery
        # can put the job back on the queue instead of leaving the database job
        # permanently stuck in "queued".
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
    )
    return app


celery_app = make_celery()
