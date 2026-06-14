"""协调入口 Agent 的图路由函数。"""

from __future__ import annotations

from typing import Literal

from app.graph.coordinator_agent.state import CoordinatorAgentState


def route_after_decision(state: CoordinatorAgentState) -> Literal["general_chat", "route_prepare_branch"]:
    """根据意图判断进入通用回复还是路线规划分支。"""

    if state.get("route_intent") == "route_planning":
        return "route_prepare_branch"
    return "general_chat"


def route_after_route_prepare(
    state: CoordinatorAgentState,
) -> Literal["route_prepare_human_interaction", "route_execute"]:
    """根据缺失字段决定是否先补参。"""

    missing_fields = state.get("missing_fields", [])
    if missing_fields:
        return "route_prepare_human_interaction"
    return "route_execute"


def route_after_route_resume_merge(
    state: CoordinatorAgentState,
) -> Literal["route_prepare_human_interaction", "route_execute"]:
    """恢复补参后再次判断是否需要追问。"""

    missing_fields = state.get("missing_fields", [])
    if missing_fields:
        return "route_prepare_human_interaction"
    return "route_execute"


def route_after_route_execute(
    state: CoordinatorAgentState,
) -> Literal["route_prepare_human_interaction", "route_finalize"]:
    """根据路线执行结果决定回到补参还是输出最终摘要。"""

    missing_fields = state.get("missing_fields", [])
    if missing_fields:
        return "route_prepare_human_interaction"
    return "route_finalize"
