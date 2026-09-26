import asyncio

from app.core.rate_limit import enforce_ai_rate_limit


def test_rate_limit_increment_and_expiry_are_atomic(monkeypatch) -> None:
    class FakeRedis:
        def __init__(self) -> None:
            self.calls: list[tuple] = []

        async def eval(self, *args):
            self.calls.append(args)
            return 1

    redis = FakeRedis()
    monkeypatch.setattr(
        "app.core.rate_limit.get_rate_limit_redis",
        lambda: redis,
    )

    asyncio.run(
        enforce_ai_rate_limit(
            "user-1",
            bucket="quiz",
            limit=5,
            window_seconds=60,
        )
    )

    assert len(redis.calls) == 1
    assert redis.calls[0][1:] == (1, "ragtutor:rate:quiz:user-1", 60)
