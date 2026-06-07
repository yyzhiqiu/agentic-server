from __future__ import annotations

from typing import Any


class LLMFallback:
    def __init__(self, primary: Any | None, fallback: Any | None = None) -> None:
        self.primary = primary
        self.fallback = fallback

    def get(self) -> Any | None:
        return self.primary or self.fallback
