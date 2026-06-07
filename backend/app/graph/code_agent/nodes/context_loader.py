"""代码助手 Agent 的上下文加载节点。"""

from __future__ import annotations

from typing import Any

from app.graph.code_agent.state import CodeAgentState
from app.observability.decorators import observe_node


def _summarize_repository_context(repository_context: dict[str, Any]) -> str:
    """把仓库上下文压缩成简短摘要。"""

    if not repository_context:
        return "未提供额外仓库上下文。"

    parts: list[str] = []
    for key, value in repository_context.items():
        if isinstance(value, (str, int, float, bool)):
            parts.append(f"{key}={value}")
        elif isinstance(value, list):
            parts.append(f"{key}=list[{len(value)}]")
        elif isinstance(value, dict):
            parts.append(f"{key}=dict[{len(value)}]")
        else:
            parts.append(f"{key}={type(value).__name__}")
    return "；".join(parts)


def create_context_loader_node():
    """创建上下文加载节点。

    当前节点不做真实文件读取，只把调用方明确传入的上下文整理为稳定摘要，避免在
    未授权情况下擅自访问本地代码或外部系统。
    """

    @observe_node("code_agent.context_loader")
    async def context_loader_node(state: CodeAgentState) -> CodeAgentState:
        repository_context = dict(state.get("repository_context", {}))
        changed_files = list(state.get("changed_files", []))
        context_summary = _summarize_repository_context(repository_context)
        if changed_files:
            context_summary = (
                f"{context_summary}；候选变更文件 {len(changed_files)} 个："
                + "、".join(changed_files[:5])
            )
        return {
            "repository_context": repository_context,
            "changed_files": changed_files,
            "context_summary": context_summary,
        }

    return context_loader_node
