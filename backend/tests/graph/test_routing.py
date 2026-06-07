"""通用聊天 Agent 路由的基础行为测试。"""

from __future__ import annotations

from app.graph.chat_agent.routing import should_continue


def test_routing_defaults_to_end() -> None:
    assert should_continue({"messages": []}) == "end"
