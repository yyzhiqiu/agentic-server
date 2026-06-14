"""协调入口 Agent 导出模块。"""

from app.graph.coordinator_agent.builder import build_coordinator_agent
from app.graph.coordinator_agent.metadata import COORDINATOR_AGENT_METADATA

__all__ = ["COORDINATOR_AGENT_METADATA", "build_coordinator_agent"]
