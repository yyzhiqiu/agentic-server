"""代码助手 Agent 的编码建议节点。"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.code_agent.prompts import CODE_AGENT_SYSTEM_PROMPT
from app.graph.code_agent.state import CodeAgentState
from app.graph.shared.messages import read_message_content, read_message_role
from app.observability.decorators import observe_node


def _last_user_content(messages: list[Any]) -> str:
    """提取最近一条用户消息内容。"""

    for message in reversed(messages):
        if read_message_role(message) == "user":
            return read_message_content(message)
    return ""


async def _call_llm(
    llm: Any,
    *,
    latest_request: str,
    task_type: str,
    context_summary: str,
) -> str:
    """调用 LLM 生成代码建议草稿。"""

    response = await llm.ainvoke(
        [
            SystemMessage(content=CODE_AGENT_SYSTEM_PROMPT),
            HumanMessage(
                content="\n".join(
                    [
                        f"任务类型：{task_type}",
                        f"上下文摘要：{context_summary}",
                        f"用户请求：{latest_request}",
                    ]
                )
            ),
        ]
    )
    return read_message_content(response)


def create_coder_node(llm: Any | None = None):
    """创建编码建议节点。

    该节点负责产出“实现建议草稿”，而不是直接返回最终答复，这样后续审查和测试
    节点可以围绕同一份草稿继续加工。
    """

    @observe_node("code_agent.coder")
    async def coder_node(state: CodeAgentState) -> CodeAgentState:
        messages = list(state.get("messages", []))
        latest_request = _last_user_content(messages)
        task_type = state.get("task_type") or "code_assist"
        context_summary = state.get("context_summary") or "未提供上下文。"
        changed_files = list(state.get("changed_files", []))

        if llm is None:
            changed_hint = ""
            if changed_files:
                changed_hint = f"；涉及文件：{'、'.join(changed_files[:5])}"
            code_draft = (
                f"Mock response from code_agent：针对任务“{task_type}”，"
                f"建议先分析请求“{latest_request}”，再结合上下文“{context_summary}”给出实现方案"
                f"{changed_hint}。"
            )
        else:
            code_draft = await _call_llm(
                llm,
                latest_request=latest_request,
                task_type=task_type,
                context_summary=context_summary,
            )

        return {"code_draft": code_draft}

    return coder_node
