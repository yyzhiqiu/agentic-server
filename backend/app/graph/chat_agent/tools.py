"""通用聊天 Agent 的可用工具定义。"""

from __future__ import annotations

from langchain_core.tools import BaseTool

from app.graph.shared.tools import calculator_tool, get_time, search_tool


def get_chat_agent_tools() -> list[BaseTool]:
    """返回当前通用聊天 Agent 可用的共享工具列表。"""

    return [search_tool, calculator_tool, get_time]
