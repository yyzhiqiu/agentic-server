from __future__ import annotations

from app.common.error_codes import ErrorCode, get_error_message


def test_error_codes_have_success_and_validation() -> None:
    assert ErrorCode.SUCCESS.value == "000000"
    assert get_error_message(ErrorCode.REQUEST_VALIDATION_ERROR) == "请求参数错误"
