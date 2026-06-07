from __future__ import annotations

from collections import defaultdict


class MetricsRegistry:
    def __init__(self) -> None:
        self.counters: dict[str, int] = defaultdict(int)

    def increment(self, name: str, value: int = 1) -> None:
        self.counters[name] += value


metrics = MetricsRegistry()
