"""代码助手 Agent 的任务规划节点。"""

from __future__ import annotations

from typing import Any

from app.graph.code_agent.state import CodeAgentState
from app.graph.shared.messages import read_message_content, read_message_role
from app.observability.decorators import observe_node


def _last_user_content(messages: list[Any]) -> str:
    """提取最近一条用户消息内容。"""

    for message in reversed(messages):
        if read_message_role(message) == "user":
            return read_message_content(message)
    return ""


def create_planner_node():
    """创建任务规划节点。

    该节点只负责把用户请求归类成后续节点易消费的结构化计划，不直接生成最终答复，
    这样后续可以逐步替换成更复杂的规划策略而不影响其他节点职责。
    """

    @observe_node("code_agent.planner")
    async def planner_node(state: CodeAgentState) -> CodeAgentState:
        messages = list(state.get("messages", []))
        task_type = state.get("task_type") or "code_assist"
        latest_request = _last_user_content(messages)
        plan = [
            f"识别任务类型：{task_type}",
            "整理可用代码上下文和变更文件",
            "给出实现或修改建议",
            "补充风险审查与测试建议",
        ]
        if latest_request:
            plan.insert(1, f"聚焦用户请求：{latest_request[:80]}")
        return {
            "task_type": task_type,
            "plan": plan,
        }

    return planner_node
