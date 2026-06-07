from __future__ import annotations

from typing import Any, Protocol


class QueueClient(Protocol):
    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        ...


class InMemoryQueue:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict[str, Any]]] = []

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        self.messages.append((topic, payload))
