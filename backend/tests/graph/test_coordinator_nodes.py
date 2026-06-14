"""协调入口 Agent 节点测试。"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.graph.coordinator_agent.nodes import create_route_decision_node

pytestmark = pytest.mark.asyncio


class _FakeRouteDecisionLLM:
    """为 coordinator 路由测试提供可控的异步 LLM 替身。"""

    def __init__(self, content: str | None = None, *, error: Exception | None = None) -> None:
        self.content = content or '{"intent":"general_chat","confidence":0.5,"reason":"默认"}'
        self.error = error
        self.calls: list[list[object]] = []

    async def ainvoke(self, messages: list[object]) -> AIMessage:
        self.calls.append(messages)
        if self.error is not None:
            raise self.error
        return AIMessage(content=self.content)


async def test_coordinator_uses_llm_context_to_route_to_route_planner() -> None:
    llm = _FakeRouteDecisionLLM(
        '{"intent":"route_planning","confidence":0.92,"reason":"用户在已有目的地上下文中要求规划路线"}'
    )
    node = create_route_decision_node(llm)

    result = await node(
        {
            "messages": [
                HumanMessage(content="我想去西安"),
                AIMessage(content="你想了解西安的什么信息？"),
                HumanMessage(content="帮我规划一下路线"),
            ],
            "metadata": {},
        }
    )

    assert result["route_intent"] == "route_planning"
    assert result["target_agent_id"] == "route_planner_agent"
    assert result["destination_text"] == "西安"
    assert result["metadata"]["route_decision"]["source"] == "llm"
    assert result["metadata"]["route_decision"]["confidence"] == 0.92
    assert "用户: 我想去西安" in llm.calls[0][1].content


async def test_coordinator_llm_can_avoid_keyword_false_positive() -> None:
    llm = _FakeRouteDecisionLLM(
        '{"intent":"general_chat","confidence":0.88,"reason":"这是产品方案咨询，不是出行路线"}'
    )
    node = create_route_decision_node(llm)

    result = await node(
        {
            "messages": [
                HumanMessage(content="从产品角度看这个方案怎么样？"),
            ],
            "metadata": {},
        }
    )

    assert result["route_intent"] == "general_chat"
    assert result["target_agent_id"] == "chat_agent"
    assert result["metadata"]["route_decision"]["source"] == "llm"


async def test_coordinator_falls_back_to_rules_when_llm_fails() -> None:
    node = create_route_decision_node(
        _FakeRouteDecisionLLM(error=RuntimeError("模型暂时不可用"))
    )

    result = await node(
        {
            "messages": [
                HumanMessage(content="我要去广东"),
            ],
            "metadata": {},
        }
    )

    assert result["route_intent"] == "route_planning"
    assert result["target_agent_id"] == "route_planner_agent"
    assert result["destination_text"] == "广东"
    assert result["metadata"]["route_decision"]["source"] == "rule_fallback"


async def test_coordinator_reuses_resume_fields_for_next_route_request() -> None:
    llm = _FakeRouteDecisionLLM(
        '{"intent":"route_planning","confidence":0.9,"reason":"用户继续提出路线规划目的地"}'
    )
    node = create_route_decision_node(llm)

    result = await node(
        {
            "messages": [
                HumanMessage(content="我要去北京"),
                AIMessage(content="当前还缺少 起点、出行方式，请补充后继续路线规划。"),
                HumanMessage(content="补充路线规划信息：起点：南京；出行方式：driving"),
                AIMessage(content="已为你生成从“南京”到“北京”的驾车路线。"),
                HumanMessage(content="我要去北京"),
            ],
            "metadata": {},
        }
    )

    assert result["route_intent"] == "route_planning"
    assert result["origin_text"] == "南京"
    assert result["destination_text"] == "北京"
    assert result["travel_mode"] == "driving"


async def test_coordinator_checkpoint_slots_survive_older_route_messages() -> None:
    llm = _FakeRouteDecisionLLM(
        '{"intent":"route_planning","confidence":0.9,"reason":"用户提出新的路线目的地"}'
    )
    node = create_route_decision_node(llm)

    result = await node(
        {
            "origin_text": "南京",
            "destination_text": "北京",
            "travel_mode": "driving",
            "messages": [
                HumanMessage(content="从上海到北京怎么走"),
                AIMessage(content="已为你生成从“上海”到“北京”的驾车路线。"),
                HumanMessage(content="我要去西安"),
            ],
            "metadata": {},
        }
    )

    assert result["origin_text"] == "南京"
    assert result["destination_text"] == "西安"
    assert result["travel_mode"] == "driving"


async def test_coordinator_parses_plain_structured_route_fields() -> None:
    llm = _FakeRouteDecisionLLM(
        '{"intent":"route_planning","confidence":0.9,"reason":"用户补充了路线规划字段"}'
    )
    node = create_route_decision_node(llm)

    result = await node(
        {
            "messages": [
                HumanMessage(content="起点：南京；出行方式：driving"),
                HumanMessage(content="我要去北京"),
            ],
            "metadata": {},
        }
    )

    assert result["origin_text"] == "南京"
    assert result["destination_text"] == "北京"
    assert result["travel_mode"] == "driving"
