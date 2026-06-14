"""路线规划 Agent 的图路由函数。"""

from __future__ import annotations

from typing import Literal

from app.graph.route_planner_agent.state import RoutePlannerAgentState


def route_after_validate(state: RoutePlannerAgentState) -> Literal["prepare_human_interaction", "execute_route_plan"]:
    """根据缺失字段决定是进入补参还是直接执行规划。"""

    missing_fields = state.get("missing_fields", [])
    if missing_fields:
        return "prepare_human_interaction"
    return "execute_route_plan"


def route_after_resume_merge(state: RoutePlannerAgentState) -> Literal["prepare_human_interaction", "execute_route_plan"]:
    """恢复后再次判断是否仍需补参。"""

    missing_fields = state.get("missing_fields", [])
    if missing_fields:
        return "prepare_human_interaction"
    return "execute_route_plan"


def route_after_execute(
    state: RoutePlannerAgentState,
) -> Literal["prepare_human_interaction", "summarize_route_result"]:
    """根据执行结果决定进入补参还是汇总结果。"""

    missing_fields = state.get("missing_fields", [])
    if missing_fields:
        return "prepare_human_interaction"
    return "summarize_route_result"
