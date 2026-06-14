"""路线规划 Agent 的静态元信息。"""

from __future__ import annotations

from app.graph.types import AgentMetadata


ROUTE_PLANNER_AGENT_METADATA = AgentMetadata(
    agent_id="route_planner_agent",
    name="路线规划助手",
    description="适合进行起终点补参、地点解析与驾车/步行/公交路线规划。",
    version="0.1.0",
    capabilities=["route_planning", "human_input"],
)
