from __future__ import annotations

from typing import Any


def create_langchain_callbacks(langfuse_client: Any | None = None) -> list[Any]:
    if langfuse_client is None:
        return []
    return []
