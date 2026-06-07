from __future__ import annotations

import pytest

from app.graph.builder import build_graph
from app.schemas.chat import ChatMessage, ChatRequest
from app.services.graph_runner import GraphRunner


@pytest.mark.asyncio
async def test_graph_returns_mock_response() -> None:
    graph = build_graph(llm=None)
    result = await graph.ainvoke(
        {
            "messages": [{"role": "user", "content": "hello"}],
            "user_id": "test-user",
            "conversation_id": "test-conversation",
            "metadata": {},
        }
    )
    assert result["messages"][-1]["role"] == "assistant"
    assert "Mock response" in result["messages"][-1]["content"]


@pytest.mark.asyncio
async def test_graph_runner_streams_mock_response_when_graph_is_used_directly() -> None:
    runner = GraphRunner(build_graph(llm=None))
    request = ChatRequest(messages=[ChatMessage(role="user", content="hello")])
    events = [event async for event in runner.stream_chat(request)]
    assert any("event: start" in event for event in events)
    assert any("event: message" in event and "Mock response" in event for event in events)
    assert any("event: done" in event for event in events)
