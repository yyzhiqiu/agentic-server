"""代码助手 Agent 的静态元信息。"""

from __future__ import annotations

from app.graph.types import AgentMetadata


CODE_AGENT_METADATA = AgentMetadata(
    agent_id="code_agent",
    name="代码助手",
    description="适合代码解释、代码生成、重构建议和代码审查。",
    version="0.1.0",
    capabilities=["code_explain", "code_review", "code_generation"],
)

