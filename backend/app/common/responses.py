from __future__ import annotations

from typing import Any

from app.common.context import get_trace_id
from app.common.error_codes import ErrorCode, get_error_message


def build_response(
    *,
    success: bool,
    code: ErrorCode | str,
    message: str,
    data: Any | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    return {
        "success": success,
        "code": code.value if isinstance(code, ErrorCode) else code,
        "message": message,
        "data": {} if data is None else data,
        "trace_id": trace_id or get_trace_id(),
    }


def success_response(
    data: Any | None = None,
    *,
    message: str = "success",
    code: ErrorCode = ErrorCode.SUCCESS,
) -> dict[str, Any]:
    return build_response(success=True, code=code, message=message, data=data)


def error_response(
    code: ErrorCode | str,
    message: str | None = None,
    data: Any | None = None,
) -> dict[str, Any]:
    error_code = ErrorCode(code)
    return build_response(
        success=False,
        code=error_code,
        message=message or get_error_message(error_code),
        data=data,
    )
