from __future__ import annotations

import pytest

from app.graph.nodes.agent import create_agent_node
from app.graph.nodes.human_review import human_review_node
from app.graph.nodes.memory import memory_node
from app.graph.nodes.retriever import retriever_node
from app.graph.nodes.summarize import summarize_node
from app.graph.nodes.tool_executor import tool_executor_node


@pytest.mark.asyncio
async def test_agent_node_returns_mock_message_without_llm() -> None:
    node = create_agent_node(None)
    state = {"messages": [{"role": "user", "content": "hello"}], "metadata": {}}

    result = await node(state)

    assert result["messages"][-1]["role"] == "assistant"
    assert "Mock response" in result["messages"][-1]["content"]


@pytest.mark.asyncio
async def test_placeholder_nodes_passthrough_state() -> None:
    state = {"messages": [{"role": "user", "content": "hello"}], "metadata": {}}

    assert await retriever_node(state) == state
    assert await summarize_node(state) == state
    assert await memory_node(state) == state
    assert await human_review_node(state) == state
    assert await tool_executor_node(state) == state
