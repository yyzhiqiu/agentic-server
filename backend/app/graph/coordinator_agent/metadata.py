"""协调入口 Agent 的静态元信息。"""

from __future__ import annotations

from app.graph.types import AgentMetadata


COORDINATOR_AGENT_METADATA = AgentMetadata(
    agent_id="coordinator_agent",
    name="多智能体协调入口",
    description="统一接收用户请求，并在通用回复与路线规划之间自动路由。",
    version="0.1.0",
    capabilities=["route_decision", "chat", "routing"],
)
