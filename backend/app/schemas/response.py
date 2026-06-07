from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    code: str = "000000"
    message: str = "success"
    data: T | dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None


class PageResponse(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class StreamEvent(BaseModel):
    event: str = "message"
    data: dict[str, Any] = Field(default_factory=dict)
