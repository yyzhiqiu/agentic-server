"""共享的人机交互协议与辅助函数。"""

from __future__ import annotations

from typing import Any

from langgraph.types import Interrupt

from app.schemas.chat import PendingHumanInput


def normalize_pending_human_input(payload: Any) -> PendingHumanInput | None:
    """把任意中断负载规整为统一的人机交互表单协议。"""

    if payload is None:
        return None
    if isinstance(payload, PendingHumanInput):
        return payload
    if isinstance(payload, Interrupt):
        return normalize_pending_human_input(payload.value)
    if isinstance(payload, dict):
        try:
            return PendingHumanInput.model_validate(payload)
        except Exception:
            return None
    return None


def pending_human_input_to_metadata(payload: PendingHumanInput | None) -> dict[str, Any]:
    """把待补参表单转换为可安全持久化的 metadata 结构。"""

    if payload is None:
        return {}
    return payload.model_dump()
