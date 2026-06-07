"""Graph 共享存储工厂。

当前实现提供一个最小可运行的内存存储，用于未来扩展 Agent 级共享上下文。
它不是数据库或缓存替代品，也不会在请求层直接暴露给 HTTP 逻辑。
"""

from __future__ import annotations

from typing import Any


class MemoryStore:
    """最小可运行的异步内存存储。"""

    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    async def get(self, key: str) -> Any | None:
        """按键读取一个内存值。"""

        return self.values.get(key)

    async def set(self, key: str, value: Any) -> None:
        """按键写入一个内存值。"""

        self.values[key] = value


def create_store() -> MemoryStore:
    """创建供多个 Agent 共享的最小内存存储实例。"""

    return MemoryStore()
