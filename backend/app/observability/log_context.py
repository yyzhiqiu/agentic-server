from __future__ import annotations

from app.common.context import get_request_id, get_trace_id, get_user_id


def current_log_context() -> dict[str, str | None]:
    return {
        "trace_id": get_trace_id(),
        "request_id": get_request_id(),
        "user_id": get_user_id(),
    }
