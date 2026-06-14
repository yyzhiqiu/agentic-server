"""聊天业务编排服务。

本模块负责把 HTTP 层聊天请求转换成一条完整的运行生命周期：准备会话、
补齐 LangGraph thread 上下文、执行图、持久化消息与运行记录，并在需要时
处理人机交互中断与恢复。
"""

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
from app.graph.shared.human_input import normalize_pending_human_input, pending_human_input_to_metadata
from app.graph.shared.messages import chat_message_to_langchain_message
from app.graph.types import AgentRegistry
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
        agent_registry: AgentRegistry | None = None,
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
        self.agent_registry = agent_registry
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
    def _response_agent_id(response: ChatResponse, fallback_agent_id: str) -> str:
        """优先读取响应中实际执行的 Agent 标识。"""

        if isinstance(response.agent_id, str) and response.agent_id:
            return response.agent_id

        metadata = dict(response.metadata)
        agent_id = metadata.get("agent_id")
        if isinstance(agent_id, str) and agent_id:
            return agent_id
        return fallback_agent_id

    @staticmethod
    def _run_agent_id(agent_run: AgentRun) -> str:
        """从运行记录的一等字段或兼容元数据中提取实际执行 Agent。"""

        if isinstance(agent_run.agent_id, str) and agent_run.agent_id:
            return agent_run.agent_id

        metadata = dict(agent_run.metadata_ or {})
        agent_id = metadata.get("agent_id")
        if isinstance(agent_id, str) and agent_id:
            return agent_id

        output = dict(agent_run.output or {})
        output_agent_id = output.get("agent_id")
        if isinstance(output_agent_id, str) and output_agent_id:
            return output_agent_id

        output_metadata = output.get("metadata")
        if isinstance(output_metadata, dict):
            metadata_agent_id = output_metadata.get("agent_id")
            if isinstance(metadata_agent_id, str) and metadata_agent_id:
                return metadata_agent_id

        return DEFAULT_AGENT_ID

    @staticmethod
    def _run_graph_agent_id(agent_run: AgentRun) -> str:
        """从运行记录元数据中解析负责该 checkpoint 的图入口 Agent。

        Why:
            对于 ``coordinator_agent`` 这类入口型图，最终对外展示的业务 Agent
            可能是 ``route_planner_agent``，但 checkpoint 仍然属于协调图本身。
            恢复执行时必须继续使用原图，否则会出现 checkpoint 与 graph 不匹配、
            重复弹表单或恢复报错等问题。
        """

        metadata = dict(agent_run.metadata_ or {})
        graph_agent_id = metadata.get("graph_agent_id")
        if isinstance(graph_agent_id, str) and graph_agent_id:
            return graph_agent_id
        return ChatService._run_agent_id(agent_run)

    def _resolve_graph_runner(self, agent_id: str) -> GraphRunner:
        """根据目标 Agent 选择实际执行所需的 GraphRunner。"""

        if agent_id == self.graph_runner.agent_id:
            return self.graph_runner

        if self.agent_registry is None:
            raise AppException(
                ErrorCode.SERVICE_UNAVAILABLE,
                message="当前环境未加载 Agent 注册表，无法恢复指定运行。",
                status_code=503,
                data={"agent_id": agent_id},
            )

        agent_definition = self.agent_registry.get(agent_id)
        if agent_definition is None:
            raise AppException(
                ErrorCode.NOT_FOUND,
                status_code=404,
                data={"agent_id": agent_id},
            )

        return GraphRunner(
            agent_definition.graph,
            agent_id=agent_definition.metadata.agent_id,
        )

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
    def _pending_human_input_metadata(response: ChatResponse) -> dict[str, Any] | None:
        """读取响应中的待补参表单，并转换为可持久化字典。

        Why:
            新旧图实现对待补参表单的落点并不完全一致，有的直接放在
            ``response.pending_human_input``，有的仍写在 ``metadata`` 中。
            这里统一归一化后再持久化，避免恢复接口依赖具体 agent 的细节。
        """

        payload = normalize_pending_human_input(response.pending_human_input)
        if payload is None:
            payload = normalize_pending_human_input(response.metadata.get("pending_human_input"))
        if payload is None:
            return None
        return pending_human_input_to_metadata(payload)

    @staticmethod
    def _resume_input_to_user_message(
        input_payload: dict[str, Any],
        pending_human_input: dict[str, Any] | None,
    ) -> ChatMessage | None:
        """把结构化补参输入转换成可持久化的用户消息。

        Why:
            补参如果只存在于恢复 payload 中，前端历史消息和后端 thread 重建都
            看不到这次用户操作。这里把表单提交同步落成普通用户消息，可以让
            会话时间线完整可见，也方便后续从数据库重新 hydrate thread。
        """

        if not input_payload:
            return None

        label_map: dict[str, str] = {}
        if isinstance(pending_human_input, dict):
            raw_fields = pending_human_input.get("fields")
            if isinstance(raw_fields, list):
                for raw_field in raw_fields:
                    if not isinstance(raw_field, dict):
                        continue
                    name = raw_field.get("name")
                    label = raw_field.get("label")
                    if isinstance(name, str) and name and isinstance(label, str) and label:
                        label_map[name] = label

        parts: list[str] = []
        for key, value in input_payload.items():
            if isinstance(value, str):
                normalized_value = value.strip()
            elif value is None:
                normalized_value = ""
            else:
                normalized_value = str(value).strip()
            if not normalized_value:
                continue
            parts.append(f"{label_map.get(key, key)}：{normalized_value}")

        if not parts:
            return None

        return ChatMessage(
            role="user",
            content=f"补充路线规划信息：{'；'.join(parts)}",
            metadata={
                "message_type": "human_input_resume",
                "resume_input": dict(input_payload),
            },
        )

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
        agent_id: str,
        reason: str | None,
        pending_human_input: dict[str, Any] | None = None,
        output: dict[str, Any] | None = None,
    ) -> None:
        """把运行记录标记为可恢复中断。"""

        async with transaction(self.session):
            metadata = dict(agent_run.metadata_ or {})
            metadata["agent_id"] = agent_id
            metadata.setdefault("graph_agent_id", self.agent_id)
            metadata["resume_available"] = True
            metadata["interrupt_source"] = "human_input"
            if reason is None:
                metadata.pop("reason", None)
            else:
                metadata["reason"] = reason
            if pending_human_input is None:
                metadata.pop("pending_human_input", None)
            else:
                metadata["pending_human_input"] = pending_human_input

            agent_run.agent_id = agent_id
            agent_run.status = "interrupted"
            agent_run.metadata_ = metadata
            agent_run.output = output or {}
            await self.session.flush()

    async def _mark_chat_run_cancelled(
        self,
        agent_run: AgentRun,
        *,
        agent_id: str,
        reason: str | None,
    ) -> None:
        """把运行记录标记为不可恢复取消。"""

        async with transaction(self.session):
            metadata = dict(agent_run.metadata_ or {})
            metadata["agent_id"] = agent_id
            metadata.setdefault("graph_agent_id", self.agent_id)
            metadata["resume_available"] = False
            if reason is None:
                metadata.pop("reason", None)
            else:
                metadata["reason"] = reason

            output: dict[str, Any] = {
                "status": "cancelled",
                "agent_id": agent_id,
            }
            if reason is not None:
                output["reason"] = reason

            agent_run.agent_id = agent_id
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
            await self._mark_chat_run_cancelled(
                agent_run,
                agent_id=self._run_agent_id(agent_run),
                reason=reason,
            )
            return action, reason

        await self._mark_chat_run_interrupted(
            agent_run,
            agent_id=self._run_agent_id(agent_run),
            reason=reason,
        )
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
            # 如果是协调器/路由智能体（coordinator_agent）相关的会话，放宽限制，允许使用被路由目标的具体智能体继续对话；
            # 否则，如果是其他显式指定的具体智能体，则必须严格匹配该智能体，以防止跨智能体对话冲突。
            if (
                conversation_agent_id != DEFAULT_AGENT_ID
                and conversation_agent_id != self.agent_id
            ):
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
                    metadata["agent_id"] = conversation_agent_id
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
        """把旧会话已持久化消息一次性回填到标准 checkpoint thread。

        Why:
            运行中的 LangGraph thread 以 checkpoint 为准，但历史会话列表来自
            数据库持久化消息。首次进入某个 thread 或历史数据迁移后，必须把
            已持久化消息补回 checkpoint，后续图执行才能拿到完整上下文。

        Notes:
            仅当目标 thread 里还没有消息时才执行回填，避免重复注入同一段历史。
        """

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

    async def _persist_resume_input_message(
        self,
        *,
        conversation: Conversation,
        input_payload: dict[str, Any] | None,
        pending_human_input: dict[str, Any] | None,
    ) -> ChatMessage | None:
        """在恢复执行前持久化一条补参用户消息。

        Notes:
            恢复 payload 是一次性运行参数，不会天然出现在消息列表里。先持久化
            成用户消息，既能提升前端可读性，也能保证后续重新 hydrate thread
            时不会丢掉这次补参动作。
        """

        if not input_payload:
            return None

        resume_message = self._resume_input_to_user_message(
            input_payload,
            pending_human_input,
        )
        if resume_message is None:
            return None

        pending_messages = await self._list_pending_messages(
            conversation.id,
            [resume_message],
        )
        if pending_messages:
            async with transaction(self.session):
                for message in pending_messages:
                    await self.message_repository.add(
                        self._message_to_model(conversation.id, message)
                    )
        return resume_message

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
                        "graph_agent_id": self.agent_id,
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
        """持久化图执行结果，并标记运行完成。

        Side Effects:
            - 持久化本轮新增消息；
            - 记录工具调用；
            - 把运行状态更新为 ``completed``；
            - 清理待补参等仅属于中断态的元数据。
        """

        pending_messages = await self._list_pending_messages(
            conversation.id,
            response.messages,
        )

        async with transaction(self.session):
            for message in pending_messages:
                await self.message_repository.add(
                    self._message_to_model(conversation.id, message)
                )

            response_agent_id = self._response_agent_id(response, self.agent_id)
            if self.tool_call_service is not None:
                await self.tool_call_service.record_for_run(
                    agent_run.id,
                    response.tool_calls,
                    agent_id=response_agent_id,
                )

            agent_run.agent_id = response_agent_id
            agent_run.status = "completed"
            agent_run.output = response.model_dump()
            metadata = dict(agent_run.metadata_ or {})
            metadata["agent_id"] = response_agent_id
            metadata.setdefault("graph_agent_id", self.agent_id)
            metadata["thread_id"] = thread_id
            metadata["resume_available"] = False
            # 完成态必须清空中断痕迹，否则前端刷新后可能继续显示旧表单。
            metadata.pop("pending_human_input", None)
            metadata.pop("interrupt_source", None)
            metadata.pop("reason", None)
            agent_run.metadata_ = metadata
            await self.session.flush()

    async def _fail_chat_run(self, agent_run: AgentRun, exc: Exception) -> None:
        """在图执行失败时持久化失败详情。"""

        async with transaction(self.session):
            failed_agent_id = self._run_agent_id(agent_run)
            agent_run.agent_id = failed_agent_id
            agent_run.status = "failed"
            output = self._build_run_failure_output(exc)
            output["agent_id"] = failed_agent_id
            agent_run.output = output
            metadata = dict(agent_run.metadata_ or {})
            metadata["agent_id"] = failed_agent_id
            metadata.setdefault("graph_agent_id", self.agent_id)
            metadata["resume_available"] = False
            agent_run.metadata_ = metadata
            await self.session.flush()

    async def _fail_chat_run_from_stream_event(
        self,
        agent_run: AgentRun,
        event: ChatStreamEvent,
    ) -> None:
        """把流式错误事件持久化为最终运行输出。"""

        async with transaction(self.session):
            failed_agent_id = self._run_agent_id(agent_run)
            agent_run.agent_id = failed_agent_id
            agent_run.status = "failed"
            output = self._build_stream_failure_output(event)
            output["agent_id"] = failed_agent_id
            agent_run.output = output
            metadata = dict(agent_run.metadata_ or {})
            metadata["agent_id"] = failed_agent_id
            metadata.setdefault("graph_agent_id", self.agent_id)
            metadata["resume_available"] = False
            agent_run.metadata_ = metadata
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
        *,
        input_payload: dict[str, Any] | None = None,
    ) -> tuple[Conversation, ChatRequest, AgentRun, str, str]:
        """加载已中断运行，并重建恢复所需的执行上下文。

        该方法负责：
            1. 校验运行记录和所属会话仍然存在；
            2. 找到最初生成 checkpoint 的图入口 Agent；
            3. 定位可恢复的 thread；
            4. 把用户补参持久化为消息；
            5. 构造传给 GraphRunner 的恢复请求。

        Why:
            恢复执行最容易出问题的点不是“有没有 run_id”，而是 checkpoint
            属于哪个 graph、位于哪个 thread、会话历史是否和恢复 payload 保持
            一致。这里集中完成这些拼装，避免不同恢复入口各自拼一套逻辑。
        """

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

        # 恢复时必须回到创建 checkpoint 的图入口，而不是仅看最终展示给用户的业务 Agent。
        run_graph_agent_id = self._run_graph_agent_id(agent_run)
        run_graph_runner = self._resolve_graph_runner(run_graph_agent_id)

        thread_id = self._run_thread_id(agent_run, conversation)
        if not self._snapshot_has_messages(await run_graph_runner.get_state(thread_id)):
            # 兼容早期版本：旧运行可能直接以 run_id 作为 checkpoint thread。
            legacy_thread_id = agent_run.id
            if self._snapshot_has_messages(await run_graph_runner.get_state(legacy_thread_id)):
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

        run_agent_id = self._run_agent_id(agent_run)
        request = ChatRequest.model_validate(dict(agent_run.input or {}))
        pending_human_input = (
            dict(agent_run.metadata_["pending_human_input"])
            if isinstance(agent_run.metadata_, dict)
            and isinstance(agent_run.metadata_.get("pending_human_input"), dict)
            else None
        )
        await self._persist_resume_input_message(
            conversation=conversation,
            input_payload=input_payload,
            pending_human_input=pending_human_input,
        )
        metadata = {
            **request.metadata,
            "agent_id": run_agent_id,
            "thread_id": thread_id,
        }
        if input_payload:
            # Graph 恢复依赖结构化 payload，消息文本只负责展示和持久化。
            metadata["resume_payload"] = {"input": dict(input_payload)}
        graph_request = request.model_copy(
            update={
                "conversation_id": conversation.id,
                "user_id": user.id,
                "metadata": metadata,
            }
        )
        return conversation, graph_request, agent_run, thread_id, run_graph_agent_id

    async def _finalize_success(
        self,
        *,
        response: ChatResponse,
        conversation: Conversation,
        agent_run: AgentRun,
        user: CurrentUser,
        thread_id: str,
    ) -> ChatResponse:
        """持久化成功输出，并补充 API 响应内容。

        Notes:
            ``response.agent_id`` 可能与 ``self.agent_id`` 不同，例如协调 Agent
            把请求分发到路线规划 Agent 后，最终对用户展示的应是实际业务 Agent。
        """

        response_agent_id = self._response_agent_id(response, self.agent_id)
        finalized_response = response.model_copy(
            update={
                "conversation_id": conversation.id,
                "agent_id": response_agent_id,
                "metadata": self._merge_response_metadata(
                    response,
                    run_id=agent_run.id,
                    agent_id=response_agent_id,
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
                agent_id=response_agent_id,
                resource_type="conversation",
                resource_id=conversation.id,
                metadata={
                    "run_id": agent_run.id,
                    "agent_id": response_agent_id,
                    "conversation_agent_id": self._conversation_agent_id(conversation),
                },
            )
        )
        return finalized_response

    async def _finalize_interrupted_response(
        self,
        *,
        response: ChatResponse,
        conversation: Conversation,
        agent_run: AgentRun,
        thread_id: str,
    ) -> ChatResponse:
        """把人机交互中断结果持久化为可恢复运行。

        Why:
            对用户来说，中断也是一次完整的“系统回应”。
            这里既要把 assistant 的补参提示消息落库，也要把结构化表单保存到
            运行记录中，后续 `/resume` 才能知道需要补哪些字段。
        """

        finalized_response = response.model_copy(
            update={
                "conversation_id": conversation.id,
                "agent_id": response.agent_id or self.agent_id,
                "metadata": self._merge_response_metadata(
                    response,
                    run_id=agent_run.id,
                    agent_id=response.agent_id or self.agent_id,
                    thread_id=thread_id,
                ),
            }
        )
        response_agent_id = self._response_agent_id(finalized_response, self.agent_id)
        pending_messages = await self._list_pending_messages(
            conversation.id,
            finalized_response.messages,
        )
        if pending_messages:
            async with transaction(self.session):
                for message in pending_messages:
                    await self.message_repository.add(
                        self._message_to_model(conversation.id, message)
                    )
        await self._mark_chat_run_interrupted(
            agent_run,
            agent_id=response_agent_id,
            reason="等待用户补充路线规划信息",
            pending_human_input=self._pending_human_input_metadata(finalized_response),
            output=finalized_response.model_dump(),
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
        graph_runner: GraphRunner | None = None,
    ) -> ChatResponse | None:
        """执行一次非流式图调用，并闭环处理运行状态。"""

        runtime_task = await self._register_runtime_task(agent_run.id)
        resolved_graph_runner = graph_runner or self.graph_runner
        try:
            response = await resolved_graph_runner.run_chat(
                request,
                user_id=user.id,
                thread_id=thread_id,
                resume=resume,
            )
            if self._pending_human_input_metadata(response) is not None:
                return await self._finalize_interrupted_response(
                    response=response,
                    conversation=conversation,
                    agent_run=agent_run,
                    thread_id=thread_id,
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

        conversation, graph_request, agent_run, thread_id, run_agent_id = await self._prepare_resume_execution(
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
            graph_runner=self._resolve_graph_runner(run_agent_id),
        )

    async def resume_chat(
        self,
        run_id: str,
        user: CurrentUser,
        input_payload: dict[str, Any],
    ) -> ChatResponse | None:
        """面向用户侧补参场景恢复一条已中断聊天运行。"""

        conversation, graph_request, agent_run, thread_id, run_agent_id = await self._prepare_resume_execution(
            run_id,
            user,
            input_payload=input_payload,
        )
        return await self._run_chat_to_completion(
            request=graph_request,
            conversation=conversation,
            agent_run=agent_run,
            user=user,
            thread_id=thread_id,
            resume=True,
            suppress_control_exception=True,
            graph_runner=self._resolve_graph_runner(run_agent_id),
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
                    if self._pending_human_input_metadata(response) is not None:
                        finalized = await self._finalize_interrupted_response(
                            response=response,
                            conversation=conversation,
                            agent_run=agent_run,
                            thread_id=thread_id,
                        )
                        yield GraphRunner.format_sse(
                            "done",
                            ChatStreamEvent(type="done", data=finalized.model_dump()),
                        )
                        return
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

    async def stream_resume_chat(
        self,
        run_id: str,
        user: CurrentUser,
        input_payload: dict[str, Any],
    ) -> AsyncIterator[str]:
        """面向用户侧补参场景恢复一条已中断流式聊天运行。"""

        conversation: Conversation | None = None
        agent_run: AgentRun | None = None
        run_agent_id: str | None = None
        try:
            conversation, graph_request, agent_run, thread_id, run_agent_id = await self._prepare_resume_execution(
                run_id,
                user,
                input_payload=input_payload,
            )
        except Exception as exc:
            yield GraphRunner.format_sse(
                "error",
                self._build_stream_error_event(exc, agent_id=self.agent_id),
            )
            return

        runtime_task = await self._register_runtime_task(agent_run.id)
        try:
            resolved_graph_runner = self._resolve_graph_runner(run_agent_id or self.agent_id)
            async for event_name, event in resolved_graph_runner.stream_chat_events(
                graph_request,
                user_id=user.id,
                thread_id=thread_id,
                resume=True,
            ):
                if event_name == "done":
                    response = ChatResponse.model_validate(event.data)
                    if self._pending_human_input_metadata(response) is not None:
                        finalized = await self._finalize_interrupted_response(
                            response=response,
                            conversation=conversation,
                            agent_run=agent_run,
                            thread_id=thread_id,
                        )
                        yield GraphRunner.format_sse(
                            "done",
                            ChatStreamEvent(type="done", data=finalized.model_dump()),
                        )
                        return
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
