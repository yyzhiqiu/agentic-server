from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def create_langfuse_client() -> Any | None:
    if not settings.LANGFUSE_ENABLED:
        return None
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        logger.warning("已启用 Langfuse，但缺少密钥，客户端将被禁用")
        return None
    try:
        from langfuse import Langfuse

        return Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
    except Exception:
        logger.exception("初始化 Langfuse 客户端失败")
        return None


def flush_langfuse(client: Any | None) -> None:
    if client is None:
        return
    try:
        flush = getattr(client, "flush", None)
        if flush:
            flush()
    except Exception:
        logger.warning("刷新 Langfuse 客户端失败", exc_info=True)


def shutdown_langfuse(client: Any | None) -> None:
    if client is None:
        return
    try:
        shutdown = getattr(client, "shutdown", None)
        if shutdown:
            shutdown()
    except Exception:
        logger.warning("关闭 Langfuse 客户端失败", exc_info=True)
