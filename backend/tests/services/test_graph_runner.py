"""图执行适配器的基础行为测试。"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.common.exceptions import LLMException
from app.graph.chat_agent.builder import build_chat_agent
from app.schemas.chat import ChatMessage, ChatRequest
from app.services.graph_runner import GraphRunner


class _GraphWithToolCalls:
    async def ainvoke(self, state, **_: object):
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


class _GraphCapturingConfig:
    def __init__(self) -> None:
        self.received_state = None
        self.received_kwargs: dict[str, object] = {}

    async def ainvoke(self, state, **kwargs: object):
        self.received_state = state
        self.received_kwargs = kwargs
        return {
            "conversation_id": "conversation-1",
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "ok"},
            ],
            "metadata": {"model": "mock"},
        }


class _GraphWithMessageToolCalls:
    async def ainvoke(self, state, **_: object):
        return {
            "conversation_id": state["conversation_id"],
            "messages": [
                *state["messages"],
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "get_time",
                            "args": {"query": "now"},
                            "id": "call_1",
                            "type": "tool_call",
                        }
                    ],
                ),
                ToolMessage(
                    content="2026-06-08 00:00:00",
                    tool_call_id="call_1",
                    status="success",
                ),
                AIMessage(content="现在时间是 2026-06-08 00:00:00"),
            ],
            "metadata": {"model": "mock"},
        }


@pytest.mark.asyncio
async def test_graph_runner_returns_mock_response() -> None:
    runner = GraphRunner(build_chat_agent(llm=None), agent_id="chat_agent")
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
async def test_graph_runner_extracts_tool_calls_from_message_chain() -> None:
    runner = GraphRunner(_GraphWithMessageToolCalls())
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="hello")],
    )

    response = await runner.run_chat(request)

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].tool_name == "get_time"
    assert response.tool_calls[0].status == "success"
    assert response.tool_calls[0].input == {"query": "now"}
    assert response.tool_calls[0].output == {"value": "2026-06-08 00:00:00"}
    assert response.tool_calls[0].metadata["tool_call_id"] == "call_1"


@pytest.mark.asyncio
async def test_graph_runner_raises_when_llm_is_marked_unavailable() -> None:
    runner = GraphRunner(
        build_chat_agent(llm=None),
        agent_id="chat_agent",
        llm_available=False,
    )
    request = ChatRequest(messages=[ChatMessage(role="user", content="hello")])

    with pytest.raises(LLMException):
        await runner.run_chat(request)


@pytest.mark.asyncio
async def test_graph_runner_passes_thread_id_to_langgraph_config() -> None:
    graph = _GraphCapturingConfig()
    runner = GraphRunner(graph, agent_id="chat_agent")
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="hello")],
    )

    await runner.run_chat(request, thread_id="conversation-1")

    assert graph.received_kwargs["config"] == {
        "configurable": {
            "thread_id": "conversation-1",
        }
    }
    assert graph.received_kwargs["durability"] == "sync"
    assert isinstance(graph.received_state["messages"][0], HumanMessage)


@pytest.mark.asyncio
async def test_graph_runner_resume_uses_none_as_input_state() -> None:
    graph = _GraphCapturingConfig()
    runner = GraphRunner(graph, agent_id="chat_agent")
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="hello")],
    )

    await runner.run_chat(request, thread_id="conversation-1", resume=True)

    assert graph.received_state is None
