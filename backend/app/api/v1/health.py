from __future__ import annotations

import inspect
from typing import Any

from fastapi import APIRouter, Request

from app.common.responses import success_response
from app.core.config import settings
from app.db.session import check_database_connection
from app.integrations.object_storage import check_object_storage_availability

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return success_response({"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV})


async def _redis_available(redis: Any | None) -> bool | None:
    if not settings.REDIS_ENABLED:
        return None
    if redis is None:
        return False

    ping = getattr(redis, "ping", None)
    if ping is None:
        return True

    try:
        result = ping()
        if inspect.isawaitable(result):
            result = await result
        return bool(result)
    except Exception:
        return False


@router.get("/ready")
async def ready(request: Request) -> dict:
    redis = getattr(request.app.state, "redis", None)
    graph = getattr(request.app.state, "graph", None)
    object_storage = getattr(request.app.state, "object_storage", None)
    database_available = await check_database_connection() if settings.DATABASE_URL else False
    redis_available = await _redis_available(redis)
    graph_available = graph is not None
    object_storage_available = await check_object_storage_availability(object_storage)
    status = (
        "ready"
        if database_available
        and graph_available
        and (redis_available is not False)
        and (object_storage_available is not False)
        else "degraded"
    )
    return success_response(
        {
            "status": status,
            "database": {
                "configured": bool(settings.DATABASE_URL),
                "available": database_available,
            },
            "redis": {
                "enabled": settings.REDIS_ENABLED,
                "available": redis_available,
            },
            "graph": {"available": graph_available},
            "object_storage": {
                "backend": settings.OBJECT_STORAGE_BACKEND,
                "configured": settings.OBJECT_STORAGE_BACKEND != "disabled",
                "available": object_storage_available,
            },
        }
    )
