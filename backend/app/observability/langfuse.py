from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def create_langfuse_client() -> Any | None:
    if not settings.LANGFUSE_ENABLED:
        return None
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        logger.warning("Langfuse is enabled but keys are missing; disabling client")
        return None
    try:
        from langfuse import Langfuse

        return Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
    except Exception:
        logger.exception("Failed to initialize Langfuse client")
        return None


def flush_langfuse(client: Any | None) -> None:
    if client is None:
        return
    try:
        flush = getattr(client, "flush", None)
        if flush:
            flush()
    except Exception:
        logger.warning("Failed to flush Langfuse client", exc_info=True)


def shutdown_langfuse(client: Any | None) -> None:
    if client is None:
        return
    try:
        shutdown = getattr(client, "shutdown", None)
        if shutdown:
            shutdown()
    except Exception:
        logger.warning("Failed to shutdown Langfuse client", exc_info=True)
