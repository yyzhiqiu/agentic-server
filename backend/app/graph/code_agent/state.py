"""代码助手 Agent 的图状态定义。"""

from __future__ import annotations

from typing import Any

from app.graph.shared.state import BaseAgentState


class CodeAgentState(BaseAgentState, total=False):
    """代码助手 Agent 在单次图执行中的共享状态。"""

    messages: list[dict[str, Any]]
    repository_context: dict[str, Any]
    changed_files: list[str]
    task_type: str | None
    plan: list[str]
    context_summary: str
    code_draft: str
    review_notes: list[str]
    test_suggestions: list[str]
    final_answer: str
