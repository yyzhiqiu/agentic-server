"""通用聊天 Agent 的条件路由定义。"""

from __future__ import annotations

from typing import Literal

from app.graph.chat_agent.state import ChatAgentState


def should_continue(state: ChatAgentState) -> Literal["end"]:
    """返回通用聊天 Agent 的下一跳。

    Returns:
        "end": 当前脚手架仅包含单个聊天节点，本轮图执行直接结束。
    """

    return "end"

