from __future__ import annotations

from typing import Any

from app.common.error_codes import ErrorCode, get_error_message


class AppException(Exception):
    def __init__(
        self,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        message: str | None = None,
        *,
        status_code: int = 500,
        data: Any | None = None,
    ) -> None:
        self.code = code
        self.message = message or get_error_message(code)
        self.status_code = status_code
        self.data = data or {}
        super().__init__(self.message)


class AuthException(AppException):
    def __init__(self, message: str | None = None, data: Any | None = None) -> None:
        super().__init__(ErrorCode.AUTH_ERROR, message, status_code=401, data=data)


class LLMException(AppException):
    def __init__(self, message: str | None = None, data: Any | None = None) -> None:
        super().__init__(ErrorCode.LLM_ERROR, message, status_code=503, data=data)


class GraphException(AppException):
    def __init__(self, message: str | None = None, data: Any | None = None) -> None:
        super().__init__(ErrorCode.GRAPH_ERROR, message, status_code=500, data=data)


class DatabaseException(AppException):
    def __init__(self, message: str | None = None, data: Any | None = None) -> None:
        super().__init__(ErrorCode.DATABASE_ERROR, message, status_code=500, data=data)
