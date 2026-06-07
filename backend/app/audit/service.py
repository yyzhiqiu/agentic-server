"""审计服务实现。

本模块负责以尽力而为的方式记录审计事件，避免可观测性或审计链路抖动
影响聊天、文件或 Agent 主流程的可用性。
"""

from __future__ import annotations

import logging

from app.audit.schemas import AuditEvent
from app.audit.writer import AuditWriter

logger = logging.getLogger(__name__)


class AuditService:
    """在不打断主业务流程的前提下记录审计事件。"""

    def __init__(self, writer: AuditWriter | None = None) -> None:
        self.writer = writer

    async def record(self, event: AuditEvent) -> None:
        """在配置了写入器时持久化审计事件。

        审计写入明确采用尽力而为策略。若写入失败，只降级为告警日志，
        避免因为审计存储暂时不可用而导致聊天、文件或 Agent 流程失败。
        """

        if self.writer is None:
            return
        try:
            await self.writer.write(event)
        except Exception:
            logger.warning("记录审计事件失败", exc_info=True)
