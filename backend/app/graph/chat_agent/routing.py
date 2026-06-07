"""通用聊天 Agent 的条件路由定义。"""

from __future__ import annotations

from typing import Literal

from app.graph.chat_agent.state import ChatAgentState


def should_continue(state: ChatAgentState) -> Literal["end"]:
    """返回通用聊天 Agent 的下一跳。

    当前版本暂不启用工具调用循环，因此模型节点执行后直接结束。
    """

    _ = state
    return "end"
