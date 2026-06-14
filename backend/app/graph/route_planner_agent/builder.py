"""路线规划 Agent 的图构建模块。"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.graph.route_planner_agent.nodes import (
    create_execute_route_plan_node,
    create_parse_route_request_node,
    create_prepare_human_interaction_node,
    create_resume_merge_node,
    create_summarize_route_result_node,
    create_validate_route_slots_node,
)
from app.graph.route_planner_agent.routing import (
    route_after_execute,
    route_after_resume_merge,
    route_after_validate,
)
from app.graph.route_planner_agent.state import RoutePlannerAgentState
from app.graph.shared.nodes.human_interaction import create_human_interaction_node
from app.integrations.amap_mcp import AmapRouteToolset


def build_route_planner_agent(
    *,
    amap_route_toolset: AmapRouteToolset | None = None,
    checkpointer: Any | None = None,
    store: Any | None = None,
):
    """构建路线规划 Agent 的确定性图结构。"""

    workflow = StateGraph(RoutePlannerAgentState)
    workflow.add_node("parse_route_request", create_parse_route_request_node())
    workflow.add_node("validate_route_slots", create_validate_route_slots_node())
    workflow.add_node("prepare_human_interaction", create_prepare_human_interaction_node())
    workflow.add_node("human_interaction", create_human_interaction_node())
    workflow.add_node("resume_merge", create_resume_merge_node())
    workflow.add_node("execute_route_plan", create_execute_route_plan_node(amap_route_toolset))
    workflow.add_node("summarize_route_result", create_summarize_route_result_node())

    workflow.set_entry_point("parse_route_request")
    workflow.add_edge("parse_route_request", "validate_route_slots")
    workflow.add_conditional_edges(
        "validate_route_slots",
        route_after_validate,
        {
            "prepare_human_interaction": "prepare_human_interaction",
            "execute_route_plan": "execute_route_plan",
        },
    )
    workflow.add_edge("prepare_human_interaction", "human_interaction")
    workflow.add_edge("human_interaction", "resume_merge")
    workflow.add_conditional_edges(
        "resume_merge",
        route_after_resume_merge,
        {
            "prepare_human_interaction": "prepare_human_interaction",
            "execute_route_plan": "execute_route_plan",
        },
    )
    workflow.add_conditional_edges(
        "execute_route_plan",
        route_after_execute,
        {
            "prepare_human_interaction": "prepare_human_interaction",
            "summarize_route_result": "summarize_route_result",
        },
    )
    workflow.add_edge("summarize_route_result", END)

    compile_kwargs: dict[str, Any] = {
        "store": store,
        "name": "route_planner_agent",
    }
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    return workflow.compile(**compile_kwargs)
