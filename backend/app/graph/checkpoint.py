"""LangGraph checkpoint 资源初始化模块。

该模块负责在应用启动期初始化 graph 级 checkpoint 资源，并统一处理
PostgreSQL 持久化、连接串兼容转换与测试环境下的内存降级策略。
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import AsyncExitStack
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)
FAILED_CHECKPOINT_URLS: set[str] = set()


def _normalize_checkpoint_url(value: str | None) -> str | None:
    """把不同驱动方言的 PostgreSQL URL 归一化为 psycopg 可用格式。"""

    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    replacements = {
        "postgresql+asyncpg://": "postgresql://",
        "postgresql+psycopg://": "postgresql://",
    }
    for source, target in replacements.items():
        if normalized.startswith(source):
            return normalized.replace(source, target, 1)

    if normalized.startswith("postgresql://") or normalized.startswith("postgres://"):
        return normalized
    return None


def _resolve_checkpoint_url() -> str | None:
    """解析当前配置下实际要使用的 checkpoint 连接串。"""

    configured_url = settings.AGENT_CHECKPOINT_URL or settings.DATABASE_URL
    return _normalize_checkpoint_url(configured_url)


def _create_memory_checkpointer() -> Any:
    """创建进程内内存 checkpoint。

    这里的内存实现主要用于测试环境或本地依赖暂不可用时的优雅降级。
    它不能跨进程持久化，但仍能支持当前进程内的暂停后恢复。
    """

    from langgraph.checkpoint.memory import InMemorySaver

    return InMemorySaver()


async def create_checkpointer(exit_stack: AsyncExitStack) -> Any | None:
    """创建 LangGraph checkpoint 实现。

    优先尝试使用 PostgreSQL 持久化 saver；若初始化失败，则自动降级到
    进程内内存 saver，避免应用启动和测试环境被外部依赖强绑定。
    """

    if not settings.AGENT_CHECKPOINT_ENABLED:
        logger.info("已关闭 Agent checkpoint 初始化")
        return None

    checkpoint_url = _resolve_checkpoint_url()
    if checkpoint_url is None:
        logger.warning("未解析到可用的 PostgreSQL checkpoint 连接串，将降级为内存 checkpoint")
        return _create_memory_checkpointer()
    if checkpoint_url in FAILED_CHECKPOINT_URLS:
        logger.warning("当前进程内已标记 checkpoint 连接不可用，将直接降级为内存 checkpoint")
        return _create_memory_checkpointer()

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        saver = await asyncio.wait_for(
            exit_stack.enter_async_context(AsyncPostgresSaver.from_conn_string(checkpoint_url)),
            timeout=settings.AGENT_CHECKPOINT_CONNECT_TIMEOUT_SECONDS,
        )
        await asyncio.wait_for(
            saver.setup(),
            timeout=settings.AGENT_CHECKPOINT_CONNECT_TIMEOUT_SECONDS,
        )
        logger.info("已启用 PostgreSQL 持久化 checkpoint")
        return saver
    except Exception:
        FAILED_CHECKPOINT_URLS.add(checkpoint_url)
        logger.warning("初始化 PostgreSQL checkpoint 失败，将降级为内存 checkpoint", exc_info=True)
        return _create_memory_checkpointer()
