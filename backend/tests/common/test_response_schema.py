from __future__ import annotations

from app.common.responses import error_response, success_response
from app.common.error_codes import ErrorCode


def test_success_response_schema() -> None:
    payload = success_response({"hello": "world"})
    assert payload["success"] is True
    assert payload["code"] == ErrorCode.SUCCESS.value
    assert payload["data"] == {"hello": "world"}


def test_error_response_schema() -> None:
    payload = error_response(ErrorCode.REQUEST_VALIDATION_ERROR)
    assert payload["success"] is False
    assert payload["code"] == ErrorCode.REQUEST_VALIDATION_ERROR.value
    assert payload["message"] == "请求参数错误"
