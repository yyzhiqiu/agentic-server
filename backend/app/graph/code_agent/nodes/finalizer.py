"""代码助手 Agent 的最终汇总节点。"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from app.graph.code_agent.state import CodeAgentState
from app.observability.decorators import observe_node


def _build_sections(title: str, items: list[str]) -> str:
    """把条目列表渲染为紧凑的中文段落。"""

    if not items:
        return f"{title}：暂无。"
    return title + "：\n" + "\n".join(f"- {item}" for item in items)


def create_finalizer_node():
    """创建最终汇总节点。

    该节点负责把前序节点产出的结构化中间结果整理成最终 assistant 消息，确保图的
    外部输出始终只有一条稳定的最终答复。
    """

    @observe_node("code_agent.finalizer")
    async def finalizer_node(state: CodeAgentState) -> CodeAgentState:
        plan = list(state.get("plan", []))
        context_summary = state.get("context_summary") or "未提供上下文。"
        code_draft = state.get("code_draft") or "暂无代码建议。"
        review_notes = list(state.get("review_notes", []))
        test_suggestions = list(state.get("test_suggestions", []))
        task_type = state.get("task_type") or "code_assist"
        changed_files = list(state.get("changed_files", []))

        final_answer = "\n\n".join(
            [
                _build_sections("执行计划", plan),
                f"上下文摘要：{context_summary}",
                f"实现建议：\n{code_draft}",
                _build_sections("审查要点", review_notes),
                _build_sections("测试建议", test_suggestions),
            ]
        )
        return {
            "messages": [
                AIMessage(
                    content=final_answer,
                    additional_kwargs={
                        "task_type": task_type,
                        "changed_files": changed_files,
                    },
                )
            ],
            "final_answer": final_answer,
        }

    return finalizer_node
