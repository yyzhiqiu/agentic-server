from __future__ import annotations

from pydantic import BaseModel, Field


class IdPath(BaseModel):
    id: str = Field(min_length=1)


class PageQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
