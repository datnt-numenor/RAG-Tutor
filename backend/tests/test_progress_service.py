from datetime import datetime, timezone

from app.services.progress_service import ProgressService


def test_record_event_deferred_dispatches_snapshot_rebuild(monkeypatch):
    service = ProgressService(supabase=object())
    occurred_at = datetime(2026, 9, 26, 8, 30, tzinfo=timezone.utc)
    dispatched: list[tuple] = []

    monkeypatch.setattr(
        service,
        "record_event",
        lambda **kwargs: {"occurred_at": occurred_at.isoformat()},
    )
    monkeypatch.setattr(
        "app.workers.progress_worker.rebuild_progress_snapshot.delay",
        lambda *args: dispatched.append(args),
    )

    service.record_event_deferred(
        user_id="user",
        project_id="project",
        event_type="chat_question",
        occurred_at=occurred_at,
    )

    assert dispatched == [
        ("user", "project", occurred_at.isoformat()),
    ]


def test_record_event_deferred_rebuilds_inline_if_dispatch_fails(monkeypatch):
    service = ProgressService(supabase=object())
    occurred_at = datetime(2026, 9, 26, 8, 30, tzinfo=timezone.utc)
    rebuilt: list[dict] = []

    monkeypatch.setattr(
        service,
        "record_event",
        lambda **kwargs: {"occurred_at": occurred_at.isoformat()},
    )
    monkeypatch.setattr(
        "app.workers.progress_worker.rebuild_progress_snapshot.delay",
        lambda *args: (_ for _ in ()).throw(RuntimeError("redis unavailable")),
    )
    monkeypatch.setattr(
        service,
        "_local_date_for",
        lambda user_id, value: value.date(),
    )
    monkeypatch.setattr(
        service,
        "rebuild_snapshot",
        lambda **kwargs: rebuilt.append(kwargs),
    )

    service.record_event_deferred(
        user_id="user",
        project_id="project",
        event_type="chat_question",
        occurred_at=occurred_at,
    )

    assert rebuilt == [{
        "user_id": "user",
        "project_id": "project",
        "snapshot_date": occurred_at.date(),
    }]
