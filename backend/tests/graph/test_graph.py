"""通用聊天 Agent graph 的基础行为测试。"""

from __future__ import annotations

import pytest

from app.graph.chat_agent.builder import build_chat_agent
from app.schemas.chat import ChatMessage, ChatRequest
from app.services.graph_runner import GraphRunner


@pytest.mark.asyncio
async def test_graph_returns_mock_response() -> None:
    graph = build_chat_agent(llm=None)
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
    runner = GraphRunner(build_chat_agent(llm=None), agent_id="chat_agent")
    request = ChatRequest(messages=[ChatMessage(role="user", content="hello")])
    events = [event async for event in runner.stream_chat(request)]
    assert any("event: start" in event for event in events)
    assert any("event: message" in event and "Mock response" in event for event in events)
    assert any("event: done" in event for event in events)
