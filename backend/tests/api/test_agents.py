from __future__ import annotations

from collections.abc import AsyncIterator, Generator
import json

import pytest

from app.api.dependencies import get_agent_service, get_chat_service
from app.core.security import CurrentUser
from app.graph.chat_agent.metadata import CHAT_AGENT_METADATA
from app.graph.code_agent.metadata import CODE_AGENT_METADATA
from app.graph.default import DEFAULT_AGENT_ID
from app.graph.types import AgentDefinition
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse
from app.services.agent_service import AgentService
from app.services.graph_runner import GraphRunner


class InMemoryAgentChatService:
    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id

    async def chat(self, request: ChatRequest, user: CurrentUser) -> ChatResponse:
        assistant = ChatMessage(
            role="assistant",
            content=f"{self.agent_id} mock response: {request.messages[-1].content}",
        )
        return ChatResponse(
            conversation_id=request.conversation_id or "conversation-1",
            message=assistant,
            messages=[*request.messages, assistant],
            metadata={"run_id": "run-1", "agent_id": self.agent_id},
        )

    async def stream_chat(
        self,
        request: ChatRequest,
        user: CurrentUser,
    ) -> AsyncIterator[str]:
        response = await self.chat(request, user)
        yield GraphRunner.format_sse(
            "start",
            {
                "type": "start",
                "content": None,
                "data": {
                    "conversation_id": response.conversation_id,
                    "run_id": response.metadata["run_id"],
                    "agent_id": self.agent_id,
                },
            },
        )
        yield GraphRunner.format_sse(
            "message",
            {
                "type": "message",
                "content": response.message.content,
                "data": {
                    "conversation_id": response.conversation_id,
                    "run_id": response.metadata["run_id"],
                    "agent_id": self.agent_id,
                },
            },
        )
        yield GraphRunner.format_sse(
            "done",
            {
                "type": "done",
                "content": None,
                "data": response.model_dump(),
            },
        )


@pytest.fixture
def agent_services(client) -> Generator[None, None, None]:
    registry = {
        CHAT_AGENT_METADATA.agent_id: AgentDefinition(
            metadata=CHAT_AGENT_METADATA,
            graph=object(),
        ),
        CODE_AGENT_METADATA.agent_id: AgentDefinition(
            metadata=CODE_AGENT_METADATA,
            graph=object(),
        ),
    }
    service = AgentService(agent_registry=registry)

    def override_chat_service(agent_id: str = DEFAULT_AGENT_ID) -> InMemoryAgentChatService:
        return InMemoryAgentChatService(agent_id)

    client.app.dependency_overrides[get_agent_service] = lambda: service
    client.app.dependency_overrides[get_chat_service] = override_chat_service
    try:
        yield
    finally:
        client.app.dependency_overrides.pop(get_agent_service, None)
        client.app.dependency_overrides.pop(get_chat_service, None)


def test_list_agents_returns_registered_metadata(client, agent_services) -> None:
    response = client.get("/v1/agents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert [item["agent_id"] for item in payload["data"]] == ["chat_agent", "code_agent"]


def test_get_agent_returns_single_metadata(client, agent_services) -> None:
    response = client.get("/v1/agents/code_agent")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["agent_id"] == "code_agent"
    assert payload["data"]["capabilities"] == [
        "code_explain",
        "code_review",
        "code_generation",
    ]


def test_get_agent_returns_unified_not_found_error(client, agent_services) -> None:
    response = client.get("/v1/agents/missing_agent")

    assert response.status_code == 404
    payload = response.json()
    assert payload["success"] is False
    assert payload["code"] == "A00004"
    assert payload["data"]["agent_id"] == "missing_agent"


def test_default_chat_route_uses_chat_agent(client, agent_services) -> None:
    response = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["metadata"]["agent_id"] == "chat_agent"
    assert payload["data"]["message"]["content"].startswith("chat_agent mock response")


def test_agent_chat_route_uses_selected_agent(client, agent_services) -> None:
    response = client.post(
        "/v1/agents/code_agent/chat",
        json={"messages": [{"role": "user", "content": "explain this code"}]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["metadata"]["agent_id"] == "code_agent"
    assert payload["data"]["message"]["content"].startswith("code_agent mock response")


def test_agent_stream_route_uses_selected_agent(client, agent_services) -> None:
    response = client.post(
        "/v1/agents/code_agent/chat/stream",
        json={"messages": [{"role": "user", "content": "review this code"}]},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: start" in response.text
    assert "event: message" in response.text
    assert "code_agent mock response" in response.text

    done_chunk = next(chunk for chunk in response.text.split("\n\n") if "event: done" in chunk)
    payload = json.loads(done_chunk.split("data: ", 1)[1])
    assert payload["data"]["metadata"]["agent_id"] == "code_agent"

