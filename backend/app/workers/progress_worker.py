"""Background progress snapshot rebuilds."""
from __future__ import annotations

from datetime import datetime
from time import perf_counter

import structlog

from app.services.progress_service import get_progress_service
from app.workers.celery_app import celery_app


logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    max_retries=3,
    name="workers.rebuild_progress_snapshot",
)
def rebuild_progress_snapshot(
    self,
    user_id: str,
    project_id: str,
    occurred_at: str,
) -> None:
    started = perf_counter()
    service = get_progress_service()
    event_time = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))

    try:
        snapshot_date = service._local_date_for(user_id, event_time)
        service.rebuild_snapshot(
            user_id=user_id,
            project_id=project_id,
            snapshot_date=snapshot_date,
        )
        logger.info(
            "progress_snapshot_rebuilt",
            user_id=user_id,
            project_id=project_id,
            snapshot_date=snapshot_date.isoformat(),
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
    except Exception as exc:
        logger.warning(
            "progress_snapshot_rebuild_failed",
            user_id=user_id,
            project_id=project_id,
            error_type=exc.__class__.__name__,
        )
        raise self.retry(exc=exc, countdown=min(2 ** self.request.retries, 30))
