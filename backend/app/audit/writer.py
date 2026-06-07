"""审计写入器实现。"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.schemas import AuditEvent
from app.db.models.audit_log import AuditLog
from app.db.repositories.audit_log_repo import AuditLogRepository
from app.db.transaction import transaction


class AuditWriter(Protocol):
    """可插拔审计事件落地实现需要遵守的协议。"""

    async def write(self, event: AuditEvent) -> None:
        ...


class DatabaseAuditWriter:
    """将审计事件写入 ``audit_logs`` 表。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _write_with_repository(self, event: AuditEvent) -> None:
        """通过 Repository 层写入一条审计记录。"""

        repo = AuditLogRepository(self.session)
        metadata = dict(event.metadata)
        if event.agent_id is not None:
            metadata.setdefault("agent_id", event.agent_id)
        await repo.add(
            AuditLog(
                action=event.action.value,
                result=event.result.value,
                actor_id=event.actor_id,
                trace_id=event.trace_id,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                metadata_=metadata,
            )
        )

    async def write(self, event: AuditEvent) -> None:
        """在安全的事务边界内持久化审计事件。"""

        async with transaction(self.session):
            await self._write_with_repository(event)
