from __future__ import annotations

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.graph.chat_agent.nodes import create_chat_agent_node
from app.graph.code_agent.nodes import (
    create_coder_node,
    create_context_loader_node,
    create_finalizer_node,
    create_planner_node,
    create_reviewer_node,
    create_test_planner_node,
)


class _ToolCapableFakeMessagesListChatModel(FakeMessagesListChatModel):
    """为节点测试提供最小可用的工具绑定能力。"""

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        del tools, tool_choice, kwargs
        return self


@pytest.mark.asyncio
async def test_chat_agent_node_returns_mock_message_without_llm() -> None:
    node = create_chat_agent_node(None)
    state = {"messages": [HumanMessage(content="hello")], "metadata": {}}

    result = await node(state)

    assert result["messages"][-1].type == "ai"
    assert "chat_agent" in result["messages"][-1].content


@pytest.mark.asyncio
async def test_chat_agent_node_preserves_tool_call_message_chain() -> None:
    node = create_chat_agent_node(
        _ToolCapableFakeMessagesListChatModel(
            responses=[
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
                AIMessage(content="现在时间是 2026-06-09 12:00:00"),
            ]
        )
    )
    state = {"messages": [HumanMessage(content="现在几点")], "metadata": {}}

    result = await node(state)

    assert len(result["messages"]) == 3
    assert isinstance(result["messages"][0], AIMessage)
    assert result["messages"][0].tool_calls[0]["name"] == "get_time"
    assert isinstance(result["messages"][1], ToolMessage)
    assert result["messages"][1].tool_call_id == "call_1"
    assert isinstance(result["messages"][2], AIMessage)
    assert "现在时间是" in result["messages"][2].content


@pytest.mark.asyncio
async def test_code_agent_nodes_can_build_final_mock_response() -> None:
    planner = create_planner_node()
    context_loader = create_context_loader_node()
    coder = create_coder_node(None)
    reviewer = create_reviewer_node()
    test_planner = create_test_planner_node()
    finalizer = create_finalizer_node()

    state = {
        "messages": [HumanMessage(content="review this function")],
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

    assert result["messages"][-1].type == "ai"
    assert "code_agent" in result["messages"][-1].content
    assert "测试建议" in result["messages"][-1].content
