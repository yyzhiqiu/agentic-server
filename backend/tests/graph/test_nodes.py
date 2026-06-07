from __future__ import annotations

import pytest

from app.graph.chat_agent.nodes import create_chat_agent_node
from app.graph.code_agent.nodes import (
    create_coder_node,
    create_context_loader_node,
    create_finalizer_node,
    create_planner_node,
    create_reviewer_node,
    create_test_planner_node,
)


@pytest.mark.asyncio
async def test_chat_agent_node_returns_mock_message_without_llm() -> None:
    node = create_chat_agent_node(None)
    state = {"messages": [{"role": "user", "content": "hello"}], "metadata": {}}

    result = await node(state)

    assert result["messages"][-1]["role"] == "assistant"
    assert "chat_agent" in result["messages"][-1]["content"]


@pytest.mark.asyncio
async def test_code_agent_nodes_can_build_final_mock_response() -> None:
    planner = create_planner_node()
    context_loader = create_context_loader_node()
    coder = create_coder_node(None)
    reviewer = create_reviewer_node()
    test_planner = create_test_planner_node()
    finalizer = create_finalizer_node()

    state = {
        "messages": [{"role": "user", "content": "review this function"}],
        "metadata": {"agent_id": "code_agent"},
        "task_type": "code_review",
        "repository_context": {"entrypoint": "backend/app/main.py"},
        "changed_files": ["backend/app/services/chat_service.py"],
    }

    state = {**state, **(await planner(state))}
    state = {**state, **(await context_loader(state))}
    state = {**state, **(await coder(state))}
    state = {**state, **(await reviewer(state))}
    state = {**state, **(await test_planner(state))}
    result = await finalizer(state)

    assert result["messages"][-1]["role"] == "assistant"
    assert "code_agent" in result["messages"][-1]["content"]
    assert "测试建议" in result["messages"][-1]["content"]
