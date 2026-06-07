"""会话相关请求与响应 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.message import MessageRead


class ConversationCreate(BaseModel):
    """用于创建新会话的请求负载。"""

    title: str | None = None
    agent_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationRead(BaseModel):
    """用于列表响应的会话元数据序列化结构。"""

    id: str
    title: str | None = None
    user_id: str | None = None
    agent_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class ConversationDetail(ConversationRead):
    """包含已持久化消息的会话详情负载。"""

    messages: list[MessageRead] = Field(default_factory=list)


class ConversationList(BaseModel):
    """分页形式的会话列表负载。"""

    items: list[ConversationRead] = Field(default_factory=list)
    total: int = 0
