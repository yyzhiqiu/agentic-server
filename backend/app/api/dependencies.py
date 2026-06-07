"""后端资源的 FastAPI 依赖提供器。

本模块负责把 lifespan 管理的应用级资源和请求级输入适配为 Service 层依赖。
它不实现业务逻辑，也不能在请求处理期间重新构建 LangGraph、HTTP Client
等应用级共享资源。
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated, Any

import httpx
from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.audit.writer import DatabaseAuditWriter
from app.core.security import CurrentUser, user_from_api_key
from app.db.repositories.agent_run_repo import AgentRunRepository
from app.db.repositories.conversation_repo import ConversationRepository
from app.db.repositories.document_repo import DocumentRepository
from app.db.repositories.file_repo import FileRepository
from app.db.repositories.message_repo import MessageRepository
from app.db.repositories.tool_call_repo import ToolCallRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_db_session as db_session_dependency
from app.graph.default import DEFAULT_AGENT_ID
from app.graph.types import AgentDefinition, AgentRegistry
from app.integrations.object_storage import ObjectStorage
from app.services.agent_service import AgentService
from app.services.agent_run_service import AgentRunService
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.file_service import FileService
from app.services.graph_runner import GraphRunner
from app.services.message_service import MessageService
from app.services.tool_call_service import ToolCallService
from app.services.user_service import UserService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """从共享的会话工厂中产出异步数据库会话。"""

    async for session in db_session_dependency():
        yield session


def get_redis(request: Request) -> Any | None:
    """返回保存在 ``app.state`` 上的 Redis 客户端。

    当 Redis 被关闭，或应用启动阶段初始化失败时，这里可能返回 ``None``。
    """

    return getattr(request.app.state, "redis", None)


def get_agent_registry(request: Request) -> AgentRegistry:
    """返回启动阶段构建并缓存在 ``app.state`` 上的 Agent 注册表。"""

    return request.app.state.agent_registry


def get_agent_service(
    agent_registry: AgentRegistry = Depends(get_agent_registry),
) -> AgentService:
    """基于启动期缓存的注册表构建轻量 Agent 服务。"""

    return AgentService(agent_registry=agent_registry)


def get_agent_definition(
    agent_id: str = DEFAULT_AGENT_ID,
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentDefinition:
    """解析当前请求要使用的 Agent 定义。

    当路由中不存在 ``agent_id`` 路径参数时，自动回落到默认 ``chat_agent``。
    """

    return agent_service.get_definition(agent_id)


def get_graph(
    agent_definition: AgentDefinition = Depends(get_agent_definition),
) -> Any:
    """返回当前请求对应的已编译 LangGraph 实例。

    对于兼容路由，这里会返回默认 ``chat_agent`` 的 graph；
    对于 ``/v1/agents/{agent_id}/...`` 路由，则返回指定 Agent 的 graph。
    """

    return agent_definition.graph


def get_llm(request: Request) -> Any | None:
    """返回由 lifespan 管理的 LLM 实例；如果未配置则返回空。"""

    return getattr(request.app.state, "llm", None)


def get_http_client(request: Request) -> httpx.AsyncClient:
    """返回 ``app.state`` 中共享的异步 HTTP 客户端。"""

    return request.app.state.http_client


def get_object_storage(request: Request) -> ObjectStorage:
    """返回 ``app.state`` 中已配置的对象存储后端。"""

    return request.app.state.object_storage


def get_graph_runner(
    agent_definition: AgentDefinition = Depends(get_agent_definition),
) -> GraphRunner:
    """基于启动期初始化的资源构建请求级 ``GraphRunner``。"""

    return GraphRunner(
        agent_definition.graph,
        agent_id=agent_definition.metadata.agent_id,
    )


async def get_user_service(
    session: AsyncSession = Depends(get_db_session),
) -> UserService:
    """构建当前写接口使用的轻量用户服务。"""

    return UserService(
        session=session,
        user_repository=UserRepository(session),
    )


async def get_chat_service(
    session: AsyncSession = Depends(get_db_session),
    graph_runner: GraphRunner = Depends(get_graph_runner),
    agent_definition: AgentDefinition = Depends(get_agent_definition),
    user_service: UserService = Depends(get_user_service),
) -> ChatService:
    """为当前请求构建聊天服务。"""

    return ChatService(
        session=session,
        graph_runner=graph_runner,
        conversation_repository=ConversationRepository(session),
        message_repository=MessageRepository(session),
        agent_run_repository=AgentRunRepository(session),
        user_service=user_service,
        agent_id=agent_definition.metadata.agent_id,
        tool_call_service=ToolCallService(
            tool_call_repository=ToolCallRepository(session),
        ),
        audit_service=AuditService(
            writer=DatabaseAuditWriter(session),
        ),
    )


async def get_conversation_service(
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> ConversationService:
    """构建带 Repository 和事务支持的会话服务。"""

    return ConversationService(
        session=session,
        conversation_repository=ConversationRepository(session),
        message_repository=MessageRepository(session),
        user_service=user_service,
        audit_service=AuditService(
            writer=DatabaseAuditWriter(session),
        ),
    )


async def get_file_service(
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
    object_storage: ObjectStorage = Depends(get_object_storage),
) -> FileService:
    """构建带 Repository 和事务支持的文件服务。"""

    return FileService(
        session=session,
        file_repository=FileRepository(session),
        document_repository=DocumentRepository(session),
        user_service=user_service,
        object_storage=object_storage,
        audit_service=AuditService(
            writer=DatabaseAuditWriter(session),
        ),
    )


async def get_message_service(
    session: AsyncSession = Depends(get_db_session),
) -> MessageService:
    """构建面向用户范围读取接口的消息服务。"""

    return MessageService(
        session=session,
        conversation_repository=ConversationRepository(session),
        message_repository=MessageRepository(session),
    )


async def get_agent_run_service(
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> AgentRunService:
    """构建带 Repository 和事务支持的 Agent 运行服务。"""

    return AgentRunService(
        session=session,
        agent_run_repository=AgentRunRepository(session),
        user_service=user_service,
        tool_call_service=ToolCallService(
            tool_call_repository=ToolCallRepository(session),
        ),
        audit_service=AuditService(
            writer=DatabaseAuditWriter(session),
        ),
    )


async def get_current_user(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> CurrentUser:
    """根据基于 API Key 的认证信息解析当前用户。"""

    return user_from_api_key(x_api_key)
