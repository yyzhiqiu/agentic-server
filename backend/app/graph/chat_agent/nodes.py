"""通用聊天 Agent 的节点实现。

本模块负责把标准聊天消息转换为 LLM 输入，或在 LLM 不可用时生成 mock 回复。
它不处理 HTTP 请求，也不写数据库。
"""

from __future__ import annotations

from typing import Any

from app.graph.chat_agent.prompts import CHAT_AGENT_SYSTEM_PROMPT
from app.graph.chat_agent.state import ChatAgentState
from app.observability.decorators import observe_node


def _last_user_content(messages: list[dict[str, Any]]) -> str:
    """提取最近一条用户消息内容。"""

    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def _normalize_llm_content(response: Any) -> str:
    """将不同 LLM 响应结构收敛为纯文本。"""

    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(item) for item in content)
    return str(content)


async def _call_llm(llm: Any, messages: list[dict[str, Any]]) -> str:
    """调用 LLM 生成通用聊天回复。"""

    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    converted = [SystemMessage(content=CHAT_AGENT_SYSTEM_PROMPT)]
    for message in messages:
        role = message.get("role", "user")
        content = str(message.get("content", ""))
        if role == "assistant":
            converted.append(AIMessage(content=content))
        else:
            converted.append(HumanMessage(content=content))
    response = await llm.ainvoke(converted)
    return _normalize_llm_content(response)


def create_chat_agent_node(llm: Any | None = None):
    """创建通用聊天 Agent 的主节点。

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
        else:
            content = await _call_llm(llm, messages)
        messages.append({"role": "assistant", "content": content})
        return {"messages": messages}

    return chat_agent_node

