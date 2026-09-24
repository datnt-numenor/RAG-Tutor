from __future__ import annotations

from functools import lru_cache

import structlog
from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.core.config import get_settings

logger = structlog.get_logger()


@lru_cache
def get_rate_limit_redis() -> Redis:
    settings = get_settings()
    return Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


async def enforce_ai_rate_limit(
    user_id: str,
    bucket: str,
    limit: int,
    window_seconds: int,
) -> None:
    redis = get_rate_limit_redis()
    key = f"ragtutor:rate:{bucket}:{user_id}"

    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
    except Exception as exc:
        logger.warning(
            "rate_limit_backend_unavailable",
            bucket=bucket,
            error=exc.__class__.__name__,
        )
        return

    if int(count) > limit:
        ttl = await redis.ttl(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "AI request quota exceeded",
                "retry_after_seconds": max(int(ttl), 1),
                "bucket": bucket,
            },
            headers={"Retry-After": str(max(int(ttl), 1))},
        )
