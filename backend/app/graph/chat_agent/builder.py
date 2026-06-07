"""通用聊天 Agent 的 graph 构建模块。"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.graph.chat_agent.nodes import create_chat_agent_node
from app.graph.chat_agent.state import ChatAgentState


def build_chat_agent(
    *,
    llm: Any | None = None,
    checkpointer: Any | None = None,
    store: Any | None = None,
):
    """构建默认通用聊天 Agent 的独立 graph。

    Args:
        llm: 启动阶段注入的 LLM 实例；为空时节点会自动降级到 mock 回复。
        checkpointer: 预留的 LangGraph 检查点对象。
        store: 预留的共享存储对象；当前骨架阶段仅保留参数，不默认启用。

    Returns:
        编译完成的 LangGraph 实例。
    """

    workflow = StateGraph(ChatAgentState)
    workflow.add_node("chat_agent", create_chat_agent_node(llm))
    workflow.set_entry_point("chat_agent")
    workflow.add_edge("chat_agent", END)

    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    _ = store
    return workflow.compile(**compile_kwargs)

