from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest

from app.api.dependencies import get_agent_run_service
from app.schemas.agent import AgentRunDetail, AgentRunList, AgentRunListItem, AgentStatus
from app.schemas.tool_call import ToolCallRead


class InMemoryAgentRunService:
    def __init__(self) -> None:
        self.items: dict[str, AgentStatus] = {}
        self.details: dict[str, AgentRunDetail] = {}

    async def list(
        self,
        user_id: str,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        conversation_id: str | None = None,
    ) -> AgentRunList:
        items = [detail for detail in self.details.values()]
        if status is not None:
            items = [detail for detail in items if detail.status == status]
        if conversation_id is not None:
            items = [detail for detail in items if detail.conversation_id == conversation_id]
        list_items = [
            AgentRunListItem(
                id=detail.id,
                conversation_id=detail.conversation_id,
                agent_id=detail.agent_id,
                status=detail.status,
                started_at=detail.started_at,
                updated_at=detail.updated_at,
                finished_at=detail.finished_at,
                duration_ms=detail.duration_ms,
                trace_id=detail.trace_id,
                error_message=detail.error_message,
                error_code=detail.error_code,
                interruption_reason=detail.interruption_reason,
            )
            for detail in items
        ]
        return AgentRunList(
            items=list_items[offset : offset + limit],
            total=len(list_items),
        )

    async def get(self, run_id: str, user_id: str) -> AgentRunDetail:
        return self.details[run_id]

    async def status(self, run_id: str | None, user_id: str) -> AgentStatus:
        if run_id is None:
            return AgentStatus(status="idle")
        return self.items.get(run_id, AgentStatus(status="idle", run_id=run_id))

    async def resume(
        self,
        run_id: str,
        payload: dict[str, Any],
        user_id: str,
        *,
        agent_id: str | None = None,
    ) -> AgentStatus:
        resolved_agent_id = agent_id or payload.get("agent_id") or "chat_agent"
        status = AgentStatus(
            status="running",
            run_id=run_id,
            agent_id=resolved_agent_id,
            metadata=dict(payload),
        )
        self.items[run_id] = status
        self.details[run_id] = AgentRunDetail(
            id=run_id,
            conversation_id=None,
            agent_id=resolved_agent_id,
            status="running",
            started_at=None,
            updated_at=None,
            finished_at=None,
            duration_ms=None,
            trace_id=payload.get("trace_id"),
            error_message=None,
            error_code=None,
            interruption_reason=None,
            input=dict(payload),
            output={},
            metadata=dict(payload),
        )
        return status

    async def interrupt(
        self,
        run_id: str,
        reason: str | None,
        user_id: str,
        *,
        agent_id: str | None = None,
    ) -> AgentStatus:
        status = AgentStatus(
            status="interrupted",
            run_id=run_id,
            agent_id=agent_id or self.items.get(run_id, AgentStatus()).agent_id,
            metadata={"reason": reason} if reason is not None else {},
        )
        self.items[run_id] = status
        existing = self.details.get(
            run_id,
            AgentRunDetail(
                id=run_id,
                conversation_id=None,
                agent_id=status.agent_id,
                status="interrupted",
                started_at=None,
                updated_at=None,
                finished_at=None,
                duration_ms=None,
                trace_id=None,
                error_message=None,
                error_code=None,
                interruption_reason=None,
                input={},
                output={},
                metadata={},
            ),
        )
        self.details[run_id] = existing.model_copy(
            update={
                "status": "interrupted",
                "agent_id": status.agent_id,
                "metadata": {"reason": reason} if reason is not None else {},
                "interruption_reason": reason,
            }
        )
        return status

    async def cancel(
        self,
        run_id: str,
        reason: str | None,
        user_id: str,
        *,
        agent_id: str | None = None,
    ) -> AgentStatus:
        status = AgentStatus(
            status="cancelled",
            run_id=run_id,
            agent_id=agent_id or self.items.get(run_id, AgentStatus()).agent_id,
            metadata={"reason": reason} if reason is not None else {},
        )
        self.items[run_id] = status
        existing = self.details.get(
            run_id,
            AgentRunDetail(
                id=run_id,
                conversation_id=None,
                agent_id=status.agent_id,
                status="cancelled",
                started_at=None,
                updated_at=None,
                finished_at=None,
                duration_ms=None,
                trace_id=None,
                error_message=None,
                error_code=None,
                interruption_reason=None,
                input={},
                output={},
                metadata={},
            ),
        )
        self.details[run_id] = existing.model_copy(
            update={
                "status": "cancelled",
                "agent_id": status.agent_id,
                "metadata": {"reason": reason} if reason is not None else {},
                "interruption_reason": reason,
            }
        )
        return status


@pytest.fixture
def agent_run_service(client) -> Generator[InMemoryAgentRunService, None, None]:
    service = InMemoryAgentRunService()
    client.app.dependency_overrides[get_agent_run_service] = lambda: service
    try:
        yield service
    finally:
        client.app.dependency_overrides.pop(get_agent_run_service, None)


def test_agent_status_endpoint(client, agent_run_service: InMemoryAgentRunService) -> None:
    response = client.get("/v1/agent/status", params={"run_id": "run-1"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["run_id"] == "run-1"
    assert payload["data"]["status"] == "idle"


def test_agent_run_list_and_detail_endpoints(
    client,
    agent_run_service: InMemoryAgentRunService,
) -> None:
    client.post(
        "/v1/agent/resume",
        json={
            "run_id": "run-1",
            "agent_id": "code_agent",
            "input": {"trace_id": "trace-1", "approved": True},
        },
    )
    agent_run_service.details["run-1"] = agent_run_service.details["run-1"].model_copy(
        update={
            "conversation_id": "conversation-1",
            "agent_id": "code_agent",
            "tool_calls": [
                ToolCallRead(
                    id="tool-call-1",
                    agent_run_id="run-1",
                    tool_name="search",
                    status="completed",
                    input={"query": "trace-1"},
                    output={"hits": 1},
                    metadata={"provider": "mock-tool"},
                )
            ],
        }
    )
    agent_run_service.items["run-2"] = AgentStatus(status="failed", run_id="run-2", metadata={})
    agent_run_service.details["run-2"] = AgentRunDetail(
        id="run-2",
        conversation_id="conversation-2",
        agent_id="chat_agent",
        status="failed",
        started_at=None,
        updated_at=None,
        finished_at=None,
        duration_ms=None,
        trace_id=None,
        error_message="boom",
        error_code="S00001",
        interruption_reason=None,
        input={},
        output={"error": "boom", "code": "S00001"},
        metadata={},
    )

    list_response = client.get("/v1/agent/runs")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["success"] is True
    assert list_payload["data"]["total"] == 2
    assert list_payload["data"]["items"][0]["id"] == "run-1"
    assert list_payload["data"]["items"][0]["agent_id"] == "code_agent"
    assert list_payload["data"]["items"][0]["trace_id"] == "trace-1"

    filtered_response = client.get(
        "/v1/agent/runs",
        params={"status": "failed", "conversation_id": "conversation-2"},
    )
    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert filtered_payload["data"]["total"] == 1
    assert filtered_payload["data"]["items"][0]["id"] == "run-2"
    assert filtered_payload["data"]["items"][0]["error_code"] == "S00001"

    detail_response = client.get("/v1/agent/runs/run-1")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["success"] is True
    assert detail_payload["data"]["id"] == "run-1"
    assert detail_payload["data"]["agent_id"] == "code_agent"
    assert detail_payload["data"]["input"] == {"trace_id": "trace-1", "approved": True}
    assert detail_payload["data"]["finished_at"] is None
    assert detail_payload["data"]["duration_ms"] is None
    assert detail_payload["data"]["tool_calls"][0]["tool_name"] == "search"


def test_agent_resume_endpoint(client, agent_run_service: InMemoryAgentRunService) -> None:
    response = client.post(
        "/v1/agent/resume",
        json={"run_id": "run-1", "agent_id": "code_agent", "input": {"approved": True}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "running"
    assert payload["data"]["agent_id"] == "code_agent"
    assert payload["data"]["metadata"] == {"approved": True}

    status_response = client.get("/v1/agent/status", params={"run_id": "run-1"})
    assert status_response.json()["data"]["status"] == "running"


def test_agent_interrupt_endpoint(client, agent_run_service: InMemoryAgentRunService) -> None:
    response = client.post(
        "/v1/agent/interrupt",
        json={"run_id": "run-1", "agent_id": "chat_agent", "reason": "manual review"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "interrupted"
    assert payload["data"]["agent_id"] == "chat_agent"
    assert payload["data"]["metadata"]["reason"] == "manual review"

    detail_response = client.get("/v1/agent/runs/run-1")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["interruption_reason"] == "manual review"


def test_agent_cancel_endpoint(client, agent_run_service: InMemoryAgentRunService) -> None:
    response = client.post(
        "/v1/agent/cancel",
        json={"run_id": "run-2", "agent_id": "chat_agent", "reason": "user stop"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "cancelled"
    assert payload["data"]["agent_id"] == "chat_agent"
    assert payload["data"]["metadata"]["reason"] == "user stop"

    detail_response = client.get("/v1/agent/runs/run-2")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["interruption_reason"] == "user stop"
