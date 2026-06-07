from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """应用操作审计日志记录。"""

    __tablename__ = "audit_logs"
    __table_args__ = {"comment": "重要应用操作的审计日志。"}

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="操作名称。",
    )
    result: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="操作结果。",
    )
    actor_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="操作者标识。",
    )
    trace_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="请求或链路追踪 ID。",
    )
    resource_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="影响资源类型。",
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="影响资源 ID。",
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
        comment="审计扩展上下文。",
    )
