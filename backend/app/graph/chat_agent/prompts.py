"""通用聊天 Agent 的专属提示词。"""

from __future__ import annotations

from app.graph.shared.prompts import BASE_SYSTEM_PROMPT, FORMAT_PROMPT, SAFETY_PROMPT


CHAT_AGENT_SYSTEM_PROMPT = "\n".join(
    [
        BASE_SYSTEM_PROMPT,
        SAFETY_PROMPT,
        FORMAT_PROMPT,
        "你是一个通用聊天 Agent，适合处理普通问答、轻量分析和多轮对话。",
    ]
)

