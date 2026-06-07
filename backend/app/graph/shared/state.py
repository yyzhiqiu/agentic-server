"""多个 Agent 可复用的基础状态定义。"""

from __future__ import annotations

from typing import Any

from langgraph.graph import MessagesState


class BaseAgentState(MessagesState, total=False):
    """所有对外 Agent 共享的基础状态字段。"""

    user_id: str | None
    conversation_id: str | None
    metadata: dict[str, Any]
