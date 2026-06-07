from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    SUCCESS = "000000"
    REQUEST_VALIDATION_ERROR = "A00001"
    AUTH_ERROR = "A00002"
    FORBIDDEN = "A00003"
    NOT_FOUND = "A00004"
    INTERNAL_ERROR = "S00001"
    SERVICE_UNAVAILABLE = "S00002"
    LLM_ERROR = "L00001"
    GRAPH_ERROR = "G00001"
    DATABASE_ERROR = "D00001"


ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.SUCCESS: "success",
    ErrorCode.REQUEST_VALIDATION_ERROR: "请求参数错误",
    ErrorCode.AUTH_ERROR: "认证失败",
    ErrorCode.FORBIDDEN: "无访问权限",
    ErrorCode.NOT_FOUND: "资源不存在",
    ErrorCode.INTERNAL_ERROR: "服务器内部错误",
    ErrorCode.SERVICE_UNAVAILABLE: "服务暂不可用",
    ErrorCode.LLM_ERROR: "LLM 调用失败",
    ErrorCode.GRAPH_ERROR: "Agent Graph 执行失败",
    ErrorCode.DATABASE_ERROR: "数据库访问失败",
}


def get_error_message(code: ErrorCode | str) -> str:
    error_code = ErrorCode(code)
    return ERROR_MESSAGES[error_code]
