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

    当前版本使用显式单节点结构：
    ``START -> chat_agent -> END``。
    工具调用能力暂时关闭，后续如需恢复，应在这里重新显式增加工具节点与路由。
    """

    workflow = StateGraph(ChatAgentState)
    workflow.add_node("chat_agent", create_chat_agent_node(llm))
    workflow.set_entry_point("chat_agent")
    workflow.add_edge("chat_agent", END)

    compile_kwargs: dict[str, Any] = {
        "store": store,
        "name": "chat_agent",
    }
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    return workflow.compile(**compile_kwargs)
