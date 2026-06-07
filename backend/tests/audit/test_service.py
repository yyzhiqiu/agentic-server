from __future__ import annotations

import pytest

from app.audit.enums import AuditAction, AuditResult
from app.audit.schemas import AuditEvent
from app.audit.service import AuditService


class _FailingAuditWriter:
    async def write(self, event: AuditEvent) -> None:
        raise RuntimeError("audit sink is unavailable")


@pytest.mark.asyncio
async def test_audit_service_swallows_writer_failures() -> None:
    service = AuditService(writer=_FailingAuditWriter())

    await service.record(
        AuditEvent(
            action=AuditAction.FILE_UPLOAD,
            result=AuditResult.SUCCESS,
            actor_id="user-1",
            resource_type="file",
            resource_id="file-1",
        )
    )
