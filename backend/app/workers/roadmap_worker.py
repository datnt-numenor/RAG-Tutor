"""Background topic-roadmap generation."""
from __future__ import annotations

from time import perf_counter

import structlog

from app.services.topic_roadmap_service import get_topic_roadmap_service
from app.workers.celery_app import celery_app


logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    max_retries=2,
    name="workers.generate_topic_roadmap",
)
def generate_topic_roadmap(self, project_id: str) -> dict:
    started = perf_counter()
    try:
        topics = get_topic_roadmap_service().generate_topics(project_id)
        result = {
            "project_id": project_id,
            "topic_count": len(topics),
        }
        logger.info(
            "roadmap_generation_complete",
            **result,
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
        return result
    except ValueError:
        raise
    except Exception as exc:
        logger.warning(
            "roadmap_generation_failed",
            project_id=project_id,
            error_type=exc.__class__.__name__,
            retry=self.request.retries,
        )
        raise self.retry(exc=exc, countdown=10 * (self.request.retries + 1))
