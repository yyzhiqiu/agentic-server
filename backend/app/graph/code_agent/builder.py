"""代码助手 Agent 的图构建模块。"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.graph.code_agent.nodes import (
    create_coder_node,
    create_context_loader_node,
    create_finalizer_node,
    create_planner_node,
    create_reviewer_node,
    create_test_planner_node,
)
from app.graph.code_agent.routing import (
    route_after_coder,
    route_after_context_loader,
    route_after_planner,
    route_after_reviewer,
    route_after_test_planner,
)
from app.graph.code_agent.state import CodeAgentState


def build_code_agent(
    *,
    llm: Any | None = None,
    checkpointer: Any | None = None,
    store: Any | None = None,
):
    """构建代码助手 Agent 的复杂图结构。

    当前结构显式拆分为规划、上下文加载、编码建议、审查、测试规划和最终汇总
    六个节点，便于后续逐步替换为更真实的代码分析与执行能力。
    """

    workflow = StateGraph(CodeAgentState)
    workflow.add_node("planner", create_planner_node())
    workflow.add_node("context_loader", create_context_loader_node())
    workflow.add_node("coder", create_coder_node(llm))
    workflow.add_node("reviewer", create_reviewer_node())
    workflow.add_node("test_planner", create_test_planner_node())
    workflow.add_node("finalizer", create_finalizer_node())

    workflow.set_entry_point("planner")
    workflow.add_conditional_edges(
        "planner",
        route_after_planner,
        {"context_loader": "context_loader"},
    )
    workflow.add_conditional_edges(
        "context_loader",
        route_after_context_loader,
        {"coder": "coder"},
    )
    workflow.add_conditional_edges(
        "coder",
        route_after_coder,
        {"reviewer": "reviewer"},
    )
    workflow.add_conditional_edges(
        "reviewer",
        route_after_reviewer,
        {"test_planner": "test_planner"},
    )
    workflow.add_conditional_edges(
        "test_planner",
        route_after_test_planner,
        {"finalizer": "finalizer"},
    )
    workflow.add_edge("finalizer", END)

    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    _ = store
    return workflow.compile(**compile_kwargs)
