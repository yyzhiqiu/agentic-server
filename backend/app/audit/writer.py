"""审计写入器实现。

本模块定义可插拔的审计写入协议，并提供基于数据库的默认实现。
写入逻辑只负责审计落库，不承担主业务事务编排职责。
"""

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
        await repo.add(
            AuditLog(
                action=event.action.value,
                result=event.result.value,
                actor_id=event.actor_id,
                trace_id=event.trace_id,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                metadata_=event.metadata,
            )
        )

    async def write(self, event: AuditEvent) -> None:
        """在安全的事务边界内持久化审计事件。

        写入器可能在主业务事务已经结束后被调用，因此需要在必要时自行开启事务。
        如果调用方已经持有活动事务，则复用现有事务，避免再次嵌套
        ``session.begin()`` 事务块。
        """

        async with transaction(self.session):
            await self._write_with_repository(event)
