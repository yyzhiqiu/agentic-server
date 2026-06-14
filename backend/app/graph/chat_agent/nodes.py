"""通用聊天 Agent 的节点实现。

本模块负责在外层 LangGraph 单节点结构中封装一个支持工具调用的内部 Agent。
节点会把当前 ``messages`` 状态传给内部 Agent，让其按需执行工具调用循环，
再仅把本轮新增的消息增量写回外层状态，避免丢失 ``ToolMessage`` 链路，也
避免在请求期间重复构建 Agent。
"""

from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage

from app.graph.chat_agent.prompts import CHAT_AGENT_SYSTEM_PROMPT
from app.graph.chat_agent.state import ChatAgentState
from app.graph.chat_agent.tools import get_chat_agent_tools
from app.graph.shared.messages import (
    message_like_to_langchain_message,
    read_message_content,
    read_message_role,
)
from app.graph.shared.tools import get_time
from app.observability.decorators import observe_node


def _last_user_content(messages: list[Any]) -> str:
    """提取最近一条用户消息内容。"""

    for message in reversed(messages):
        if read_message_role(message) == "user":
            return read_message_content(message)
    return ""


def _build_agent_input_messages(messages: list[Any]) -> list[BaseMessage]:
    """把状态中的消息规整为内部 Agent 可消费的 LangChain 消息。"""

    return [message_like_to_langchain_message(message) for message in messages]


def _extract_appended_messages(
        original_messages: list[Any],
        result_messages: Any,
) -> list[BaseMessage]:
    """提取内部 Agent 相对输入新增的消息增量。

    内部 ``create_agent`` 返回的是完整消息链路，外层 ``MessagesState`` 只应
    追加本轮新增消息，才能保留工具调用轨迹并维持外层状态合并语义稳定。
    """

    if not isinstance(result_messages, list):
        return []

    return [
        message_like_to_langchain_message(message)
        for message in result_messages[len(original_messages):]
    ]


def _supports_tool_binding(llm: Any) -> bool:
    """判断模型是否支持 LangChain Agent 所需的工具绑定能力。

    Why:
        测试替身和部分轻量模型继承了 ``bind_tools`` 方法但默认抛出
        ``NotImplementedError``。这种情况下仍应允许通用聊天直接调用模型，
        不能因为工具绑定不可用而让整个 chat_agent 失败。
    """

    bind_tools = getattr(llm, "bind_tools", None)
    if bind_tools is None:
        return False

    try:
        bind_tools(get_chat_agent_tools())
    except NotImplementedError:
        return False
    return True


async def _invoke_plain_llm(llm: Any, messages: list[Any]) -> list[BaseMessage]:
    """在工具绑定不可用时直接调用模型并返回新增回复。"""

    response = await llm.ainvoke(
        [
            SystemMessage(content=CHAT_AGENT_SYSTEM_PROMPT),
            *_build_agent_input_messages(messages),
        ]
    )
    return [message_like_to_langchain_message(response)]


def create_chat_agent_node(llm: Any | None = None):
    """创建通用聊天 Agent 的模型节点。

    Reads:
        messages: 当前多轮消息上下文。

    Writes:
        messages: 追加本轮新增的 assistant 与 tool 消息。

    Side Effects:
        当 ``llm`` 可用时，会调用外部模型服务，并可能触发工具调用。
    """

    tool_enabled_agent = None
    if llm is not None and _supports_tool_binding(llm):
        tool_enabled_agent = create_agent(
            model=llm,
            tools=get_chat_agent_tools(),
            system_prompt=CHAT_AGENT_SYSTEM_PROMPT,
            name="chat_agent_inner",
        )

    @observe_node("chat_agent")
    async def chat_agent_node(state: ChatAgentState) -> ChatAgentState:
        messages = list(state.get("messages", []))
        if llm is None:
            content = (
                "Mock response from chat_agent: "
                f"LLM 未配置，已收到你的消息：{_last_user_content(messages)}"
            )
            return {"messages": [AIMessage(content=content)]}

        if tool_enabled_agent is None:
            return {"messages": await _invoke_plain_llm(llm, messages)}

        response = await tool_enabled_agent.ainvoke(
            {"messages": _build_agent_input_messages(messages)}
        )
        return {
            "messages": _extract_appended_messages(
                messages,
                response.get("messages", []),
            )
        }

    return chat_agent_node
