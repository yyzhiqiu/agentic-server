from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from app.observability.tracing import trace_operation


F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def observe_node(name: str | None = None) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            with trace_operation(name or func.__name__):
                return await func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator
