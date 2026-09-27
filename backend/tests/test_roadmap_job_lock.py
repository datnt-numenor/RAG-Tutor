import asyncio

from app.api.v1.endpoints.topics import (
    _claim_roadmap_job,
    _release_roadmap_job,
)


class FakeRedis:
    def __init__(self, existing: str | None = None):
        self.existing = existing
        self.eval_calls = []

    async def set(self, key, value, **kwargs):
        if self.existing is not None:
            return False
        self.existing = value
        return True

    async def get(self, key):
        return self.existing

    async def eval(self, *args):
        self.eval_calls.append(args)
        return 1


def test_claim_reuses_existing_roadmap_job(monkeypatch) -> None:
    redis = FakeRedis(existing="existing-job")
    monkeypatch.setattr(
        "app.api.v1.endpoints.topics.get_rate_limit_redis",
        lambda: redis,
    )

    job_id, should_dispatch = asyncio.run(_claim_roadmap_job("project-1"))

    assert job_id == "existing-job"
    assert should_dispatch is False


def test_release_only_deletes_matching_roadmap_job(monkeypatch) -> None:
    redis = FakeRedis(existing="job-1")
    monkeypatch.setattr(
        "app.api.v1.endpoints.topics.get_rate_limit_redis",
        lambda: redis,
    )

    asyncio.run(_release_roadmap_job("project-1", "job-1"))

    assert redis.eval_calls[0][1:] == (
        1,
        "ragtutor:roadmap-job:project-1",
        "job-1",
    )
