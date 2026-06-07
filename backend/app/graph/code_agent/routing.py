"""代码助手 Agent 的节点路由定义。"""

from __future__ import annotations

from typing import Literal

from app.graph.code_agent.state import CodeAgentState


def route_after_planner(state: CodeAgentState) -> Literal["context_loader"]:
    """规划完成后进入上下文加载节点。"""

    _ = state
    return "context_loader"


def route_after_context_loader(state: CodeAgentState) -> Literal["coder"]:
    """上下文准备完成后进入编码建议节点。"""

    _ = state
    return "coder"


def route_after_coder(state: CodeAgentState) -> Literal["reviewer"]:
    """编码建议生成后进入审查节点。"""

    _ = state
    return "reviewer"


def route_after_reviewer(state: CodeAgentState) -> Literal["test_planner"]:
    """审查完成后进入测试规划节点。"""

    _ = state
    return "test_planner"


def route_after_test_planner(state: CodeAgentState) -> Literal["finalizer"]:
    """测试规划完成后进入最终汇总节点。"""

    _ = state
    return "finalizer"
