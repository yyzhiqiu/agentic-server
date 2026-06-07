"""Graph 检查点工厂。

当前阶段先保留空实现，用于保证多 Agent Registry 的启动链路稳定。
后续如需接入 Redis、数据库或 LangGraph 官方持久化能力，可从这里统一扩展。
"""

from __future__ import annotations

from typing import Any


def create_checkpointer() -> Any | None:
    """创建 LangGraph 检查点实现。

    Returns:
        当前阶段返回 ``None``，表示不启用持久化检查点。
    """

    return None
