from __future__ import annotations

from typing import Any


class MemoryStore:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    async def get(self, key: str) -> Any | None:
        return self.values.get(key)

    async def set(self, key: str, value: Any) -> None:
        self.values[key] = value
