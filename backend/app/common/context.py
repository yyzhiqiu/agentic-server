from __future__ import annotations

from contextvars import ContextVar, Token


trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


def get_trace_id() -> str | None:
    return trace_id_var.get()


def get_request_id() -> str | None:
    return request_id_var.get()


def get_user_id() -> str | None:
    return user_id_var.get()


def set_trace_id(trace_id: str) -> Token[str | None]:
    return trace_id_var.set(trace_id)


def set_request_id(request_id: str) -> Token[str | None]:
    return request_id_var.set(request_id)


def set_user_id(user_id: str | None) -> Token[str | None]:
    return user_id_var.set(user_id)


def reset_context(
    trace_token: Token[str | None],
    request_token: Token[str | None],
    user_token: Token[str | None],
) -> None:
    trace_id_var.reset(trace_token)
    request_id_var.reset(request_token)
    user_id_var.reset(user_token)
