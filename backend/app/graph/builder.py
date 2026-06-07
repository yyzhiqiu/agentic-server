"""默认 Agent graph 的兼容构建入口。

本模块保留旧的 ``build_graph`` 导入路径，内部转发到 ``chat_agent``。
这样可以在平滑升级到 Agent Registry 的同时，不破坏现有测试和兼容代码。
"""

from __future__ import annotations

from typing import Any

from app.graph.chat_agent.builder import build_chat_agent


def build_graph(
    llm: Any | None = None,
    *,
    checkpointer: Any | None = None,
    store: Any | None = None,
):
    """构建默认 ``chat_agent`` 的 graph 兼容实例。"""

    return build_chat_agent(
        llm=llm,
        checkpointer=checkpointer,
        store=store,
    )
