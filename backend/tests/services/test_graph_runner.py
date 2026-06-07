from __future__ import annotations

import pytest

from app.common.exceptions import LLMException
from app.graph.builder import build_graph
from app.schemas.chat import ChatMessage, ChatRequest
from app.services.graph_runner import GraphRunner


class _GraphWithToolCalls:
    async def ainvoke(self, state):
        return {
            "conversation_id": state["conversation_id"],
            "messages": [
                *state["messages"],
                {"role": "assistant", "content": "Used search tool"},
            ],
            "tool_calls": [
                {
                    "tool_name": "search",
                    "status": "completed",
                    "input": {"query": "hello"},
                    "output": {"hits": 2},
                    "metadata": {"provider": "mock-tool"},
                }
            ],
            "metadata": {"model": "mock"},
        }


@pytest.mark.asyncio
async def test_graph_runner_returns_mock_response() -> None:
    runner = GraphRunner(build_graph(llm=None))
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="hello")],
    )

    response = await runner.run_chat(request)

    assert response.conversation_id == "conversation-1"
    assert response.message.role == "assistant"
    assert "Mock response" in response.message.content


@pytest.mark.asyncio
async def test_graph_runner_extracts_tool_calls_from_graph_result() -> None:
    runner = GraphRunner(_GraphWithToolCalls())
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="hello")],
    )

    response = await runner.run_chat(request)

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].tool_name == "search"
    assert response.tool_calls[0].output == {"hits": 2}


@pytest.mark.asyncio
async def test_graph_runner_raises_when_llm_is_marked_unavailable() -> None:
    runner = GraphRunner(build_graph(llm=None), llm_available=False)
    request = ChatRequest(messages=[ChatMessage(role="user", content="hello")])

    with pytest.raises(LLMException):
        await runner.run_chat(request)
