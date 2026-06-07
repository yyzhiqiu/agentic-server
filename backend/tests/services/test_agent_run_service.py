from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import pytest

from app.audit.enums import AuditAction, AuditResult
from app.audit.schemas import AuditEvent
from app.audit.service import AuditService
from app.common.exceptions import AppException
from app.schemas.tool_call import ToolCallRead
from app.services.agent_run_service import AgentRunService


class _FakeSession:
    @asynccontextmanager
    async def begin(self):
        yield self

    async def flush(self) -> None:
        return None


class _FakeAgentRun:
    def __init__(
        self,
        *,
        id: str,
        agent_id: str,
        user_id: str,
        status: str,
        input: dict[str, Any],
        output: dict[str, Any],
        metadata_: dict[str, Any],
        conversation_id: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.agent_id = agent_id
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.status = status
        self.input = input
        self.output = output
        self.metadata_ = metadata_
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or self.created_at


class _FakeAgentRunRepository:
    def __init__(self) -> None:
        self.items: dict[str, _FakeAgentRun] = {}

    async def add(self, agent_run) -> _FakeAgentRun:
        if getattr(agent_run, "created_at", None) is None:
            agent_run.created_at = datetime.now(timezone.utc)
        if getattr(agent_run, "updated_at", None) is None:
            agent_run.updated_at = agent_run.created_at
        self.items[agent_run.id] = agent_run
        return agent_run

    async def get_by_id_for_user(self, run_id: str, user_id: str) -> _FakeAgentRun | None:
        item = self.items.get(run_id)
        if item is None or item.user_id != user_id:
            return None
        return item

    async def list_by_user(
        self,
        user_id: str,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        conversation_id: str | None = None,
    ) -> list[_FakeAgentRun]:
        items = [item for item in self.items.values() if item.user_id == user_id]
        if status is not None:
            items = [item for item in items if item.status == status]
        if conversation_id is not None:
            items = [item for item in items if item.conversation_id == conversation_id]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return items[offset : offset + limit]

    async def count_by_user(
        self,
        user_id: str,
        *,
        status: str | None = None,
        conversation_id: str | None = None,
    ) -> int:
        items = [item for item in self.items.values() if item.user_id == user_id]
        if status is not None:
            items = [item for item in items if item.status == status]
        if conversation_id is not None:
            items = [item for item in items if item.conversation_id == conversation_id]
        return len(items)


class _FakeToolCallService:
    def __init__(self) -> None:
        self.items_by_run: dict[str, list[ToolCallRead]] = {}

    async def list_for_run(self, agent_run_id: str) -> list[ToolCallRead]:
        return list(self.items_by_run.get(agent_run_id, []))


class _FakeAuditWriter:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def write(self, event: AuditEvent) -> None:
        self.events.append(event)


@pytest.mark.asyncio
async def test_agent_run_service_creates_and_reads_run_status() -> None:
    audit_writer = _FakeAuditWriter()
    service = AgentRunService(
        session=_FakeSession(),  # type: ignore[arg-type]
        agent_run_repository=_FakeAgentRunRepository(),  # type: ignore[arg-type]
        audit_service=AuditService(writer=audit_writer),
    )

    created = await service.resume(
        "run-1",
        {"approved": True},
        "user-1",
        agent_id="code_agent",
    )
    assert created.status == "running"
    assert created.run_id == "run-1"
    assert created.agent_id == "code_agent"
    assert created.metadata == {"approved": True}
    assert len(audit_writer.events) == 1
    assert audit_writer.events[0].action == AuditAction.AGENT_RESUME
    assert audit_writer.events[0].result == AuditResult.SUCCESS
    assert audit_writer.events[0].actor_id == "user-1"
    assert audit_writer.events[0].resource_type == "agent_run"
    assert audit_writer.events[0].resource_id == "run-1"
    assert audit_writer.events[0].metadata == {
        "status": "running",
        "input": {"approved": True},
    }

    fetched = await service.status("run-1", "user-1")
    assert fetched.status == "running"
    assert fetched.run_id == "run-1"
    assert fetched.agent_id == "code_agent"


@pytest.mark.asyncio
async def test_agent_run_service_interrupts_existing_run() -> None:
    audit_writer = _FakeAuditWriter()
    service = AgentRunService(
        session=_FakeSession(),  # type: ignore[arg-type]
        agent_run_repository=_FakeAgentRunRepository(),  # type: ignore[arg-type]
        audit_service=AuditService(writer=audit_writer),
    )

    await service.resume("run-1", {"approved": True}, "user-1", agent_id="chat_agent")
    interrupted = await service.interrupt(
        "run-1",
        "manual review",
        "user-1",
        agent_id="chat_agent",
    )

    assert interrupted.status == "interrupted"
    assert interrupted.agent_id == "chat_agent"
    assert interrupted.metadata == {"reason": "manual review"}

    detail = await service.get("run-1", "user-1")
    assert detail.interruption_reason == "manual review"
    assert detail.error_message is None
    assert detail.error_code is None
    assert audit_writer.events[-1].action == AuditAction.AGENT_INTERRUPT
    assert audit_writer.events[-1].result == AuditResult.SUCCESS
    assert audit_writer.events[-1].resource_id == "run-1"
    assert audit_writer.events[-1].metadata == {
        "status": "interrupted",
        "reason": "manual review",
    }


@pytest.mark.asyncio
async def test_agent_run_service_returns_idle_for_unknown_run() -> None:
    service = AgentRunService(
        session=_FakeSession(),  # type: ignore[arg-type]
        agent_run_repository=_FakeAgentRunRepository(),  # type: ignore[arg-type]
    )

    status = await service.status("missing", "user-1")
    assert status.status == "idle"
    assert status.run_id == "missing"


@pytest.mark.asyncio
async def test_agent_run_service_lists_and_reads_user_runs() -> None:
    service = AgentRunService(
        session=_FakeSession(),  # type: ignore[arg-type]
        agent_run_repository=_FakeAgentRunRepository(),  # type: ignore[arg-type]
    )

    await service.resume("run-1", {"trace_id": "trace-1"}, "user-1", agent_id="chat_agent")
    await service.resume("run-2", {"trace_id": "trace-2"}, "user-1", agent_id="code_agent")

    listed = await service.list("user-1")
    assert listed.total == 2
    assert listed.items[0].id == "run-2"
    assert listed.items[0].agent_id == "code_agent"
    assert listed.items[0].trace_id == "trace-2"

    detail = await service.get("run-1", "user-1")
    assert detail.id == "run-1"
    assert detail.agent_id == "chat_agent"
    assert detail.input == {"trace_id": "trace-1"}
    assert detail.metadata == {"trace_id": "trace-1"}


@pytest.mark.asyncio
async def test_agent_run_service_exposes_terminal_timestamps_and_duration() -> None:
    repository = _FakeAgentRunRepository()
    created_at = datetime(2026, 6, 7, 10, 0, 0, tzinfo=timezone.utc)
    updated_at = datetime(2026, 6, 7, 10, 0, 5, 500000, tzinfo=timezone.utc)
    repository.items["run-1"] = _FakeAgentRun(
        id="run-1",
        agent_id="code_agent",
        user_id="user-1",
        status="completed",
        input={"trace_id": "trace-1"},
        output={"ok": True},
        metadata_={"trace_id": "trace-1"},
        created_at=created_at,
        updated_at=updated_at,
    )
    service = AgentRunService(
        session=_FakeSession(),  # type: ignore[arg-type]
        agent_run_repository=repository,  # type: ignore[arg-type]
    )

    listed = await service.list("user-1")
    assert listed.items[0].agent_id == "code_agent"
    assert listed.items[0].updated_at == updated_at
    assert listed.items[0].finished_at == updated_at
    assert listed.items[0].duration_ms == 5500

    detail = await service.get("run-1", "user-1")
    assert detail.updated_at == updated_at
    assert detail.finished_at == updated_at
    assert detail.duration_ms == 5500


@pytest.mark.asyncio
async def test_agent_run_service_exposes_failed_run_reason_summary() -> None:
    repository = _FakeAgentRunRepository()
    repository.items["run-1"] = _FakeAgentRun(
        id="run-1",
        agent_id="chat_agent",
        user_id="user-1",
        status="failed",
        input={"trace_id": "trace-1"},
        output={"error": "LLM_API_KEY is not configured", "code": "L00001"},
        metadata_={"trace_id": "trace-1"},
    )
    service = AgentRunService(
        session=_FakeSession(),  # type: ignore[arg-type]
        agent_run_repository=repository,  # type: ignore[arg-type]
    )

    listed = await service.list("user-1")
    assert listed.items[0].agent_id == "chat_agent"
    assert listed.items[0].error_message == "LLM_API_KEY is not configured"
    assert listed.items[0].error_code == "L00001"
    assert listed.items[0].interruption_reason is None

    detail = await service.get("run-1", "user-1")
    assert detail.error_message == "LLM_API_KEY is not configured"
    assert detail.error_code == "L00001"


@pytest.mark.asyncio
async def test_agent_run_service_filters_runs_by_status_and_conversation() -> None:
    repository = _FakeAgentRunRepository()
    repository.items["run-1"] = _FakeAgentRun(
        id="run-1",
        agent_id="chat_agent",
        user_id="user-1",
        conversation_id="conversation-1",
        status="completed",
        input={},
        output={},
        metadata_={},
        created_at=datetime(2026, 6, 7, 10, 0, 0, tzinfo=timezone.utc),
    )
    repository.items["run-2"] = _FakeAgentRun(
        id="run-2",
        agent_id="code_agent",
        user_id="user-1",
        conversation_id="conversation-2",
        status="failed",
        input={},
        output={"error": "boom", "code": "S00001"},
        metadata_={},
        created_at=datetime(2026, 6, 7, 10, 0, 1, tzinfo=timezone.utc),
    )
    repository.items["run-3"] = _FakeAgentRun(
        id="run-3",
        agent_id="code_agent",
        user_id="user-1",
        conversation_id="conversation-1",
        status="failed",
        input={},
        output={"error": "bad request", "code": "A00001"},
        metadata_={},
        created_at=datetime(2026, 6, 7, 10, 0, 2, tzinfo=timezone.utc),
    )
    service = AgentRunService(
        session=_FakeSession(),  # type: ignore[arg-type]
        agent_run_repository=repository,  # type: ignore[arg-type]
    )

    filtered = await service.list(
        "user-1",
        status="failed",
        conversation_id="conversation-1",
    )

    assert filtered.total == 1
    assert [item.id for item in filtered.items] == ["run-3"]
    assert filtered.items[0].agent_id == "code_agent"


@pytest.mark.asyncio
async def test_agent_run_service_get_raises_not_found_for_unknown_run() -> None:
    service = AgentRunService(
        session=_FakeSession(),  # type: ignore[arg-type]
        agent_run_repository=_FakeAgentRunRepository(),  # type: ignore[arg-type]
    )

    with pytest.raises(AppException) as exc_info:
        await service.get("missing", "user-1")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_agent_run_service_includes_tool_calls_in_detail() -> None:
    repository = _FakeAgentRunRepository()
    repository.items["run-1"] = _FakeAgentRun(
        id="run-1",
        agent_id="chat_agent",
        user_id="user-1",
        status="completed",
        input={},
        output={},
        metadata_={},
    )
    tool_call_service = _FakeToolCallService()
    tool_call_service.items_by_run["run-1"] = [
        ToolCallRead(
            id="tool-call-1",
            agent_run_id="run-1",
            tool_name="search",
            status="completed",
            input={"query": "hello"},
            output={"hits": 2},
            metadata={"provider": "mock-tool"},
        )
    ]
    service = AgentRunService(
        session=_FakeSession(),  # type: ignore[arg-type]
        agent_run_repository=repository,  # type: ignore[arg-type]
        tool_call_service=tool_call_service,  # type: ignore[arg-type]
    )

    detail = await service.get("run-1", "user-1")

    assert detail.agent_id == "chat_agent"
    assert len(detail.tool_calls) == 1
    assert detail.tool_calls[0].tool_name == "search"
    assert detail.tool_calls[0].output == {"hits": 2}
