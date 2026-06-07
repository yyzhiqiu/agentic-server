"""多个 Agent 共享的文件工具占位实现。"""

from __future__ import annotations


async def file_tool(path: str) -> dict:
    """返回默认禁用状态，避免 Agent 未授权读写本地文件。"""

    return {"path": path, "content": None, "status": "not_configured"}

