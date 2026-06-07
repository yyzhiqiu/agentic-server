"""聊天请求、响应与流式事件 Schema。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.tool_call import ToolCallPayload


Role = Literal["system", "user", "assistant", "tool"]


class ChatMessage(BaseModel):
    """单条聊天消息。"""

    role: Role = "user"
    content: str = Field(min_length=1)
    name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """通用聊天请求。"""

    messages: list[ChatMessage] = Field(min_length=1)
    conversation_id: str | None = None
    user_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """通用聊天响应。"""

    conversation_id: str | None = None
    agent_id: str | None = None
    message: ChatMessage
    messages: list[ChatMessage] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[ToolCallPayload] = Field(default_factory=list)


class ChatStreamEvent(BaseModel):
    """流式聊天事件。"""

    type: Literal["start", "message", "error", "done"] = "message"
    content: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
