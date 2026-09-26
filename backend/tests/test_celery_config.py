from app.workers.celery_app import celery_app


def test_worker_jobs_are_acknowledged_only_after_completion() -> None:
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_progress_worker_is_registered() -> None:
    assert "app.workers.progress_worker" in celery_app.conf.include
