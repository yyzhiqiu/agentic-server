"""Agent 控制与运行记录响应 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.tool_call import ToolCallRead


class AgentStatus(BaseModel):
    """单个运行记录使用的轻量控制状态负载。"""

    status: Literal["idle", "running", "interrupted", "completed", "failed"] = "idle"
    run_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentRunListItem(BaseModel):
    """用于列表视图的 Agent 运行记录摘要。"""

    id: str
    conversation_id: str | None = None
    status: Literal["running", "interrupted", "completed", "failed", "created"] = "created"
    started_at: datetime | None = None
    updated_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    trace_id: str | None = None
    error_message: str | None = None
    error_code: str | None = None
    interruption_reason: str | None = None


class AgentRunDetail(AgentRunListItem):
    """用于详情视图的 Agent 运行记录完整负载。"""

    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[ToolCallRead] = Field(default_factory=list)


class AgentRunList(BaseModel):
    """分页形式的 Agent 运行记录列表负载。"""

    items: list[AgentRunListItem] = Field(default_factory=list)
    total: int = 0


class AgentResumeRequest(BaseModel):
    """用于将运行记录标记为恢复执行的请求负载。"""

    run_id: str
    input: dict[str, Any] = Field(default_factory=dict)


class AgentInterruptRequest(BaseModel):
    """用于将运行记录标记为中断的请求负载。"""

    run_id: str
    reason: str | None = None
