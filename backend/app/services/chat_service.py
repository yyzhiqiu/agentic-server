"""聊天业务编排服务。

本服务围绕共享的 LangGraph 运行器协调同步与流式聊天流程，负责会话解析、
消息去重、Agent 运行生命周期持久化以及审计记录，而图执行本身仍由
``GraphRunner`` 负责。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.enums import AuditAction, AuditResult
from app.audit.schemas import AuditEvent
from app.audit.service import AuditService
from app.common.context import get_trace_id
from app.common.error_codes import ErrorCode
from app.common.exceptions import AppException
from app.core.security import CurrentUser
from app.db.models.agent_run import AgentRun
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.repositories.agent_run_repo import AgentRunRepository
from app.db.repositories.conversation_repo import ConversationRepository
from app.db.repositories.message_repo import MessageRepository
from app.db.transaction import transaction
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse, ChatStreamEvent
from app.services.graph_runner import GraphRunner
from app.services.tool_call_service import ToolCallService
from app.services.user_service import UserService


class ChatService:
    """编排聊天执行与持久化流程。

    本服务负责聊天请求相关的业务流程，包括轻量用户准备、会话解析、
    请求与响应消息持久化、Agent 运行跟踪、流式生命周期处理以及审计记录。
    图执行和事件翻译仍只由图运行器负责。
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        graph_runner: GraphRunner,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        agent_run_repository: AgentRunRepository,
        user_service: UserService,
        tool_call_service: ToolCallService | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.session = session
        self.graph_runner = graph_runner
        self.conversation_repository = conversation_repository
        self.message_repository = message_repository
        self.agent_run_repository = agent_run_repository
        self.user_service = user_service
        self.tool_call_service = tool_call_service
        self.audit_service = audit_service or AuditService()

    @staticmethod
    def _derive_conversation_title(messages: list[ChatMessage]) -> str | None:
        """从首条用户消息中提取简短的会话标题。"""

        for message in messages:
            if message.role != "user":
                continue
            title = " ".join(message.content.strip().split())
            if not title:
                continue
            return title[:80]
        return None

    @staticmethod
    def _message_to_model(conversation_id: str, message: ChatMessage) -> Message:
        """将 API 聊天消息转换为可持久化的 ORM 消息记录。"""

        metadata = dict(message.metadata)
        if message.name is not None:
            metadata["name"] = message.name
        return Message(
            conversation_id=conversation_id,
            role=message.role,
            content=message.content,
            metadata_=metadata,
        )

    @staticmethod
    def _message_from_model(message: Message) -> ChatMessage:
        """将已持久化的 ORM 消息转换为聊天 Schema。"""

        metadata = dict(message.metadata_ or {})
        name = metadata.pop("name", None)
        return ChatMessage(
            role=message.role,
            content=message.content,
            name=name,
            metadata=metadata,
        )

    @staticmethod
    def _messages_equal(left: ChatMessage, right: ChatMessage) -> bool:
        """使用服务层会持久化的字段比较两条聊天消息是否相等。"""

        return (
            left.role == right.role
            and left.content == right.content
            and left.name == right.name
            and left.metadata == right.metadata
        )

    @staticmethod
    def _merge_response_metadata(
        response: ChatResponse,
        *,
        run_id: str,
    ) -> dict[str, Any]:
        """为响应负载补充由服务层维护的元信息。"""

        metadata = dict(response.metadata)
        metadata["run_id"] = run_id
        return metadata

    @staticmethod
    def _build_run_failure_output(exc: Exception) -> dict[str, Any]:
        """将图执行或 LLM 失败序列化为 Agent 运行输出元数据。"""

        data: dict[str, Any] = {
            "error": str(exc),
            "type": exc.__class__.__name__,
        }
        if isinstance(exc, AppException):
            data["code"] = exc.code.value
            data["details"] = exc.data
        return data

    @staticmethod
    def _build_stream_failure_output(event: ChatStreamEvent) -> dict[str, Any]:
        """将流式错误事件序列化为 Agent 运行输出元数据。"""

        data: dict[str, Any] = {
            "error": event.content or "stream execution failed",
            "type": "stream_error",
        }
        if event.data:
            data["details"] = dict(event.data)
            code = event.data.get("code")
            if isinstance(code, str):
                data["code"] = code
        return data

    @staticmethod
    def _build_stream_error_event(
        exc: Exception,
        *,
        conversation_id: str | None = None,
        run_id: str | None = None,
    ) -> ChatStreamEvent:
        """根据异常构建面向客户端的流式错误事件。"""

        if isinstance(exc, AppException):
            data = dict(exc.data)
            data.setdefault("code", exc.code.value)
            content = exc.message
        else:
            data = {
                "code": ErrorCode.INTERNAL_ERROR.value,
                "error": str(exc),
            }
            content = "服务器内部错误"

        if conversation_id is not None:
            data.setdefault("conversation_id", conversation_id)
        if run_id is not None:
            data.setdefault("run_id", run_id)

        return ChatStreamEvent(
            type="error",
            content=content,
            data=data,
        )

    @staticmethod
    def _enrich_stream_event(
        event: ChatStreamEvent,
        *,
        conversation_id: str,
        run_id: str,
    ) -> ChatStreamEvent:
        """为流式事件补充会话和运行元信息。"""

        data = dict(event.data)
        data.setdefault("conversation_id", conversation_id)
        data.setdefault("run_id", run_id)
        return event.model_copy(update={"data": data})

    async def _resolve_conversation(
        self,
        request: ChatRequest,
        user: CurrentUser,
    ) -> Conversation:
        """加载已有会话，或为当前聊天请求创建新会话。"""

        if request.conversation_id is not None:
            conversation = await self.conversation_repository.get_by_id_for_user(
                request.conversation_id,
                user.id,
            )
            if conversation is None:
                raise AppException(
                    ErrorCode.NOT_FOUND,
                    status_code=404,
                    data={"conversation_id": request.conversation_id},
                )
            return conversation

        async with transaction(self.session):
            conversation = await self.conversation_repository.add(
                Conversation(
                    user_id=user.id,
                    title=self._derive_conversation_title(request.messages),
                    metadata_=dict(request.metadata),
                )
            )

        return conversation

    async def _list_pending_messages(
        self,
        conversation_id: str,
        incoming_messages: list[ChatMessage],
    ) -> list[ChatMessage]:
        """只返回仍需持久化的消息。

        API 常常会在每次请求时提交完整会话历史。
        这个辅助方法把已存储消息视为前缀，只持久化新增的后缀部分。
        如果两边历史出现意外分叉，则退化为只持久化最新一条输入消息，
        避免重复回放大量历史记录。
        """

        if not incoming_messages:
            return []

        stored_messages = await self.message_repository.list_by_conversation(
            conversation_id,
            limit=max(50, len(incoming_messages) + 50),
            offset=0,
        )
        stored = [self._message_from_model(message) for message in stored_messages]

        prefix_length = 0
        while (
            prefix_length < len(stored)
            and prefix_length < len(incoming_messages)
            and self._messages_equal(stored[prefix_length], incoming_messages[prefix_length])
        ):
            prefix_length += 1

        if prefix_length == len(stored):
            return incoming_messages[prefix_length:]

        latest_incoming = incoming_messages[-1]
        if stored and self._messages_equal(stored[-1], latest_incoming):
            return []
        return [latest_incoming]

    async def _start_chat_run(
        self,
        request: ChatRequest,
        conversation: Conversation,
        user: CurrentUser,
    ) -> AgentRun:
        """在图执行开始前持久化请求侧状态。"""

        pending_messages = await self._list_pending_messages(
            conversation.id,
            request.messages,
        )

        async with transaction(self.session):
            for message in pending_messages:
                await self.message_repository.add(
                    self._message_to_model(conversation.id, message)
                )

            agent_run = await self.agent_run_repository.add(
                AgentRun(
                    conversation_id=conversation.id,
                    user_id=user.id,
                    status="running",
                    input=request.model_dump(),
                    output={},
                    metadata_={"trace_id": get_trace_id()},
                )
            )

        return agent_run

    async def _complete_chat_run(
        self,
        agent_run: AgentRun,
        conversation: Conversation,
        response: ChatResponse,
    ) -> None:
        """持久化图执行结果，并将运行状态标记为完成。"""

        pending_messages = await self._list_pending_messages(
            conversation.id,
            response.messages,
        )

        async with transaction(self.session):
            for message in pending_messages:
                await self.message_repository.add(
                    self._message_to_model(conversation.id, message)
                )

            if self.tool_call_service is not None:
                await self.tool_call_service.record_for_run(
                    agent_run.id,
                    response.tool_calls,
                )

            agent_run.status = "completed"
            agent_run.output = response.model_dump()
            await self.session.flush()

    async def _fail_chat_run(self, agent_run: AgentRun, exc: Exception) -> None:
        """在图执行失败时持久化失败详情。"""

        async with transaction(self.session):
            agent_run.status = "failed"
            agent_run.output = self._build_run_failure_output(exc)
            await self.session.flush()

    async def _fail_chat_run_from_stream_event(
        self,
        agent_run: AgentRun,
        event: ChatStreamEvent,
    ) -> None:
        """将流式错误事件持久化为最终运行输出。"""

        async with transaction(self.session):
            agent_run.status = "failed"
            agent_run.output = self._build_stream_failure_output(event)
            await self.session.flush()

    async def _prepare_chat_execution(
        self,
        request: ChatRequest,
        user: CurrentUser,
    ) -> tuple[Conversation, ChatRequest, AgentRun]:
        """准备用户状态，并持久化请求侧聊天上下文。"""

        await self.user_service.ensure_user(user.id, name=user.name)

        conversation = await self._resolve_conversation(request, user)
        graph_request = request.model_copy(
            update={
                "conversation_id": conversation.id,
                "user_id": user.id,
            }
        )
        agent_run = await self._start_chat_run(graph_request, conversation, user)
        return conversation, graph_request, agent_run

    async def _finalize_success(
        self,
        *,
        response: ChatResponse,
        conversation: Conversation,
        agent_run: AgentRun,
        user: CurrentUser,
    ) -> ChatResponse:
        """持久化成功输出，并补充 API 响应内容。"""

        await self._complete_chat_run(agent_run, conversation, response)
        await self.audit_service.record(
            AuditEvent(
                action=AuditAction.CHAT,
                result=AuditResult.SUCCESS,
                actor_id=user.id,
                trace_id=get_trace_id(),
                resource_type="conversation",
                resource_id=conversation.id,
                metadata={"run_id": agent_run.id},
            )
        )
        return response.model_copy(
            update={
                "conversation_id": conversation.id,
                "metadata": self._merge_response_metadata(
                    response,
                    run_id=agent_run.id,
                ),
            }
        )

    async def chat(self, request: ChatRequest, user: CurrentUser) -> ChatResponse:
        """执行一次非流式聊天请求，并持久化其完整生命周期。

        参数：
            request: 当前调用方提交的聊天请求负载，可能包含完整消息历史。
            user: 由 API 层解析出的请求级身份。

        返回：
            补充了持久化会话 ID 与 Agent 运行元信息的图执行响应。

        副作用：
            可能创建轻量用户记录、创建会话、追加请求与响应消息、
            创建或更新 Agent 运行记录，并写入审计事件。
        """

        conversation, graph_request, agent_run = await self._prepare_chat_execution(
            request,
            user,
        )

        try:
            response = await self.graph_runner.run_chat(graph_request, user_id=user.id)
        except Exception as exc:
            await self._fail_chat_run(agent_run, exc)
            raise

        return await self._finalize_success(
            response=response,
            conversation=conversation,
            agent_run=agent_run,
            user=user,
        )

    async def stream_chat(
        self,
        request: ChatRequest,
        user: CurrentUser,
    ) -> AsyncIterator[str]:
        """执行一次流式聊天请求，并持久化其完整生命周期。

        流式接口始终以 SSE 形式响应，因此一旦响应开始发送，
        后续错误会被转换为 ``error`` 事件，而不是继续向上传播为 HTTP 异常。
        """

        conversation: Conversation | None = None
        agent_run: AgentRun | None = None
        try:
            conversation, graph_request, agent_run = await self._prepare_chat_execution(
                request,
                user,
            )
        except Exception as exc:
            yield GraphRunner.format_sse(
                "error",
                self._build_stream_error_event(exc),
            )
            return

        try:
            async for event_name, event in self.graph_runner.stream_chat_events(
                graph_request,
                user_id=user.id,
            ):
                if event_name == "done":
                    response = ChatResponse.model_validate(event.data)
                    finalized = await self._finalize_success(
                        response=response,
                        conversation=conversation,
                        agent_run=agent_run,
                        user=user,
                    )
                    yield GraphRunner.format_sse(
                        "done",
                        ChatStreamEvent(type="done", data=finalized.model_dump()),
                    )
                    return

                enriched_event = self._enrich_stream_event(
                    event,
                    conversation_id=conversation.id,
                    run_id=agent_run.id,
                )

                if event_name == "error":
                    await self._fail_chat_run_from_stream_event(agent_run, enriched_event)
                    yield GraphRunner.format_sse("error", enriched_event)
                    return

                yield GraphRunner.format_sse(event_name, enriched_event)
        except Exception as exc:
            await self._fail_chat_run(agent_run, exc)
            yield GraphRunner.format_sse(
                "error",
                self._build_stream_error_event(
                    exc,
                    conversation_id=conversation.id,
                    run_id=agent_run.id,
                ),
            )
