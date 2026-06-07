"""审计事件 Schema。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.audit.enums import AuditAction, AuditResult


class AuditEvent(BaseModel):
    """统一的审计事件负载。"""

    action: AuditAction
    result: AuditResult = AuditResult.SUCCESS
    actor_id: str | None = None
    trace_id: str | None = None
    agent_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
