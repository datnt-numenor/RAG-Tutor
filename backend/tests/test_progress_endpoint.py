import asyncio
from threading import Barrier
from types import SimpleNamespace

from app.api.v1.endpoints.progress import progress_overview
from app.core.auth import AuthenticatedUser


class FakeQuery:
    def __init__(self, table: str, barrier: Barrier):
        self.table = table
        self.barrier = barrier

    def __getattr__(self, name):
        def chain(*args, **kwargs):
            return self

        return chain

    def execute(self):
        if self.table == "project_members":
            return SimpleNamespace(data=[{
                "project_id": "project-1",
                "projects": {"id": "project-1", "name": "Project"},
            }])
        self.barrier.wait(timeout=1)
        return SimpleNamespace(data=[])


class FakeDatabase:
    def __init__(self):
        self.barrier = Barrier(5)

    def table(self, name: str):
        return FakeQuery(name, self.barrier)


def test_progress_overview_runs_independent_queries_concurrently(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.progress.get_supabase_admin",
        FakeDatabase,
    )
    user = AuthenticatedUser("user-1", "user@example.test", "token")

    result = asyncio.run(progress_overview(user))

    assert result["projects"] == 1
    assert result["project_breakdown"][0]["documents"] == 0
