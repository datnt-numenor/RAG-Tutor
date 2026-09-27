from app.workers.celery_app import celery_app
from app.workers.roadmap_worker import generate_topic_roadmap
from app.workers.summary_worker import summarize_document


def test_worker_jobs_are_acknowledged_only_after_completion() -> None:
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.result_expires == 3600


def test_progress_worker_is_registered() -> None:
    assert "app.workers.progress_worker" in celery_app.conf.include


def test_roadmap_worker_is_registered() -> None:
    assert "app.workers.roadmap_worker" in celery_app.conf.include


def test_ai_background_tasks_have_bounded_runtime_and_retries() -> None:
    assert generate_topic_roadmap.max_retries == 2
    assert generate_topic_roadmap.soft_time_limit == 180
    assert generate_topic_roadmap.time_limit == 210
    assert summarize_document.max_retries == 2
    assert summarize_document.soft_time_limit == 120
    assert summarize_document.time_limit == 150
