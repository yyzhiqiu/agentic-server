from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.audit.enums import AuditAction, AuditResult
from app.audit.schemas import AuditEvent
from app.audit.service import AuditService
from app.common.exceptions import AppException, LLMException
from app.core.security import CurrentUser
from app.db.models.agent_run import AgentRun
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.models.user import User
from app.graph.default import DEFAULT_AGENT_ID
from app.graph.shared.messages import message_like_to_chat_message
from app.graph.types import AgentDefinition, AgentMetadata
from app.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatStreamEvent,
    PendingHumanInput,
)
from app.services.agent_runtime_registry import AgentRuntimeRegistry, RuntimeControlRequest
from app.services.chat_service import ChatService
from app.services.graph_runner import GraphRunner
from app.services.tool_call_service import ToolCallService
from app.services.user_service import UserService
from tests.support.transactional_session import TransactionalSessionStub, maybe_mark_autobegin


class _FakeSession(TransactionalSessionStub):
    pass


class _FakeGraphRunner:
    def __init__(
        self,
        *,
        error: Exception | None = None,
        stream_error: ChatStreamEvent | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        pending_human_input: PendingHumanInput | None = None,
    ) -> None:
        self.error = error
        self.stream_error = stream_error
        self.tool_calls = tool_calls or []
        self.pending_human_input = pending_human_input
        self.requests: list[tuple[ChatRequest, str | None, str | None, bool]] = []
        self.thread_messages: dict[str, list[ChatMessage]] = {}

    async def get_state(self, thread_id: str):
        messages = self.thread_messages.get(thread_id)
        if messages is None:
            return None
        return SimpleNamespace(values={"messages": list(messages)})

    async def update_state(
        self,
        thread_id: str,
        values: dict[str, Any],
        *,
        as_node: str | None = None,
    ) -> dict[str, Any]:
        _ = as_node
        raw_messages = values.get("messages", [])
        normalized = [
            converted
            for item in raw_messages
            if (converted := message_like_to_chat_message(item)) is not None
        ]
        self.thread_messages[thread_id] = normalized
        return {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def _response_content(request: ChatRequest) -> str:
        latest = request.messages[-1]
        return f"Mock response: {latest.content}"

    async def run_chat(
        self,
        request: ChatRequest,
        *,
        user_id: str | None = None,
        thread_id: str | None = None,
        resume: bool = False,
    ) -> ChatResponse:
        self.requests.append((request, user_id, thread_id, resume))
        if self.error is not None:
            raise self.error

        resolved_thread_id = thread_id or request.conversation_id or "default-thread"
        history = list(self.thread_messages.get(resolved_thread_id, []))
        if not resume:
            history.extend(request.messages)

        assistant = ChatMessage(
            role="assistant",
            content=self._response_content(request),
        )
        history.append(assistant)
        self.thread_messages[resolved_thread_id] = history
        return ChatResponse(
            conversation_id=request.conversation_id,
            agent_id=request.metadata.get("agent_id")
            if isinstance(request.metadata.get("agent_id"), str)
            else DEFAULT_AGENT_ID,
            message=assistant,
            messages=history,
            metadata={
                "model": "mock",
                "agent_id": (
                    request.metadata.get("agent_id")
                    if isinstance(request.metadata.get("agent_id"), str)
                    else DEFAULT_AGENT_ID
                ),
            },
            tool_calls=self.tool_calls,
            pending_human_input=self.pending_human_input,
        )

    async def stream_chat_events(
        self,
        request: ChatRequest,
        *,
        user_id: str | None = None,
        thread_id: str | None = None,
        resume: bool = False,
    ):
        self.requests.append((request, user_id, thread_id, resume))
        if self.stream_error is not None:
            yield "error", self.stream_error
            return

        resolved_thread_id = thread_id or request.conversation_id or "default-thread"
        history = list(self.thread_messages.get(resolved_thread_id, []))
        if not resume:
            history.extend(request.messages)

        assistant = ChatMessage(
            role="assistant",
            content=self._response_content(request),
        )
        history.append(assistant)
        self.thread_messages[resolved_thread_id] = history
        response = ChatResponse(
            conversation_id=request.conversation_id,
            agent_id=request.metadata.get("agent_id")
            if isinstance(request.metadata.get("agent_id"), str)
            else DEFAULT_AGENT_ID,
            message=assistant,
            messages=history,
            metadata={
                "model": "mock",
                "agent_id": (
                    request.metadata.get("agent_id")
                    if isinstance(request.metadata.get("agent_id"), str)
                    else DEFAULT_AGENT_ID
                ),
            },
            tool_calls=self.tool_calls,
            pending_human_input=self.pending_human_input,
        )
        yield "start", ChatStreamEvent(type="start")
        yield "message", ChatStreamEvent(type="message", content=assistant.content)
        yield "done", ChatStreamEvent(type="done", data=response.model_dump())


class _ThreadAwareGraphRunner(_FakeGraphRunner):
    def __init__(
        self,
        *,
        available_threads: set[str] | None = None,
        pending_human_input: PendingHumanInput | None = None,
    ) -> None:
        super().__init__(pending_human_input=pending_human_input)
        self.available_threads = set(available_threads or set())

    async def get_state(self, thread_id: str):
        if thread_id not in self.available_threads:
            return None
        return await super().get_state(thread_id)


class _FakeUserRepository:
    def __init__(self, session: _FakeSession | None = None) -> None:
        self.session = session
        self.items: dict[str, User] = {}

    async def get(self, id_: str) -> User | None:
        maybe_mark_autobegin(self.session)
        return self.items.get(id_)

    async def add(self, user: User) -> User:
        self.items[user.id] = user
        return user


class _FakeConversationRepository:
    def __init__(self, session: _FakeSession | None = None) -> None:
        self.session = session
        self.items: dict[str, Conversation] = {}

    async def add(self, conversation: Conversation) -> Conversation:
        conversation.id = conversation.id or f"conversation-{len(self.items) + 1}"
        if conversation.created_at is None:
            conversation.created_at = datetime.now(timezone.utc)
        if not getattr(conversation, "agent_id", None):
            conversation.agent_id = DEFAULT_AGENT_ID
        self.items[conversation.id] = conversation
        return conversation

    async def get_by_id_for_user(self, conversation_id: str, user_id: str) -> Conversation | None:
        maybe_mark_autobegin(self.session)
        item = self.items.get(conversation_id)
        if item is None or item.user_id != user_id or item.deleted_at is not None:
            return None
        return item


class _FakeMessageRepository:
    def __init__(self, session: _FakeSession | None = None) -> None:
        self.session = session
        self.items: list[Message] = []

    async def add(self, message: Message) -> Message:
        message.id = message.id or f"message-{len(self.items) + 1}"
        if message.created_at is None:
            message.created_at = datetime.now(timezone.utc)
        self.items.append(message)
        return message

    async def list_by_conversation(
        self,
        conversation_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Message]:
        maybe_mark_autobegin(self.session)
        messages = [item for item in self.items if item.conversation_id == conversation_id]
        return messages[offset : offset + limit]


class _FakeAgentRunRepository:
    def __init__(self) -> None:
        self.items: dict[str, AgentRun] = {}

    async def add(self, agent_run: AgentRun) -> AgentRun:
        agent_run.id = agent_run.id or f"run-{len(self.items) + 1}"
        if agent_run.created_at is None:
            agent_run.created_at = datetime.now(timezone.utc)
        if not getattr(agent_run, "agent_id", None):
            agent_run.agent_id = DEFAULT_AGENT_ID
        self.items[agent_run.id] = agent_run
        return agent_run

    async def get_by_id_for_user(self, run_id: str, user_id: str) -> AgentRun | None:
        item = self.items.get(run_id)
        if item is None or item.user_id != user_id:
            return None
        return item

    async def get_latest_by_conversation_for_user(
        self,
        conversation_id: str,
        user_id: str,
    ) -> AgentRun | None:
        candidates = [
            item
            for item in self.items.values()
            if item.conversation_id == conversation_id and item.user_id == user_id
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda item: item.created_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return candidates[0]


class _FakeToolCallRepository:
    def __init__(self) -> None:
        self.items: list[Any] = []

    async def add(self, tool_call) -> Any:
        tool_call.id = getattr(tool_call, "id", None) or f"tool-call-{len(self.items) + 1}"
        if getattr(tool_call, "created_at", None) is None:
            now = datetime.now(timezone.utc)
            tool_call.created_at = now
            tool_call.updated_at = now
        self.items.append(tool_call)
        return tool_call

    async def list_by_agent_run(self, agent_run_id: str) -> list[Any]:
        return [item for item in self.items if item.agent_run_id == agent_run_id]


class _FakeAuditWriter:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def write(self, event: AuditEvent) -> None:
        self.events.append(event)


def _build_service(
    *,
    graph_runner: _FakeGraphRunner | None = None,
    conversation_repository: _FakeConversationRepository | None = None,
    message_repository: _FakeMessageRepository | None = None,
    agent_run_repository: _FakeAgentRunRepository | None = None,
    user_repository: _FakeUserRepository | None = None,
    tool_call_repository: _FakeToolCallRepository | None = None,
    audit_writer: _FakeAuditWriter | None = None,
    session: _FakeSession | None = None,
    runtime_registry: AgentRuntimeRegistry | None = None,
) -> tuple[
    ChatService,
    _FakeGraphRunner,
    _FakeConversationRepository,
    _FakeMessageRepository,
    _FakeAgentRunRepository,
    _FakeUserRepository,
]:
    session = session or _FakeSession()
    graph = graph_runner or _FakeGraphRunner()
    conversations = conversation_repository or _FakeConversationRepository(session)
    messages = message_repository or _FakeMessageRepository(session)
    agent_runs = agent_run_repository or _FakeAgentRunRepository()
    users = user_repository or _FakeUserRepository(session)
    tool_calls = tool_call_repository or _FakeToolCallRepository()
    writer = audit_writer or _FakeAuditWriter()
    user_service = UserService(
        session=session,  # type: ignore[arg-type]
        user_repository=users,  # type: ignore[arg-type]
    )
    service = ChatService(
        session=session,  # type: ignore[arg-type]
        graph_runner=graph,  # type: ignore[arg-type]
        conversation_repository=conversations,  # type: ignore[arg-type]
        message_repository=messages,  # type: ignore[arg-type]
        agent_run_repository=agent_runs,  # type: ignore[arg-type]
        user_service=user_service,
        runtime_registry=runtime_registry,
        agent_registry={
            "coordinator_agent": AgentDefinition(
                metadata=AgentMetadata(
                    agent_id="coordinator_agent",
                    name="协调入口",
                    description="mock",
                    version="0.1.0",
                    capabilities=[],
                ),
                graph=object(),
            ),
            "chat_agent": AgentDefinition(
                metadata=AgentMetadata(
                    agent_id="chat_agent",
                    name="通用回复",
                    description="mock",
                    version="0.1.0",
                    capabilities=[],
                ),
                graph=object(),
            ),
            "route_planner_agent": AgentDefinition(
                metadata=AgentMetadata(
                    agent_id="route_planner_agent",
                    name="路线规划",
                    description="mock",
                    version="0.1.0",
                    capabilities=[],
                ),
                graph=object(),
            ),
        },
        tool_call_service=ToolCallService(  # type: ignore[arg-type]
            tool_call_repository=tool_calls,
        ),
        audit_service=AuditService(writer=writer),
    )
    return service, graph, conversations, messages, agent_runs, users


@pytest.mark.asyncio
async def test_chat_service_creates_conversation_and_persists_chat_state() -> None:
    service, graph, conversations, messages, agent_runs, users = _build_service()
    request = ChatRequest(messages=[ChatMessage(role="user", content="hello world")])
    user = CurrentUser(id="user-1", name="tester")

    response = await service.chat(request, user)

    assert response.conversation_id == "conversation-1"
    assert response.message.role == "assistant"
    assert response.metadata["model"] == "mock"
    assert response.metadata["run_id"] == "run-1"
    assert response.metadata["agent_id"] == "coordinator_agent"
    assert response.metadata["thread_id"] == "conversation-1"
    assert conversations.items["conversation-1"].title == "hello world"
    assert conversations.items["conversation-1"].agent_id == "coordinator_agent"
    assert conversations.items["conversation-1"].metadata_["thread_id"] == "conversation-1"
    assert [message.role for message in messages.items] == ["user", "assistant"]
    assert agent_runs.items["run-1"].agent_id == "coordinator_agent"
    assert agent_runs.items["run-1"].status == "completed"
    assert agent_runs.items["run-1"].conversation_id == "conversation-1"
    assert agent_runs.items["run-1"].metadata_["thread_id"] == "conversation-1"
    assert graph.requests[0][0].conversation_id == "conversation-1"
    assert graph.requests[0][0].messages == [ChatMessage(role="user", content="hello world")]
    assert users.items["user-1"].name == "tester"


@pytest.mark.asyncio
async def test_chat_service_reuses_existing_conversation_without_replaying_history() -> None:
    conversations = _FakeConversationRepository()
    messages = _FakeMessageRepository()
    service, graph, _, persisted_messages, _, _ = _build_service(
        conversation_repository=conversations,
        message_repository=messages,
    )
    user = CurrentUser(id="user-1", name="tester")

    conversation = await conversations.add(
        Conversation(
            id="conversation-9",
            user_id="user-1",
            agent_id="coordinator_agent",
            title="demo",
            metadata_={},
        )
    )
    await persisted_messages.add(
        Message(conversation_id=conversation.id, role="user", content="hello", metadata_={})
    )
    await persisted_messages.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content="Mock response: hello",
            metadata_={},
        )
    )

    response = await service.chat(
        ChatRequest(
            conversation_id=conversation.id,
            messages=[
                ChatMessage(role="user", content="hello"),
                ChatMessage(role="assistant", content="Mock response: hello"),
                ChatMessage(role="user", content="follow up"),
            ],
        ),
        user,
    )

    assert response.conversation_id == "conversation-9"
    assert response.messages == [
        ChatMessage(role="user", content="hello", metadata={}),
        ChatMessage(role="assistant", content="Mock response: hello", metadata={}),
        ChatMessage(role="user", content="follow up", metadata={}),
        ChatMessage(role="assistant", content="Mock response: follow up", metadata={}),
    ]
    assert len(persisted_messages.items) == 4
    assert [message.content for message in persisted_messages.items] == [
        "hello",
        "Mock response: hello",
        "follow up",
        "Mock response: follow up",
    ]
    assert graph.requests[0][0].messages == [ChatMessage(role="user", content="follow up")]
    assert graph.requests[0][2] == "conversation-9"


@pytest.mark.asyncio
async def test_chat_service_existing_conversation_can_continue_with_incremental_message_only() -> None:
    conversations = _FakeConversationRepository()
    messages = _FakeMessageRepository()
    service, graph, _, persisted_messages, _, _ = _build_service(
        conversation_repository=conversations,
        message_repository=messages,
    )
    user = CurrentUser(id="user-1", name="tester")

    conversation = await conversations.add(
        Conversation(
            id="conversation-8",
            user_id="user-1",
            agent_id="coordinator_agent",
            title="demo",
            metadata_={},
        )
    )
    await persisted_messages.add(
        Message(conversation_id=conversation.id, role="user", content="hello", metadata_={})
    )
    await persisted_messages.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content="Mock response: hello",
            metadata_={},
        )
    )

    response = await service.chat(
        ChatRequest(
            conversation_id=conversation.id,
            messages=[ChatMessage(role="user", content="next step")],
        ),
        user,
    )

    assert response.messages[-2:] == [
        ChatMessage(role="user", content="next step", metadata={}),
        ChatMessage(role="assistant", content="Mock response: next step", metadata={}),
    ]
    assert graph.requests[0][0].messages == [ChatMessage(role="user", content="next step")]
    assert graph.requests[0][2] == "conversation-8"


@pytest.mark.asyncio
async def test_chat_service_rejects_conversation_bound_to_other_agent() -> None:
    conversations = _FakeConversationRepository()
    service, _, _, _, _, _ = _build_service(conversation_repository=conversations)
    user = CurrentUser(id="user-1", name="tester")

    await conversations.add(
        Conversation(
            id="conversation-9",
            user_id="user-1",
            agent_id="code_agent",
            title="demo",
            metadata_={"agent_id": "code_agent"},
        )
    )

    with pytest.raises(AppException) as exc_info:
        await service.chat(
            ChatRequest(
                conversation_id="conversation-9",
                messages=[ChatMessage(role="user", content="continue")],
            ),
            user,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.data["conversation_agent_id"] == "code_agent"
    assert exc_info.value.data["requested_agent_id"] == "coordinator_agent"


@pytest.mark.asyncio
async def test_chat_service_raises_not_found_for_unknown_conversation() -> None:
    service, _, _, _, _, _ = _build_service()

    with pytest.raises(AppException) as exc_info:
        await service.chat(
            ChatRequest(
                conversation_id="missing",
                messages=[ChatMessage(role="user", content="hello")],
            ),
            CurrentUser(id="user-1", name="tester"),
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_chat_service_marks_run_failed_when_graph_execution_errors() -> None:
    service, _, _, messages, agent_runs, _ = _build_service(
        graph_runner=_FakeGraphRunner(error=LLMException("LLM_API_KEY is not configured"))
    )

    with pytest.raises(LLMException):
        await service.chat(
            ChatRequest(messages=[ChatMessage(role="user", content="hello")]),
            CurrentUser(id="user-1", name="tester"),
        )

    assert [message.role for message in messages.items] == ["user"]
    assert agent_runs.items["run-1"].agent_id == "coordinator_agent"
    assert agent_runs.items["run-1"].status == "failed"
    assert agent_runs.items["run-1"].output["error"] == "LLM_API_KEY is not configured"
    assert agent_runs.items["run-1"].output["code"] == "L00001"


@pytest.mark.asyncio
async def test_chat_service_persists_tool_calls_for_completed_runs() -> None:
    tool_call_repository = _FakeToolCallRepository()
    service, _, _, _, agent_runs, _ = _build_service(
        graph_runner=_FakeGraphRunner(
            tool_calls=[
                {
                    "tool_name": "search",
                    "status": "completed",
                    "input": {"query": "agentic server"},
                    "output": {"hits": 3},
                    "metadata": {"provider": "mock-tool"},
                }
            ]
        ),
        tool_call_repository=tool_call_repository,
    )

    response = await service.chat(
        ChatRequest(messages=[ChatMessage(role="user", content="hello")]),
        CurrentUser(id="user-1", name="tester"),
    )

    assert response.tool_calls[0].tool_name == "search"
    assert len(tool_call_repository.items) == 1
    assert tool_call_repository.items[0].agent_run_id == "run-1"
    assert tool_call_repository.items[0].tool_name == "search"
    assert tool_call_repository.items[0].output == {"hits": 3}
    assert tool_call_repository.items[0].metadata_["agent_id"] == "coordinator_agent"
    assert agent_runs.items["run-1"].output["tool_calls"][0]["tool_name"] == "search"


@pytest.mark.asyncio
async def test_chat_service_records_audit_event_on_success() -> None:
    audit_writer = _FakeAuditWriter()
    service, _, _, _, _, _ = _build_service(audit_writer=audit_writer)

    await service.chat(
        ChatRequest(messages=[ChatMessage(role="user", content="hello")]),
        CurrentUser(id="user-1", name="tester"),
    )

    assert len(audit_writer.events) == 1
    assert audit_writer.events[0].action == AuditAction.CHAT
    assert audit_writer.events[0].result == AuditResult.SUCCESS
    assert audit_writer.events[0].actor_id == "user-1"
    assert audit_writer.events[0].agent_id == "coordinator_agent"


@pytest.mark.asyncio
async def test_chat_service_handles_read_then_write_autobegin_flow() -> None:
    session = _FakeSession()
    service, _, conversations, messages, agent_runs, users = _build_service(session=session)

    response = await service.chat(
        ChatRequest(messages=[ChatMessage(role="user", content="hello autobegin")]),
        CurrentUser(id="user-1", name="tester"),
    )

    assert response.conversation_id == "conversation-1"
    assert users.items["user-1"].name == "tester"
    assert [message.role for message in messages.items] == ["user", "assistant"]
    assert conversations.items["conversation-1"].agent_id == "coordinator_agent"
    assert agent_runs.items["run-1"].agent_id == "coordinator_agent"
    assert agent_runs.items["run-1"].status == "completed"
    assert conversations.items["conversation-1"].title == "hello autobegin"
    assert session.rollback_calls == 0
    assert session.commit_calls >= 3


@pytest.mark.asyncio
async def test_chat_service_stream_persists_successful_chat_lifecycle() -> None:
    service, graph, conversations, messages, agent_runs, users = _build_service()
    request = ChatRequest(messages=[ChatMessage(role="user", content="stream hello")])
    user = CurrentUser(id="user-1", name="tester")

    events = [event async for event in service.stream_chat(request, user)]

    assert any("event: start" in event for event in events)
    assert any("event: message" in event and "Mock response" in event for event in events)
    assert any("event: done" in event for event in events)
    assert conversations.items["conversation-1"].title == "stream hello"
    assert conversations.items["conversation-1"].agent_id == "coordinator_agent"
    assert [message.role for message in messages.items] == ["user", "assistant"]
    assert agent_runs.items["run-1"].agent_id == "coordinator_agent"
    assert agent_runs.items["run-1"].status == "completed"
    assert users.items["user-1"].name == "tester"
    assert graph.requests[0][0].conversation_id == "conversation-1"

    done_event = next(event for event in events if event.startswith("event: done"))
    payload = json.loads(done_event.split("data: ", 1)[1])
    assert payload["data"]["conversation_id"] == "conversation-1"
    assert payload["data"]["metadata"]["run_id"] == "run-1"
    assert payload["data"]["metadata"]["agent_id"] == "coordinator_agent"


@pytest.mark.asyncio
async def test_chat_service_stream_marks_run_failed_when_graph_yields_error() -> None:
    service, _, _, messages, agent_runs, _ = _build_service(
        graph_runner=_FakeGraphRunner(
            stream_error=ChatStreamEvent(
                type="error",
                content="LLM_API_KEY is not configured",
                data={"code": "L00001", "provider": "mock-disabled"},
            )
        )
    )

    events = [
        event
        async for event in service.stream_chat(
            ChatRequest(messages=[ChatMessage(role="user", content="hello")]),
            CurrentUser(id="user-1", name="tester"),
        )
    ]

    assert any("event: error" in event for event in events)
    assert [message.role for message in messages.items] == ["user"]
    assert agent_runs.items["run-1"].agent_id == "coordinator_agent"
    assert agent_runs.items["run-1"].status == "failed"
    assert agent_runs.items["run-1"].output["error"] == "LLM_API_KEY is not configured"
    assert agent_runs.items["run-1"].output["code"] == "L00001"


@pytest.mark.asyncio
async def test_chat_service_stream_persists_interrupted_message_history() -> None:
    pending_human_input = PendingHumanInput(
        kind="form",
        title="补充路线规划信息",
        message="当前还缺少起点、出行方式，请补充后继续路线规划。",
        fields=[
            {
                "name": "origin",
                "label": "起点",
                "type": "text",
                "required": True,
                "placeholder": "请输入起点",
                "options": [],
            },
            {
                "name": "travel_mode",
                "label": "出行方式",
                "type": "select",
                "required": True,
                "options": [
                    {"label": "驾车", "value": "driving"},
                    {"label": "步行", "value": "walking"},
                    {"label": "公交", "value": "transit"},
                ],
            },
        ],
        submit_label="继续规划路线",
        missing_fields=["origin", "travel_mode"],
    )
    service, _, conversations, messages, agent_runs, _ = _build_service(
        graph_runner=_FakeGraphRunner(pending_human_input=pending_human_input)
    )

    events = [
        event
        async for event in service.stream_chat(
            ChatRequest(messages=[ChatMessage(role="user", content="我要去广东")]),
            CurrentUser(id="user-1", name="tester"),
        )
    ]

    done_event = next(event for event in events if event.startswith("event: done"))
    payload = json.loads(done_event.split("data: ", 1)[1])

    assert payload["data"]["pending_human_input"]["missing_fields"] == [
        "origin",
        "travel_mode",
    ]
    assert conversations.items["conversation-1"].agent_id == "coordinator_agent"
    assert [message.role for message in messages.items] == ["user", "assistant"]
    assert messages.items[1].content == "Mock response: 我要去广东"
    assert agent_runs.items["run-1"].status == "interrupted"
    assert agent_runs.items["run-1"].metadata_["interrupt_source"] == "human_input"
    assert agent_runs.items["run-1"].metadata_["pending_human_input"]["missing_fields"] == [
        "origin",
        "travel_mode",
    ]


@pytest.mark.asyncio
async def test_chat_service_passes_conversation_thread_id_to_graph_runner() -> None:
    service, graph, _, _, _, _ = _build_service()

    await service.chat(
        ChatRequest(messages=[ChatMessage(role="user", content="hello")]),
        CurrentUser(id="user-1", name="tester"),
    )

    assert graph.requests[0][2] == "conversation-1"
    assert graph.requests[0][3] is False


@pytest.mark.asyncio
async def test_chat_service_marks_run_cancelled_when_runtime_requests_cancel() -> None:
    class _CancelledRegistry:
        async def register(self, run_id: str, task) -> None:
            return None

        async def unregister(self, run_id: str, task) -> None:
            return None

        async def get_control_request(self, run_id: str) -> RuntimeControlRequest:
            return RuntimeControlRequest(action="cancel", reason="user cancelled")

    class _CancellingGraphRunner(_FakeGraphRunner):
        async def run_chat(
            self,
            request: ChatRequest,
            *,
            user_id: str | None = None,
            thread_id: str | None = None,
            resume: bool = False,
        ) -> ChatResponse:
            raise asyncio.CancelledError()

    service, _, _, _, agent_runs, _ = _build_service(
        graph_runner=_CancellingGraphRunner(),
        runtime_registry=_CancelledRegistry(),  # type: ignore[arg-type]
    )

    with pytest.raises(AppException) as exc_info:
        await service.chat(
            ChatRequest(messages=[ChatMessage(role="user", content="hello")]),
            CurrentUser(id="user-1", name="tester"),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.message == "Agent 运行已取消"
    assert agent_runs.items["run-1"].status == "cancelled"
    assert agent_runs.items["run-1"].metadata_["reason"] == "user cancelled"
    assert agent_runs.items["run-1"].output["status"] == "cancelled"


@pytest.mark.asyncio
async def test_chat_service_resume_uses_graph_agent_id_for_checkpoint_lookup() -> None:
    pending_human_input = PendingHumanInput(
        kind="form",
        title="补充路线规划信息",
        message="当前还缺少起点，请补充后继续路线规划。",
        fields=[
            {
                "name": "origin",
                "label": "起点",
                "type": "text",
                "required": True,
                "placeholder": "请输入起点",
                "options": [],
            }
        ],
        submit_label="继续规划路线",
        missing_fields=["origin"],
    )
    coordinator_graph = _FakeGraphRunner(pending_human_input=pending_human_input)
    route_graph = _ThreadAwareGraphRunner(available_threads=set())
    service, _, conversations, messages, agent_runs, _ = _build_service(
        graph_runner=coordinator_graph,
    )
    service.agent_registry = {
        "coordinator_agent": AgentDefinition(
            metadata=AgentMetadata(
                agent_id="coordinator_agent",
                name="协调入口",
                description="mock",
                version="0.1.0",
                capabilities=[],
            ),
            graph=object(),
        ),
        "route_planner_agent": AgentDefinition(
            metadata=AgentMetadata(
                agent_id="route_planner_agent",
                name="路线规划",
                description="mock",
                version="0.1.0",
                capabilities=[],
            ),
            graph=object(),
        ),
    }

    async def _resolve_graph_runner(agent_id: str) -> GraphRunner:
        raise AssertionError(f"unexpected async call for {agent_id}")

    route_runner = route_graph

    def _patched_resolve_graph_runner(agent_id: str):
        if agent_id == "coordinator_agent":
            return coordinator_graph
        if agent_id == "route_planner_agent":
            return route_runner
        raise AssertionError(f"unexpected agent id: {agent_id}")

    service._resolve_graph_runner = _patched_resolve_graph_runner  # type: ignore[method-assign]

    user = CurrentUser(id="user-1", name="tester")
    initial_response = await service.chat(
        ChatRequest(messages=[ChatMessage(role="user", content="我要去广东")]),
        user,
    )

    assert initial_response.pending_human_input is not None
    assert agent_runs.items["run-1"].status == "interrupted"
    agent_runs.items["run-1"].agent_id = "route_planner_agent"
    agent_runs.items["run-1"].metadata_["agent_id"] = "route_planner_agent"
    agent_runs.items["run-1"].metadata_["graph_agent_id"] = "coordinator_agent"

    resumed = await service.resume_chat(
        "run-1",
        user,
        {"origin": "深圳南山科技园"},
    )

    assert resumed is not None
    assert coordinator_graph.requests[-1][3] is True
    assert coordinator_graph.requests[-1][0].metadata["resume_payload"] == {
        "input": {"origin": "深圳南山科技园"}
    }
    assert route_graph.requests == []
    assert messages.items[-1].content == "Mock response: 我要去广东"
    assert conversations.items["conversation-1"].agent_id == "coordinator_agent"
