from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.audit.enums import AuditAction, AuditResult


class AuditEvent(BaseModel):
    action: AuditAction
    result: AuditResult = AuditResult.SUCCESS
    actor_id: str | None = None
    trace_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
