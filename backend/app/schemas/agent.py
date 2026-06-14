"""Agent 控制与运行记录响应 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, RootModel

from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.tool_call import ToolCallRead


class AgentMetadataResponse(BaseModel):
    """对外暴露的 Agent 元信息响应。"""

    agent_id: str
    name: str
    description: str
    version: str
    capabilities: list[str] = Field(default_factory=list)


class AgentListResponse(RootModel[list[AgentMetadataResponse]]):
    """可用 Agent 元信息列表响应。"""


class AgentChatRequest(ChatRequest):
    """指定 Agent 的聊天请求。

    在通用聊天结构之外，显式暴露代码类 Agent 常见的上下文字段，避免继续依赖
    ``metadata`` 中的隐式约定。
    """

    repository_context: dict[str, Any] = Field(default_factory=dict)
    changed_files: list[str] = Field(default_factory=list)
    task_type: str | None = None


class AgentChatResponse(ChatResponse):
    """指定 Agent 的聊天响应。"""


class AgentStatus(BaseModel):
    """单个运行记录使用的轻量控制状态负载。"""

    status: Literal["idle", "running", "interrupted", "cancelled", "completed", "failed"] = "idle"
    run_id: str | None = None
    agent_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentRunListItem(BaseModel):
    """用于列表视图的 Agent 运行记录摘要。"""

    id: str
    conversation_id: str | None = None
    agent_id: str | None = None
    status: Literal["running", "interrupted", "cancelled", "completed", "failed", "created"] = "created"
    started_at: datetime | None = None
    updated_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    trace_id: str | None = None
    error_message: str | None = None
    error_code: str | None = None
    interruption_reason: str | None = None
    pending_human_input: dict[str, Any] | None = None
    interrupt_source: str | None = None


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
    """用于恢复已中断运行的请求负载。"""

    run_id: str
    agent_id: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)


class AgentInterruptRequest(BaseModel):
    """用于将运行记录标记为中断的请求负载。"""

    run_id: str
    agent_id: str | None = None
    reason: str | None = None


class AgentCancelRequest(BaseModel):
    """用于将运行记录标记为取消的请求负载。"""

    run_id: str
    agent_id: str | None = None
    reason: str | None = None
