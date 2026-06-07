"""消息相关请求与响应 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """用于表示已持久化会话消息的负载。"""

    conversation_id: str
    role: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageRead(MessageCreate):
    """读取接口返回的消息序列化负载。"""

    id: str
    created_at: datetime | None = None


class MessageList(BaseModel):
    """单个会话下的分页消息列表负载。"""

    items: list[MessageRead] = Field(default_factory=list)
    total: int = 0
