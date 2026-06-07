"""FastAPI 应用生命周期资源管理模块。

本模块负责在启动阶段初始化应用级共享资源，包括 LLM、Redis、HTTP Client、
对象存储、Langfuse、多 Agent graph 注册表、checkpoint 与运行时任务注册表。
它不处理任何请求级业务逻辑。
"""

from __future__ import annotations

import logging
from contextlib import AsyncExitStack, asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.graph.checkpoint import create_checkpointer
from app.graph.default import DEFAULT_AGENT_ID
from app.graph.registry import build_agent_registry
from app.graph.store import create_store
from app.integrations.http_client import close_http_client, create_http_client
from app.integrations.object_storage import create_object_storage
from app.integrations.redis import close_redis_client, create_redis_client
from app.llms.factory import create_llm
from app.observability.langfuse import (
    create_langfuse_client,
    flush_langfuse,
    shutdown_langfuse,
)
from app.services.agent_runtime_registry import AgentRuntimeRegistry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """统一管理应用级共享资源的启动与关闭。"""

    logger.info("=================正在启动应用资源=================")
    async with AsyncExitStack() as exit_stack:
        app.state.redis = await create_redis_client()
        app.state.http_client = create_http_client()
        app.state.object_storage = create_object_storage()
        app.state.llm = create_llm()
        app.state.langfuse = create_langfuse_client()
        app.state.agent_runtime_registry = AgentRuntimeRegistry()
        app.state.agent_checkpointer = await create_checkpointer(exit_stack)
        app.state.agent_store = create_store()
        app.state.agent_registry = build_agent_registry(
            llm=app.state.llm,
            checkpointer=app.state.agent_checkpointer,
            store=app.state.agent_store,
        )
        app.state.graph = app.state.agent_registry[DEFAULT_AGENT_ID].graph

        logger.info("=================已成功启动应用资源================")
        try:
            yield
        finally:
            logger.info("=================关闭应用资源=================")
            runtime_registry = getattr(app.state, "agent_runtime_registry", None)
            if runtime_registry is not None:
                await runtime_registry.shutdown()
            await close_redis_client(getattr(app.state, "redis", None))
            await close_http_client(getattr(app.state, "http_client", None))
            langfuse_client = getattr(app.state, "langfuse", None)
            flush_langfuse(langfuse_client)
            shutdown_langfuse(langfuse_client)
