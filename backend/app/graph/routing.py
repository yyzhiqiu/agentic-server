"""默认 Agent 路由的兼容导出模块。"""

from __future__ import annotations

from typing import Literal

from app.graph.chat_agent.routing import should_continue as should_chat_agent_continue
from app.graph.state import AgentState


def should_continue(state: AgentState) -> Literal["end"]:
    """兼容旧导入路径，复用 ``chat_agent`` 的默认路由。"""

    return should_chat_agent_continue(state)
