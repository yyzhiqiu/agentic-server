from __future__ import annotations

from collections.abc import AsyncIterator, Generator
import json

import pytest

from app.api.dependencies import get_chat_service
from app.common.exceptions import LLMException
from app.core.security import CurrentUser
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse
from app.services.graph_runner import GraphRunner


class InMemoryChatService:
    def __init__(self) -> None:
        self.raise_llm_error = False

    async def chat(self, request: ChatRequest, user: CurrentUser) -> ChatResponse:
        if self.raise_llm_error:
            raise LLMException("LLM_API_KEY is not configured", data={"provider": "mock-disabled"})

        assistant = ChatMessage(role="assistant", content=f"Mock response: {request.messages[-1].content}")
        return ChatResponse(
            conversation_id=request.conversation_id or "conversation-1",
            message=assistant,
            messages=[*request.messages, assistant],
            metadata={"run_id": "run-1"},
        )

    async def stream_chat(
        self,
        request: ChatRequest,
        user: CurrentUser,
    ) -> AsyncIterator[str]:
        if self.raise_llm_error:
            yield GraphRunner.format_sse(
                "error",
                {
                    "type": "error",
                    "content": "LLM_API_KEY is not configured",
                    "data": {
                        "provider": "mock-disabled",
                        "code": "L00001",
                    },
                },
            )
            return

        response = await self.chat(request, user)
        yield GraphRunner.format_sse(
            "start",
            {
                "type": "start",
                "content": None,
                "data": {
                    "conversation_id": response.conversation_id,
                    "run_id": response.metadata["run_id"],
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
def chat_service(client) -> Generator[InMemoryChatService, None, None]:
    service = InMemoryChatService()
    client.app.dependency_overrides[get_chat_service] = lambda: service
    try:
        yield service
    finally:
        client.app.dependency_overrides.pop(get_chat_service, None)


def test_chat_returns_llm_configuration_error(client, chat_service: InMemoryChatService) -> None:
    chat_service.raise_llm_error = True
    response = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 503
    payload = response.json()
    assert payload["success"] is False
    assert payload["code"] == "L00001"
    assert payload["message"] == "LLM_API_KEY is not configured"


def test_chat_stream_returns_sse_error_when_llm_is_missing(
    client,
    chat_service: InMemoryChatService,
) -> None:
    chat_service.raise_llm_error = True
    response = client.post(
        "/v1/chat/stream",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: error" in response.text
    assert "LLM_API_KEY is not configured" in response.text


def test_chat_stream_can_return_mock_response(
    client,
    chat_service: InMemoryChatService,
) -> None:
    response = client.post(
        "/v1/chat/stream",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 200
    assert "event: start" in response.text
    assert "event: message" in response.text
    assert "event: done" in response.text

    done_chunk = next(chunk for chunk in response.text.split("\n\n") if "event: done" in chunk)
    payload = json.loads(done_chunk.split("data: ", 1)[1])
    assert payload["data"]["conversation_id"] == "conversation-1"
    assert payload["data"]["metadata"]["run_id"] == "run-1"


def test_chat_can_return_mock_response_when_graph_is_prebuilt(
    client,
    chat_service: InMemoryChatService,
) -> None:
    response = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["conversation_id"] == "conversation-1"
    assert payload["data"]["message"]["role"] == "assistant"
    assert "Mock response" in payload["data"]["message"]["content"]
    assert payload["data"]["metadata"]["run_id"] == "run-1"
