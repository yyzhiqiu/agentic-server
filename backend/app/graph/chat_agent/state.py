"""通用聊天 Agent 的图状态定义。"""

from __future__ import annotations

from typing import Any

from app.graph.shared.state import BaseAgentState


class ChatAgentState(BaseAgentState, total=False):
    """通用聊天 Agent 在单次图执行中的共享状态。"""

    messages: list[dict[str, Any]]

