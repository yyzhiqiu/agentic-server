from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.graph.builder import build_graph
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
    app.state.graph = build_graph(app.state.llm)
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
