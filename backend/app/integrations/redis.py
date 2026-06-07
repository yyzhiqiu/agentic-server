from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


async def create_redis_client() -> Any | None:
    if not settings.REDIS_ENABLED:
        return None
    try:
        from redis.asyncio import Redis

        return Redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        logger.exception("Failed to initialize Redis client")
        return None


async def close_redis_client(client: Any | None) -> None:
    if client is None:
        return
    close = getattr(client, "aclose", None) or getattr(client, "close", None)
    if close is not None:
        result = close()
        if hasattr(result, "__await__"):
            await result
