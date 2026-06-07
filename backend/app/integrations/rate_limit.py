from __future__ import annotations

from typing import Any


class RateLimiter:
    def __init__(self, redis: Any | None) -> None:
        self.redis = redis

    async def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        if self.redis is None:
            return True
        redis_key = f"rate_limit:{key}"
        count = await self.redis.incr(redis_key)
        if count == 1:
            await self.redis.expire(redis_key, window_seconds)
        return count <= limit
