"""带命名空间和安全降级能力的缓存辅助逻辑。"""

from __future__ import annotations

from typing import Any

from app.core.config import settings


class CacheClient:
    """对 Redis 客户端做一层轻量命名空间封装。"""

    def __init__(self, redis: Any | None, namespace: str | None = None) -> None:
        self.redis = redis
        self.namespace = namespace or settings.CACHE_NAMESPACE

    def key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    async def get(self, key: str) -> str | None:
        if self.redis is None:
            return None
        return await self.redis.get(self.key(key))

    async def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        if self.redis is None:
            return False
        await self.redis.set(self.key(key), value, ex=ttl)
        return True

    async def delete(self, key: str) -> bool:
        if self.redis is None:
            return False
        return bool(await self.redis.delete(self.key(key)))
