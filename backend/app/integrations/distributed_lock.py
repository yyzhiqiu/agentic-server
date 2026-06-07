from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator


class DistributedLock:
    def __init__(self, redis: Any | None) -> None:
        self.redis = redis

    @asynccontextmanager
    async def acquire(self, key: str, ttl: int = 30) -> AsyncIterator[bool]:
        if self.redis is None:
            yield True
            return
        lock_key = f"lock:{key}"
        acquired = bool(await self.redis.set(lock_key, "1", ex=ttl, nx=True))
        try:
            yield acquired
        finally:
            if acquired:
                await self.redis.delete(lock_key)
