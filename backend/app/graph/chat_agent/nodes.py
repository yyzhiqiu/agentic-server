"""通用聊天 Agent 的节点实现。

本模块负责显式构建聊天模型节点：它会把当前 ``messages`` 状态与
系统提示词组装成一次模型调用输入，并返回单条 assistant 消息。
当前版本不启用工具调用循环，后续如需恢复工具能力，应在 graph 层
显式增加 ``ToolNode`` 与配套路由。
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage

from app.graph.chat_agent.prompts import CHAT_AGENT_SYSTEM_PROMPT
from app.graph.chat_agent.state import ChatAgentState
from app.graph.shared.messages import (
    message_like_to_langchain_message,
    read_message_content,
    read_message_role,
)
from app.observability.decorators import observe_node


def _last_user_content(messages: list[Any]) -> str:
    """提取最近一条用户消息内容。"""

    for message in reversed(messages):
        if read_message_role(message) == "user":
            return read_message_content(message)
    return ""


def _build_llm_messages(messages: list[Any]) -> list[BaseMessage]:
    """把状态中的消息组装为一次模型调用输入。"""

    converted = [SystemMessage(content=CHAT_AGENT_SYSTEM_PROMPT)]
    converted.extend(message_like_to_langchain_message(message) for message in messages)
    return converted


def _normalize_model_response(response: BaseMessage) -> AIMessage:
    """把模型返回值规整为 ``AIMessage``。"""

    if isinstance(response, AIMessage):
        return AIMessage(content=read_message_content(response))

    return AIMessage(content=read_message_content(response))


def create_chat_agent_node(llm: Any | None = None):
    """创建通用聊天 Agent 的模型节点。

    Reads:
        messages: 当前多轮消息上下文。

    Writes:
        messages: 追加一条 assistant 消息。

    Side Effects:
        当 ``llm`` 可用时，可能调用外部模型服务。
    """

    @observe_node("chat_agent")
    async def chat_agent_node(state: ChatAgentState) -> ChatAgentState:
        messages = list(state.get("messages", []))
        if llm is None:
            content = (
                "Mock response from chat_agent: "
                f"LLM 未配置，已收到你的消息：{_last_user_content(messages)}"
            )
            return {"messages": [AIMessage(content=content)]}

        response = await llm.ainvoke(_build_llm_messages(messages))
        return {"messages": [_normalize_model_response(response)]}

    return chat_agent_node
