"""共享的人机交互节点。"""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from app.observability.decorators import observe_node


def create_human_interaction_node():
    """创建共享的人机交互中断节点。"""

    @observe_node("shared.human_interaction")
    async def human_interaction_node(state: dict[str, Any]) -> dict[str, Any]:
        pending_human_input = state.get("pending_human_input")
        if pending_human_input is None:
            return {}
        resumed_human_input = interrupt(pending_human_input)
        return {
            "human_input": resumed_human_input,
            "pending_human_input": None,
        }

    return human_interaction_node
