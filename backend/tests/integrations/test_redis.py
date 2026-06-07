from __future__ import annotations

import pytest

from app.integrations import redis as redis_module
from app.integrations.redis import close_redis_client, create_redis_client


@pytest.mark.asyncio
async def test_create_redis_client_returns_none_when_disabled(monkeypatch) -> None:
    monkeypatch.setattr(redis_module.settings, "REDIS_ENABLED", False)
    client = await create_redis_client()
    assert client is None


@pytest.mark.asyncio
async def test_close_redis_client_ignores_none() -> None:
    await close_redis_client(None)
