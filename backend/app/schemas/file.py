"""文件相关请求与响应 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FileRead(BaseModel):
    """API 层返回的文件元数据序列化结构。"""

    id: str
    filename: str
    content_type: str | None = None
    storage_key: str | None = None
    size: int | None = None
    user_id: str | None = None
    status: str = "registered"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class FileList(BaseModel):
    """用于列表视图的分页文件元数据负载。"""

    items: list[FileRead] = Field(default_factory=list)
    total: int = 0
