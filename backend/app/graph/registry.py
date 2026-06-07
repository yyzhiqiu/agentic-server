"""启动期 Agent 注册表构建模块。

本模块负责集中编译并注册当前服务对外提供的多个独立 Agent graph。
它不处理 HTTP 请求，也不在请求期间重复构建 graph。
"""

from __future__ import annotations

from typing import Any

from app.graph.chat_agent import CHAT_AGENT_METADATA, build_chat_agent
from app.graph.code_agent import CODE_AGENT_METADATA, build_code_agent
from app.graph.types import AgentDefinition, AgentRegistry


def build_agent_registry(
    *,
    llm: Any | None = None,
    checkpointer: Any | None = None,
    store: Any | None = None,
) -> AgentRegistry:
    """构建当前服务可用的 Agent 注册表。

    Args:
        llm: 启动阶段初始化好的 LLM 实例；为空时各 Agent 应自行降级到 mock。
        checkpointer: 预留给 LangGraph 的检查点实现。
        store: 预留给 LangGraph 的共享存储实现。

    Returns:
        以 ``agent_id`` 为键的 AgentDefinition 映射。
    """

    return {
        CHAT_AGENT_METADATA.agent_id: AgentDefinition(
            metadata=CHAT_AGENT_METADATA,
            graph=build_chat_agent(
                llm=llm,
                checkpointer=checkpointer,
                store=store,
            ),
        ),
        CODE_AGENT_METADATA.agent_id: AgentDefinition(
            metadata=CODE_AGENT_METADATA,
            graph=build_code_agent(
                llm=llm,
                checkpointer=checkpointer,
                store=store,
            ),
        ),
    }

