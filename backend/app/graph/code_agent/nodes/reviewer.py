"""代码助手 Agent 的代码审查节点。"""

from __future__ import annotations

from app.graph.code_agent.prompts import CODE_AGENT_REVIEW_PROMPT
from app.graph.code_agent.state import CodeAgentState
from app.observability.decorators import observe_node


def create_reviewer_node():
    """创建代码审查节点。

    当前节点使用轻量规则补充风险提示，后续可以替换为更细粒度的静态分析、Diff 审查
    或模型化审查逻辑。
    """

    @observe_node("code_agent.reviewer")
    async def reviewer_node(state: CodeAgentState) -> CodeAgentState:
        task_type = state.get("task_type") or "code_assist"
        changed_files = list(state.get("changed_files", []))
        review_notes = [
            CODE_AGENT_REVIEW_PROMPT,
            f"本次任务类型为 {task_type}，需要关注与该任务匹配的边界条件。",
        ]
        if changed_files:
            review_notes.append(
                f"优先检查这些文件的回归风险：{'、'.join(changed_files[:5])}。"
            )
        else:
            review_notes.append("未提供变更文件列表，需提醒调用方补充影响范围。")
        return {"review_notes": review_notes}

    return reviewer_node
