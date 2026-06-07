from __future__ import annotations

from app.graph.state import AgentState


def should_continue(state: AgentState) -> str:
    return "end"
