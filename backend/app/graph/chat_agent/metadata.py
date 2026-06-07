"""通用聊天 Agent 的静态元信息。"""

from __future__ import annotations

from app.graph.types import AgentMetadata


CHAT_AGENT_METADATA = AgentMetadata(
    agent_id="chat_agent",
    name="通用聊天助手",
    description="适合普通问答、对话和轻量任务处理。",
    version="0.1.0",
    capabilities=["chat", "qa"],
)

