from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.llms.chat import create_chat_openai

logger = logging.getLogger(__name__)


def create_llm() -> Any | None:
    if not settings.LLM_API_KEY:
        logger.info("LLM_API_KEY 为空，将使用模拟响应模式")
        return None
    provider = settings.LLM_PROVIDER.lower()
    if provider in {"openai", "deepseek", "openai-compatible"}:
        return create_chat_openai()
    logger.warning("不支持的 LLM_PROVIDER=%s，将使用模拟响应模式", provider)
    return None
