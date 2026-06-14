from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest

from app.audit.enums import AuditAction, AuditResult
from app.audit.schemas import AuditEvent
from app.audit.service import AuditService
from app.common.exceptions import AppException
from app.db.models.message import Message
from app.schemas.conversation import ConversationCreate
from app.schemas.tool_call import ToolCallRead
from app.services.conversation_service import ConversationService


class _FakeSession:
    @asynccontextmanager
    async def begin(self):
        yield self


class _FakeConversation:
    def __init__(
        self,
        *,
        id: str,
        user_id: str,
        agent_id: str,
        title: str | None,
        metadata_: dict,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.agent_id = agent_id
        self.title = title
        self.metadata_ = metadata_
        self.created_at = created_at or datetime.now(timezone.utc)
        self.deleted_at: datetime | None = None


class _FakeConversationRepository:
    def __init__(self) -> None:
        self.items: dict[str, _FakeConversation] = {}

    async def add(self, conversation) -> _FakeConversation:
        conversation.id = conversation.id or f"conversation-{len(self.items) + 1}"
        if conversation.created_at is None:
            conversation.created_at = datetime.now(timezone.utc)
        self.items[conversation.id] = conversation
        return conversation

    async def list_by_user(self, user_id: str, *, limit: int = 20, offset: int = 0):
        items = [
            item
            for item in self.items.values()
            if item.user_id == user_id and item.deleted_at is None
        ]
        return items[offset : offset + limit]

    async def count_by_user(self, user_id: str) -> int:
        return len(
            [
                item
                for item in self.items.values()
                if item.user_id == user_id and item.deleted_at is None
            ]
        )

    async def get_by_id_for_user(self, conversation_id: str, user_id: str):
        item = self.items.get(conversation_id)
        if item is None or item.user_id != user_id or item.deleted_at is not None:
            return None
        return item

    async def soft_delete(self, conversation):
        conversation.deleted_at = datetime.now(timezone.utc)
        return conversation


class _FakeMessageRepository:
    def __init__(self) -> None:
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
        items = [
            item
            for item in self.items
            if item.conversation_id == conversation_id and item.deleted_at is None
        ]
        return items[offset : offset + limit]


class _FakeAgentRun:
    def __init__(
        self,
        *,
        id: str,
        conversation_id: str,
        user_id: str,
        agent_id: str,
        output: dict,
        created_at: datetime,
    ) -> None:
        self.id = id
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.agent_id = agent_id
        self.status = "completed"
        self.output = output
        self.metadata_: dict = {}
        self.created_at = created_at
        self.updated_at = created_at


class _FakeAgentRunRepository:
    def __init__(self, items: list[_FakeAgentRun]) -> None:
        self.items = items

    async def list_by_user(
        self,
        user_id: str,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        conversation_id: str | None = None,
    ) -> list[_FakeAgentRun]:
        items = [
            item
            for item in self.items
            if item.user_id == user_id
            and (conversation_id is None or item.conversation_id == conversation_id)
            and (status is None or item.status == status)
        ]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return items[offset : offset + limit]


class _FakeToolCallService:
    def __init__(self, items_by_run: dict[str, list[ToolCallRead]]) -> None:
        self.items_by_run = items_by_run

    async def list_for_runs(
        self,
        agent_run_ids: list[str],
    ) -> dict[str, list[ToolCallRead]]:
        return {
            run_id: list(self.items_by_run.get(run_id, []))
            for run_id in agent_run_ids
        }


class _FakeAuditWriter:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def write(self, event: AuditEvent) -> None:
        self.events.append(event)


@pytest.mark.asyncio
async def test_conversation_service_crud_scaffold() -> None:
    message_repository = _FakeMessageRepository()
    audit_writer = _FakeAuditWriter()
    service = ConversationService(
        session=_FakeSession(),  # type: ignore[arg-type]
        conversation_repository=_FakeConversationRepository(),  # type: ignore[arg-type]
        message_repository=message_repository,  # type: ignore[arg-type]
        audit_service=AuditService(writer=audit_writer),
    )

    created = await service.create(
        ConversationCreate(title="demo", agent_id="code_agent"),
        "user-1",
    )
    assert created.id == "conversation-1"
    assert created.title == "demo"
    assert created.user_id == "user-1"
    assert created.agent_id == "code_agent"

    listed = await service.list("user-1")
    assert listed.total == 1
    assert listed.items[0].id == created.id

    await message_repository.add(
        Message(
            conversation_id=created.id,
            role="user",
            content="hello",
            metadata_={},
        )
    )
    await message_repository.add(
        Message(
            conversation_id=created.id,
            role="assistant",
            content="world",
            metadata_={"tool": "mock"},
        )
    )

    fetched = await service.get(created.id, "user-1")
    assert fetched.id == created.id
    assert [message.role for message in fetched.messages] == ["user", "assistant"]
    assert fetched.messages[1].metadata == {"tool": "mock"}

    deleted = await service.delete(created.id, "user-1")
    assert deleted == {"id": created.id, "status": "deleted"}
    assert len(audit_writer.events) == 1
    assert audit_writer.events[0].action == AuditAction.DELETE
    assert audit_writer.events[0].result == AuditResult.SUCCESS
    assert audit_writer.events[0].resource_id == created.id
    assert audit_writer.events[0].agent_id == "code_agent"

    listed_after_delete = await service.list("user-1")
    assert listed_after_delete.total == 0


@pytest.mark.asyncio
async def test_conversation_service_raises_not_found_for_unknown_conversation() -> None:
    service = ConversationService(
        session=_FakeSession(),  # type: ignore[arg-type]
        conversation_repository=_FakeConversationRepository(),  # type: ignore[arg-type]
        message_repository=_FakeMessageRepository(),  # type: ignore[arg-type]
    )

    with pytest.raises(AppException) as exc_info:
        await service.get("missing", "user-1")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_conversation_service_returns_run_traces_for_each_assistant_message() -> None:
    conversation_repository = _FakeConversationRepository()
    message_repository = _FakeMessageRepository()
    created = await conversation_repository.add(
        _FakeConversation(
            id="conversation-1",
            user_id="user-1",
            agent_id="coordinator_agent",
            title="demo",
            metadata_={},
        )
    )
    await message_repository.add(
        Message(
            conversation_id=created.id,
            role="assistant",
            content="first answer",
            metadata_={"message_id": "message-1"},
        )
    )
    await message_repository.add(
        Message(
            conversation_id=created.id,
            role="assistant",
            content="second answer",
            metadata_={"message_id": "message-2"},
        )
    )
    now = datetime.now(timezone.utc)
    runs = [
        _FakeAgentRun(
            id="run-1",
            conversation_id=created.id,
            user_id="user-1",
            agent_id="chat_agent",
            output={
                "message": {
                    "content": "first answer",
                    "metadata": {"message_id": "message-1"},
                },
                "metadata": {"route_decision": {"confidence": 0.9}},
            },
            created_at=now,
        ),
        _FakeAgentRun(
            id="run-2",
            conversation_id=created.id,
            user_id="user-1",
            agent_id="chat_agent",
            output={
                "message": {
                    "content": "second answer",
                    "metadata": {"message_id": "message-2"},
                },
                "metadata": {},
            },
            created_at=now + timedelta(microseconds=1),
        ),
    ]
    tool_call = ToolCallRead(
        id="tool-1",
        agent_run_id="run-1",
        tool_name="search",
        status="success",
        input={"query": "hello"},
        output={"hits": 1},
        metadata={"tool_call_id": "call-1"},
    )
    duplicated_tool_call = tool_call.model_copy(
        update={
            "id": "tool-2",
            "agent_run_id": "run-2",
        }
    )
    service = ConversationService(
        session=_FakeSession(),  # type: ignore[arg-type]
        conversation_repository=conversation_repository,  # type: ignore[arg-type]
        message_repository=message_repository,  # type: ignore[arg-type]
        agent_run_repository=_FakeAgentRunRepository(runs),  # type: ignore[arg-type]
        tool_call_service=_FakeToolCallService(
            {
                "run-1": [tool_call],
                "run-2": [duplicated_tool_call],
            }
        ),  # type: ignore[arg-type]
    )

    detail = await service.get(created.id, "user-1")

    assert detail.latest_run is not None
    assert detail.latest_run.id == "run-2"
    assert [trace.id for trace in detail.run_traces] == ["run-1", "run-2"]
    assert detail.run_traces[0].assistant_message_id == "message-1"
    assert detail.run_traces[0].tool_calls[0].output == {"hits": 1}
    assert detail.run_traces[1].tool_calls == []
