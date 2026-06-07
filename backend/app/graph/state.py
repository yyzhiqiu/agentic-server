from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    user_id: str | None
    conversation_id: str | None
    metadata: dict[str, Any]
