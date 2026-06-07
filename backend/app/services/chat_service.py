"""聊天业务编排服务。"""

from __future__ import annotations

import asyncio
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
from app.graph.default import DEFAULT_AGENT_ID
from app.graph.shared.messages import chat_message_to_langchain_message
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse, ChatStreamEvent
from app.services.agent_runtime_registry import AgentRuntimeRegistry
from app.services.graph_runner import GraphRunner
from app.services.tool_call_service import ToolCallService
from app.services.user_service import UserService


class ChatService:
    """编排聊天执行与持久化流程。

    Service 层负责：
    1. 准备会话与运行记录；
    2. 调用 GraphRunner 执行 LangGraph；
    3. 持久化消息、工具调用与运行结果；
    4. 把进程内取消信号转换为可恢复中断或彻底取消状态。
    """

    BLOCKING_RUN_STATUSES = frozenset({"created", "running", "interrupted"})
    THREAD_HYDRATE_BATCH_SIZE = 200

    def __init__(
        self,
        *,
        session: AsyncSession,
        graph_runner: GraphRunner,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        agent_run_repository: AgentRunRepository,
        user_service: UserService,
        agent_id: str = DEFAULT_AGENT_ID,
        runtime_registry: AgentRuntimeRegistry | None = None,
        tool_call_service: ToolCallService | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.session = session
        self.graph_runner = graph_runner
        self.conversation_repository = conversation_repository
        self.message_repository = message_repository
        self.agent_run_repository = agent_run_repository
        self.user_service = user_service
        self.agent_id = agent_id
        self.runtime_registry = runtime_registry
        self.tool_call_service = tool_call_service
        self.audit_service = audit_service or AuditService()

    @staticmethod
    def _derive_conversation_title(messages: list[ChatMessage]) -> str | None:
        """从首条用户消息中提取简短会话标题。"""

        for message in messages:
            if message.role != "user":
                continue
            title = " ".join(message.content.strip().split())
            if not title:
                continue
            return title[:80]
        return None

    @staticmethod
    def _conversation_agent_id(conversation: Conversation) -> str:
        """读取会话绑定的 Agent 标识。"""

        if isinstance(conversation.agent_id, str) and conversation.agent_id:
            return conversation.agent_id

        metadata = dict(conversation.metadata_ or {})
        agent_id = metadata.get("agent_id")
        if isinstance(agent_id, str) and agent_id:
            return agent_id
        return DEFAULT_AGENT_ID

    @staticmethod
    def _message_to_model(conversation_id: str, message: ChatMessage) -> Message:
        """把聊天消息转换为可持久化的 ORM 消息记录。"""

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
        """把已持久化的 ORM 消息转换为聊天 Schema。"""

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
        """使用持久化相关字段比较两条聊天消息是否相等。"""

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
        agent_id: str,
        thread_id: str,
    ) -> dict[str, Any]:
        """为响应补充由服务层维护的元信息。"""

        metadata = dict(response.metadata)
        metadata["run_id"] = run_id
        metadata["agent_id"] = agent_id
        metadata["thread_id"] = thread_id
        return metadata

    @staticmethod
    def _build_run_failure_output(exc: Exception) -> dict[str, Any]:
        """把图执行失败信息序列化为运行输出元数据。"""

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
        """把流式错误事件序列化为运行输出元数据。"""

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
        agent_id: str | None = None,
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
        if agent_id is not None:
            data.setdefault("agent_id", agent_id)

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
        agent_id: str,
        thread_id: str,
    ) -> ChatStreamEvent:
        """为流式事件补充会话和运行元信息。"""

        data = dict(event.data)
        data.setdefault("conversation_id", conversation_id)
        data.setdefault("run_id", run_id)
        data.setdefault("agent_id", agent_id)
        data.setdefault("thread_id", thread_id)
        return event.model_copy(update={"data": data})

    @staticmethod
    def _snapshot_values(snapshot: Any | None) -> dict[str, Any]:
        """从不同实现的状态快照中提取 values 负载。"""

        if snapshot is None:
            return {}

        values = getattr(snapshot, "values", None)
        if isinstance(values, dict):
            return dict(values)

        if isinstance(snapshot, dict):
            raw_values = snapshot.get("values")
            if isinstance(raw_values, dict):
                return dict(raw_values)
            return dict(snapshot)

        return {}

    @classmethod
    def _snapshot_has_messages(cls, snapshot: Any | None) -> bool:
        """判断状态快照中是否已经存在消息历史。"""

        values = cls._snapshot_values(snapshot)
        messages = values.get("messages")
        return isinstance(messages, list) and len(messages) > 0

    @staticmethod
    def _conversation_thread_id(conversation: Conversation) -> str:
        """读取会话绑定的 LangGraph thread 标识。"""

        metadata = dict(conversation.metadata_ or {})
        thread_id = metadata.get("thread_id")
        if isinstance(thread_id, str) and thread_id:
            return thread_id
        return conversation.id

    @staticmethod
    def _run_thread_id(agent_run: AgentRun, conversation: Conversation) -> str:
        """解析某条运行实际绑定的 LangGraph thread 标识。"""

        metadata = dict(agent_run.metadata_ or {})
        thread_id = metadata.get("thread_id")
        if isinstance(thread_id, str) and thread_id:
            return thread_id
        return ChatService._conversation_thread_id(conversation)

    @staticmethod
    def _build_control_exception(
        *,
        action: str,
        reason: str | None,
        run_id: str,
        agent_id: str,
    ) -> AppException:
        """把运行控制结果转换为结构化业务异常。"""

        if action == "cancel":
            message = "Agent 运行已取消"
        else:
            message = "Agent 运行已中断，可稍后恢复"

        data: dict[str, Any] = {
            "run_id": run_id,
            "agent_id": agent_id,
        }
        if reason is not None:
            data["reason"] = reason
        return AppException(
            ErrorCode.REQUEST_VALIDATION_ERROR,
            message=message,
            status_code=409,
            data=data,
        )

    async def _register_runtime_task(self, run_id: str) -> asyncio.Task[Any] | None:
        """把当前协程任务登记到运行时注册表。"""

        if self.runtime_registry is None:
            return None

        task = asyncio.current_task()
        if task is None:
            return None

        await self.runtime_registry.register(run_id, task)
        return task

    async def _unregister_runtime_task(
        self,
        run_id: str,
        task: asyncio.Task[Any] | None,
    ) -> None:
        """把当前协程任务从运行时注册表中移除。"""

        if self.runtime_registry is None or task is None:
            return
        await self.runtime_registry.unregister(run_id, task)

    async def _mark_chat_run_interrupted(
        self,
        agent_run: AgentRun,
        *,
        reason: str | None,
    ) -> None:
        """把运行记录标记为可恢复中断。"""

        async with transaction(self.session):
            metadata = dict(agent_run.metadata_ or {})
            metadata["agent_id"] = self.agent_id
            metadata["resume_available"] = True
            if reason is None:
                metadata.pop("reason", None)
            else:
                metadata["reason"] = reason

            agent_run.agent_id = self.agent_id
            agent_run.status = "interrupted"
            agent_run.metadata_ = metadata
            agent_run.output = {}
            await self.session.flush()

    async def _mark_chat_run_cancelled(
        self,
        agent_run: AgentRun,
        *,
        reason: str | None,
    ) -> None:
        """把运行记录标记为不可恢复取消。"""

        async with transaction(self.session):
            metadata = dict(agent_run.metadata_ or {})
            metadata["agent_id"] = self.agent_id
            metadata["resume_available"] = False
            if reason is None:
                metadata.pop("reason", None)
            else:
                metadata["reason"] = reason

            output: dict[str, Any] = {
                "status": "cancelled",
                "agent_id": self.agent_id,
            }
            if reason is not None:
                output["reason"] = reason

            agent_run.agent_id = self.agent_id
            agent_run.status = "cancelled"
            agent_run.metadata_ = metadata
            agent_run.output = output
            await self.session.flush()

    async def _handle_cancelled_run(self, agent_run: AgentRun) -> tuple[str, str | None]:
        """把 ``CancelledError`` 解释为可恢复中断或彻底取消。

        Why:
            LangGraph 在开启 checkpoint 时，即使底层 asyncio 任务被取消，
            也会保留最近一次 checkpoint。这里把“进程内任务取消”映射成
            运行记录状态更新，避免数据库里遗留永远卡在 ``running`` 的脏状态。
        """

        action = "interrupt"
        reason = "运行任务已中断，可稍后恢复"
        if self.runtime_registry is not None:
            control_request = await self.runtime_registry.get_control_request(agent_run.id)
            if control_request is not None:
                action = control_request.action
                reason = control_request.reason or reason

        if action == "cancel":
            await self._mark_chat_run_cancelled(agent_run, reason=reason)
            return action, reason

        await self._mark_chat_run_interrupted(agent_run, reason=reason)
        return action, reason

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

            conversation_agent_id = self._conversation_agent_id(conversation)
            if conversation_agent_id != self.agent_id:
                raise AppException(
                    ErrorCode.REQUEST_VALIDATION_ERROR,
                    message="当前会话已绑定到其他 Agent，请切换到对应智能体后继续对话。",
                    status_code=409,
                    data={
                        "conversation_id": request.conversation_id,
                        "conversation_agent_id": conversation_agent_id,
                        "requested_agent_id": self.agent_id,
                    },
                )

            metadata = dict(conversation.metadata_ or {})
            if metadata.get("thread_id") != conversation.id:
                async with transaction(self.session):
                    metadata["agent_id"] = self.agent_id
                    metadata["thread_id"] = conversation.id
                    conversation.metadata_ = metadata
                    await self.session.flush()
            return conversation

        async with transaction(self.session):
            metadata = dict(request.metadata)
            metadata.setdefault("agent_id", self.agent_id)
            conversation = await self.conversation_repository.add(
                Conversation(
                    user_id=user.id,
                    agent_id=self.agent_id,
                    title=self._derive_conversation_title(request.messages),
                    metadata_=metadata,
                )
            )
            metadata["thread_id"] = conversation.id
            conversation.metadata_ = metadata
            await self.session.flush()

        return conversation

    async def _load_persisted_messages(self, conversation_id: str) -> list[ChatMessage]:
        """分页读取会话下全部已持久化消息，用于 thread 初始化。"""

        offset = 0
        items: list[ChatMessage] = []
        while True:
            batch = await self.message_repository.list_by_conversation(
                conversation_id,
                limit=self.THREAD_HYDRATE_BATCH_SIZE,
                offset=offset,
            )
            if not batch:
                return items

            items.extend(self._message_from_model(message) for message in batch)
            if len(batch) < self.THREAD_HYDRATE_BATCH_SIZE:
                return items
            offset += len(batch)

    async def _hydrate_thread_from_persisted_messages(
        self,
        *,
        conversation: Conversation,
        user: CurrentUser,
        thread_id: str,
    ) -> None:
        """把旧会话已持久化消息一次性回填到标准 checkpoint thread。"""

        snapshot = await self.graph_runner.get_state(thread_id)
        if self._snapshot_has_messages(snapshot):
            return

        persisted_messages = await self._load_persisted_messages(conversation.id)
        if not persisted_messages:
            return

        await self.graph_runner.update_state(
            thread_id,
            {
                "messages": [
                    chat_message_to_langchain_message(message)
                    for message in persisted_messages
                ],
                "conversation_id": conversation.id,
                "user_id": user.id,
                "metadata": {
                    **dict(conversation.metadata_ or {}),
                    "agent_id": self.agent_id,
                    "thread_id": thread_id,
                },
            },
        )

    async def _ensure_conversation_accepts_new_turn(
        self,
        conversation: Conversation,
        user_id: str,
    ) -> None:
        """阻止在未处理的运行上继续向同一 thread 追加新输入。"""

        latest_run = await self.agent_run_repository.get_latest_by_conversation_for_user(
            conversation.id,
            user_id,
        )
        if latest_run is None:
            return

        if latest_run.status in {"created", "running"}:
            raise AppException(
                ErrorCode.REQUEST_VALIDATION_ERROR,
                message="当前会话仍有运行中的任务，请稍后重试或先取消该运行。",
                status_code=409,
                data={
                    "conversation_id": conversation.id,
                    "run_id": latest_run.id,
                    "status": latest_run.status,
                },
            )

        if latest_run.status == "interrupted":
            raise AppException(
                ErrorCode.REQUEST_VALIDATION_ERROR,
                message="当前会话存在待恢复的中断运行，请先恢复或取消后再继续对话。",
                status_code=409,
                data={
                    "conversation_id": conversation.id,
                    "run_id": latest_run.id,
                    "status": latest_run.status,
                },
            )

    async def _list_pending_messages(
        self,
        conversation_id: str,
        incoming_messages: list[ChatMessage],
    ) -> list[ChatMessage]:
        """只返回仍需持久化的消息。"""

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
        *,
        thread_id: str,
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
                    agent_id=self.agent_id,
                    user_id=user.id,
                    status="running",
                    input=request.model_dump(),
                    output={},
                    metadata_={
                        "trace_id": get_trace_id(),
                        "agent_id": self.agent_id,
                        "thread_id": thread_id,
                    },
                )
            )

        return agent_run

    async def _complete_chat_run(
        self,
        agent_run: AgentRun,
        conversation: Conversation,
        response: ChatResponse,
        thread_id: str,
    ) -> None:
        """持久化图执行结果，并标记运行完成。"""

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
                    agent_id=self.agent_id,
                )

            agent_run.agent_id = self.agent_id
            agent_run.status = "completed"
            agent_run.output = response.model_dump()
            metadata = dict(agent_run.metadata_ or {})
            metadata["thread_id"] = thread_id
            agent_run.metadata_ = metadata
            await self.session.flush()

    async def _fail_chat_run(self, agent_run: AgentRun, exc: Exception) -> None:
        """在图执行失败时持久化失败详情。"""

        async with transaction(self.session):
            agent_run.agent_id = self.agent_id
            agent_run.status = "failed"
            output = self._build_run_failure_output(exc)
            output["agent_id"] = self.agent_id
            agent_run.output = output
            await self.session.flush()

    async def _fail_chat_run_from_stream_event(
        self,
        agent_run: AgentRun,
        event: ChatStreamEvent,
    ) -> None:
        """把流式错误事件持久化为最终运行输出。"""

        async with transaction(self.session):
            agent_run.agent_id = self.agent_id
            agent_run.status = "failed"
            output = self._build_stream_failure_output(event)
            output["agent_id"] = self.agent_id
            agent_run.output = output
            await self.session.flush()

    async def _prepare_chat_execution(
        self,
        request: ChatRequest,
        user: CurrentUser,
    ) -> tuple[Conversation, ChatRequest, AgentRun, str]:
        """准备用户状态，并持久化请求侧聊天上下文。"""

        await self.user_service.ensure_user(user.id, name=user.name)

        conversation = await self._resolve_conversation(request, user)
        if request.conversation_id is not None:
            await self._ensure_conversation_accepts_new_turn(conversation, user.id)

        thread_id = self._conversation_thread_id(conversation)
        await self._hydrate_thread_from_persisted_messages(
            conversation=conversation,
            user=user,
            thread_id=thread_id,
        )

        pending_messages = await self._list_pending_messages(
            conversation.id,
            request.messages,
        )
        if not pending_messages:
            raise AppException(
                ErrorCode.REQUEST_VALIDATION_ERROR,
                message="当前请求没有新的消息需要发送。",
                status_code=409,
                data={"conversation_id": conversation.id},
            )

        graph_request = request.model_copy(
            update={
                "messages": pending_messages,
                "conversation_id": conversation.id,
                "user_id": user.id,
                "metadata": {
                    **request.metadata,
                    "agent_id": self.agent_id,
                    "thread_id": thread_id,
                },
            }
        )
        agent_run = await self._start_chat_run(
            graph_request,
            conversation,
            user,
            thread_id=thread_id,
        )
        return conversation, graph_request, agent_run, thread_id

    async def _prepare_resume_execution(
        self,
        run_id: str,
        user: CurrentUser,
    ) -> tuple[Conversation, ChatRequest, AgentRun, str]:
        """加载已中断运行，并重建恢复所需的执行上下文。"""

        await self.user_service.ensure_user(user.id, name=user.name)

        agent_run = await self.agent_run_repository.get_by_id_for_user(run_id, user.id)
        if agent_run is None:
            raise AppException(
                ErrorCode.NOT_FOUND,
                status_code=404,
                data={"run_id": run_id},
            )
        if agent_run.conversation_id is None:
            raise AppException(
                ErrorCode.REQUEST_VALIDATION_ERROR,
                message="当前运行缺少会话上下文，无法恢复。",
                status_code=409,
                data={"run_id": run_id},
            )

        conversation = await self.conversation_repository.get_by_id_for_user(
            agent_run.conversation_id,
            user.id,
        )
        if conversation is None:
            raise AppException(
                ErrorCode.NOT_FOUND,
                status_code=404,
                data={
                    "run_id": run_id,
                    "conversation_id": agent_run.conversation_id,
                },
            )

        conversation_agent_id = self._conversation_agent_id(conversation)
        if conversation_agent_id != self.agent_id:
            raise AppException(
                ErrorCode.REQUEST_VALIDATION_ERROR,
                message="当前运行绑定的会话 Agent 与恢复入口不一致。",
                status_code=409,
                data={
                    "run_id": run_id,
                    "conversation_agent_id": conversation_agent_id,
                    "requested_agent_id": self.agent_id,
                },
            )

        thread_id = self._run_thread_id(agent_run, conversation)
        if not self._snapshot_has_messages(await self.graph_runner.get_state(thread_id)):
            legacy_thread_id = agent_run.id
            if self._snapshot_has_messages(await self.graph_runner.get_state(legacy_thread_id)):
                thread_id = legacy_thread_id
            else:
                raise AppException(
                    ErrorCode.REQUEST_VALIDATION_ERROR,
                    message="当前运行不存在可恢复的 checkpoint 状态。",
                    status_code=409,
                    data={
                        "run_id": run_id,
                        "conversation_id": conversation.id,
                    },
                )

        request = ChatRequest.model_validate(dict(agent_run.input or {}))
        graph_request = request.model_copy(
            update={
                "conversation_id": conversation.id,
                "user_id": user.id,
                "metadata": {
                    **request.metadata,
                    "agent_id": self.agent_id,
                    "thread_id": thread_id,
                },
            }
        )
        return conversation, graph_request, agent_run, thread_id

    async def _finalize_success(
        self,
        *,
        response: ChatResponse,
        conversation: Conversation,
        agent_run: AgentRun,
        user: CurrentUser,
        thread_id: str,
    ) -> ChatResponse:
        """持久化成功输出，并补充 API 响应内容。"""

        finalized_response = response.model_copy(
            update={
                "conversation_id": conversation.id,
                "agent_id": self.agent_id,
                "metadata": self._merge_response_metadata(
                    response,
                    run_id=agent_run.id,
                    agent_id=self.agent_id,
                    thread_id=thread_id,
                ),
            }
        )
        await self._complete_chat_run(
            agent_run,
            conversation,
            finalized_response,
            thread_id=thread_id,
        )
        await self.audit_service.record(
            AuditEvent(
                action=AuditAction.CHAT,
                result=AuditResult.SUCCESS,
                actor_id=user.id,
                trace_id=get_trace_id(),
                agent_id=self.agent_id,
                resource_type="conversation",
                resource_id=conversation.id,
                metadata={
                    "run_id": agent_run.id,
                    "agent_id": self.agent_id,
                },
            )
        )
        return finalized_response

    async def _run_chat_to_completion(
        self,
        *,
        request: ChatRequest,
        conversation: Conversation,
        agent_run: AgentRun,
        user: CurrentUser,
        thread_id: str,
        resume: bool = False,
        suppress_control_exception: bool = False,
    ) -> ChatResponse | None:
        """执行一次非流式图调用，并闭环处理运行状态。"""

        runtime_task = await self._register_runtime_task(agent_run.id)
        try:
            response = await self.graph_runner.run_chat(
                request,
                user_id=user.id,
                thread_id=thread_id,
                resume=resume,
            )
        except asyncio.CancelledError:
            action, reason = await self._handle_cancelled_run(agent_run)
            if suppress_control_exception:
                return None
            raise self._build_control_exception(
                action=action,
                reason=reason,
                run_id=agent_run.id,
                agent_id=self.agent_id,
            )
        except Exception as exc:
            await self._fail_chat_run(agent_run, exc)
            raise
        finally:
            await self._unregister_runtime_task(agent_run.id, runtime_task)

        return await self._finalize_success(
            response=response,
            conversation=conversation,
            agent_run=agent_run,
            user=user,
            thread_id=thread_id,
        )

    async def chat(self, request: ChatRequest, user: CurrentUser) -> ChatResponse:
        """执行一次非流式聊天请求，并持久化其完整生命周期。"""

        conversation, graph_request, agent_run, thread_id = await self._prepare_chat_execution(
            request,
            user,
        )
        result = await self._run_chat_to_completion(
            request=graph_request,
            conversation=conversation,
            agent_run=agent_run,
            user=user,
            thread_id=thread_id,
        )
        if result is None:
            raise AppException(
                ErrorCode.INTERNAL_ERROR,
                message="聊天运行未返回结果",
            )
        return result

    async def resume_run(self, run_id: str, user: CurrentUser) -> ChatResponse | None:
        """从已持久化 checkpoint 恢复一条已中断运行。"""

        conversation, graph_request, agent_run, thread_id = await self._prepare_resume_execution(
            run_id,
            user,
        )
        return await self._run_chat_to_completion(
            request=graph_request,
            conversation=conversation,
            agent_run=agent_run,
            user=user,
            thread_id=thread_id,
            resume=True,
            suppress_control_exception=True,
        )

    async def stream_chat(
        self,
        request: ChatRequest,
        user: CurrentUser,
    ) -> AsyncIterator[str]:
        """执行一次流式聊天请求，并持久化其完整生命周期。"""

        conversation: Conversation | None = None
        agent_run: AgentRun | None = None
        try:
            conversation, graph_request, agent_run, thread_id = await self._prepare_chat_execution(
                request,
                user,
            )
        except Exception as exc:
            yield GraphRunner.format_sse(
                "error",
                self._build_stream_error_event(exc, agent_id=self.agent_id),
            )
            return

        runtime_task = await self._register_runtime_task(agent_run.id)
        try:
            async for event_name, event in self.graph_runner.stream_chat_events(
                graph_request,
                user_id=user.id,
                thread_id=thread_id,
            ):
                if event_name == "done":
                    response = ChatResponse.model_validate(event.data)
                    finalized = await self._finalize_success(
                        response=response,
                        conversation=conversation,
                        agent_run=agent_run,
                        user=user,
                        thread_id=thread_id,
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
                    agent_id=self.agent_id,
                    thread_id=thread_id,
                )

                if event_name == "error":
                    await self._fail_chat_run_from_stream_event(agent_run, enriched_event)
                    yield GraphRunner.format_sse("error", enriched_event)
                    return

                yield GraphRunner.format_sse(event_name, enriched_event)
        except asyncio.CancelledError:
            action, reason = await self._handle_cancelled_run(agent_run)
            controlled_error = self._build_control_exception(
                action=action,
                reason=reason,
                run_id=agent_run.id,
                agent_id=self.agent_id,
            )
            yield GraphRunner.format_sse(
                "error",
                self._build_stream_error_event(
                    controlled_error,
                    conversation_id=conversation.id,
                    run_id=agent_run.id,
                    agent_id=self.agent_id,
                ),
            )
        except Exception as exc:
            await self._fail_chat_run(agent_run, exc)
            yield GraphRunner.format_sse(
                "error",
                self._build_stream_error_event(
                    exc,
                    conversation_id=conversation.id,
                    run_id=agent_run.id,
                    agent_id=self.agent_id,
                ),
            )
        finally:
            await self._unregister_runtime_task(agent_run.id, runtime_task)
