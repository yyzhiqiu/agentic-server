"""协调入口 Agent 的图构建模块。"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.graph.coordinator_agent.nodes import (
    create_general_chat_node,
    create_passthrough_human_interaction_node,
    create_route_decision_node,
    create_route_execute_node,
    create_route_finalize_node,
    create_route_prepare_branch_node,
    create_route_prepare_human_interaction_node,
    create_route_resume_merge_node,
)
from app.graph.coordinator_agent.routing import (
    route_after_decision,
    route_after_route_execute,
    route_after_route_prepare,
    route_after_route_resume_merge,
)
from app.graph.coordinator_agent.state import CoordinatorAgentState
from app.integrations.amap_mcp import AmapRouteToolset


def build_coordinator_agent(
    *,
    llm: Any | None = None,
    amap_route_toolset: AmapRouteToolset | None = None,
    checkpointer: Any | None = None,
    store: Any | None = None,
):
    """构建默认对话入口使用的协调 Agent。"""

    workflow = StateGraph(CoordinatorAgentState)
    workflow.add_node("route_decision", create_route_decision_node(llm))
    workflow.add_node("general_chat", create_general_chat_node(llm))
    workflow.add_node("route_prepare_branch", create_route_prepare_branch_node())
    workflow.add_node(
        "route_prepare_human_interaction",
        create_route_prepare_human_interaction_node(),
    )
    workflow.add_node("human_interaction", create_passthrough_human_interaction_node())
    workflow.add_node("route_resume_merge", create_route_resume_merge_node())
    workflow.add_node("route_execute", create_route_execute_node(amap_route_toolset))
    workflow.add_node("route_finalize", create_route_finalize_node())

    workflow.set_entry_point("route_decision")
    workflow.add_conditional_edges(
        "route_decision",
        route_after_decision,
        {
            "general_chat": "general_chat",
            "route_prepare_branch": "route_prepare_branch",
        },
    )
    workflow.add_edge("general_chat", END)
    workflow.add_conditional_edges(
        "route_prepare_branch",
        route_after_route_prepare,
        {
            "route_prepare_human_interaction": "route_prepare_human_interaction",
            "route_execute": "route_execute",
        },
    )
    workflow.add_edge("route_prepare_human_interaction", "human_interaction")
    workflow.add_edge("human_interaction", "route_resume_merge")
    workflow.add_conditional_edges(
        "route_resume_merge",
        route_after_route_resume_merge,
        {
            "route_prepare_human_interaction": "route_prepare_human_interaction",
            "route_execute": "route_execute",
        },
    )
    workflow.add_conditional_edges(
        "route_execute",
        route_after_route_execute,
        {
            "route_prepare_human_interaction": "route_prepare_human_interaction",
            "route_finalize": "route_finalize",
        },
    )
    workflow.add_edge("route_finalize", END)

    compile_kwargs: dict[str, Any] = {
        "store": store,
        "name": "coordinator_agent",
    }
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    return workflow.compile(**compile_kwargs)
