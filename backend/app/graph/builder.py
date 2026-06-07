from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.graph.nodes.agent import create_agent_node
from app.graph.state import AgentState


def build_graph(llm: Any | None = None):
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", create_agent_node(llm))
    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)
    return workflow.compile()
