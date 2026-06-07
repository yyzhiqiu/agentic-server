"""代码助手 Agent 的测试规划节点。"""

from __future__ import annotations

from app.graph.code_agent.prompts import CODE_AGENT_TEST_PROMPT
from app.graph.code_agent.state import CodeAgentState
from app.observability.decorators import observe_node


def create_test_planner_node():
    """创建测试规划节点。"""

    @observe_node("code_agent.test_planner")
    async def test_planner_node(state: CodeAgentState) -> CodeAgentState:
        task_type = state.get("task_type") or "code_assist"
        changed_files = list(state.get("changed_files", []))
        suggestions = [CODE_AGENT_TEST_PROMPT]
        if task_type == "code_review":
            suggestions.append("补充针对回归点的最小复现用例。")
        else:
            suggestions.append("为核心路径补充单元测试，并验证失败分支。")
        if changed_files:
            suggestions.append(
                f"优先覆盖文件相关行为：{'、'.join(changed_files[:5])}。"
            )
        return {"test_suggestions": suggestions}

    return test_planner_node
