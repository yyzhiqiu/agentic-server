from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from app.graph.default import DEFAULT_AGENT_ID
from app.graph.registry import build_agent_registry


def test_agent_registry_builds_chat_and_code_agents() -> None:
    registry = build_agent_registry(llm=None)

    assert DEFAULT_AGENT_ID in registry
    assert "code_agent" in registry
    assert registry[DEFAULT_AGENT_ID].metadata.agent_id == DEFAULT_AGENT_ID
    assert registry["code_agent"].metadata.capabilities == [
        "code_explain",
        "code_review",
        "code_generation",
    ]


@pytest.mark.asyncio
async def test_agent_registry_graphs_can_return_mock_messages() -> None:
    registry = build_agent_registry(llm=None)

    chat_result = await registry["chat_agent"].graph.ainvoke(
        {
            "messages": [HumanMessage(content="hello")],
            "metadata": {},
        }
    )
    code_result = await registry["code_agent"].graph.ainvoke(
        {
            "messages": [HumanMessage(content="review this function")],
            "metadata": {"task_type": "code_review"},
        }
    )

    assert "chat_agent" in chat_result["messages"][-1].content
    assert "code_agent" in code_result["messages"][-1].content
