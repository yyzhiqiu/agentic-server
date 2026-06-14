"""聊天请求、响应与流式事件 Schema。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.tool_call import ToolCallPayload


Role = Literal["system", "user", "assistant", "tool"]


class HumanInputOption(BaseModel):
    """结构化人机交互字段中的单个候选项。"""

    label: str = Field(min_length=1)
    value: str = Field(min_length=1)


class HumanInputField(BaseModel):
    """描述前端可渲染的单个补参字段。"""

    name: str = Field(min_length=1)
    label: str = Field(min_length=1)
    type: Literal["text", "select"] = "text"
    required: bool = True
    placeholder: str | None = None
    value: str | None = None
    allow_custom: bool = False
    custom_option_label: str | None = None
    custom_placeholder: str | None = None
    options: list[HumanInputOption] = Field(default_factory=list)


class PendingHumanInput(BaseModel):
    """描述当前运行暂停时需要用户补充的结构化输入。"""

    kind: Literal["form"] = "form"
    title: str = Field(min_length=1)
    message: str = Field(min_length=1)
    fields: list[HumanInputField] = Field(default_factory=list)
    submit_label: str = Field(min_length=1)
    missing_fields: list[str] = Field(default_factory=list)


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
    pending_human_input: PendingHumanInput | None = None


class ChatResumeRequest(BaseModel):
    """面向用户侧的人机补参恢复请求。"""

    run_id: str = Field(min_length=1)
    input: dict[str, Any] = Field(default_factory=dict)


class ChatStreamEvent(BaseModel):
    """流式聊天事件。"""

    type: Literal[
        "start",
        "message",
        "node_start",
        "node_end",
        "tool_start",
        "tool_end",
        "interrupt",
        "error",
        "done",
    ] = "message"
    content: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
