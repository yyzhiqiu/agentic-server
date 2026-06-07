"""工具调用相关请求与响应 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolCallPayload(BaseModel):
    """图执行与聊天响应中携带的结构化工具调用负载。"""

    tool_name: str
    status: str = "completed"
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCallRead(ToolCallPayload):
    """读取接口返回的工具调用序列化负载。"""

    id: str
    agent_run_id: str | None = None
    agent_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
