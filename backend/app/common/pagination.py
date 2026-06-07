from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.common.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


T = TypeVar("T")


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
