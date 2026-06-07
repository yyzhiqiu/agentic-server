"""默认通用聊天 Agent。"""

from app.graph.chat_agent.builder import build_chat_agent
from app.graph.chat_agent.metadata import CHAT_AGENT_METADATA

__all__ = ["CHAT_AGENT_METADATA", "build_chat_agent"]

