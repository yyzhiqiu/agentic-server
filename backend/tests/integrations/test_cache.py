from __future__ import annotations

import pytest

from app.core.config import settings
from app.integrations.cache import CacheClient


@pytest.mark.asyncio
async def test_cache_client_degrades_without_redis() -> None:
    cache = CacheClient(None)

    assert cache.key("demo") == f"{settings.CACHE_NAMESPACE}:demo"
    assert await cache.get("demo") is None
    assert await cache.set("demo", "value") is False
    assert await cache.delete("demo") is False
