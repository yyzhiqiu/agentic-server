from __future__ import annotations

from typing import Any

from app.graph.prompts.system import SYSTEM_PROMPT
from app.graph.state import AgentState
from app.observability.decorators import observe_node


def _last_user_content(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def _normalize_llm_content(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(item) for item in content)
    return str(content)


async def _call_llm(llm: Any, messages: list[dict[str, Any]]) -> str:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    converted = [SystemMessage(content=SYSTEM_PROMPT)]
    for message in messages:
        role = message.get("role", "user")
        content = str(message.get("content", ""))
        if role == "assistant":
            converted.append(AIMessage(content=content))
        else:
            converted.append(HumanMessage(content=content))
    response = await llm.ainvoke(converted)
    return _normalize_llm_content(response)


def create_agent_node(llm: Any | None = None):
    @observe_node("agent")
    async def agent_node(state: AgentState) -> AgentState:
        messages = list(state.get("messages", []))
        if llm is None:
            content = (
                "Mock response: LLM_API_KEY is not configured. "
                f"Received: {_last_user_content(messages)}"
            )
        else:
            content = await _call_llm(llm, messages)
        messages.append({"role": "assistant", "content": content})
        return {"messages": messages}

    return agent_node
