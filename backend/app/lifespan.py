"""FastAPI 应用生命周期资源管理模块。

本模块负责在启动阶段初始化应用级共享资源，包括 LLM、Redis、HTTP Client、
对象存储、Langfuse，以及多 Agent graph 注册表。它不处理任何请求级业务逻辑。
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.graph.default import DEFAULT_AGENT_ID
from app.graph.registry import build_agent_registry
from app.graph.checkpoint import create_checkpointer
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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("=================启动应用资源=================")
    app.state.redis = await create_redis_client()
    app.state.http_client = create_http_client()
    app.state.object_storage = create_object_storage()
    app.state.llm = create_llm()
    app.state.agent_checkpointer = create_checkpointer()
    app.state.agent_store = create_store()
    app.state.agent_registry = build_agent_registry(
        llm=app.state.llm,
        checkpointer=app.state.agent_checkpointer,
        store=app.state.agent_store,
    )
    app.state.graph = app.state.agent_registry[DEFAULT_AGENT_ID].graph

    print(app.state.graph.get_graph().draw_mermaid())

    app.state.langfuse = create_langfuse_client()
    try:
        yield
    finally:
        logger.info("=================关闭应用资源=================")
        await close_redis_client(getattr(app.state, "redis", None))
        await close_http_client(getattr(app.state, "http_client", None))
        langfuse_client = getattr(app.state, "langfuse", None)
        flush_langfuse(langfuse_client)
        shutdown_langfuse(langfuse_client)
