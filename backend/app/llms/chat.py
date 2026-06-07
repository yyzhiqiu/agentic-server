from __future__ import annotations

from typing import Any

from app.core.config import settings


def create_chat_openai() -> Any | None:
    if not settings.LLM_API_KEY:
        return None
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": settings.LLM_MODEL,
        "api_key": settings.LLM_API_KEY,
        "temperature": settings.LLM_TEMPERATURE,
        "timeout": settings.LLM_TIMEOUT,
        "max_retries": settings.LLM_MAX_RETRIES,
    }
    if settings.LLM_BASE_URL:
        kwargs["base_url"] = settings.LLM_BASE_URL
    return ChatOpenAI(**kwargs)
