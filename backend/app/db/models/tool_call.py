from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ToolCall(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """工具调用记录。"""

    __tablename__ = "tool_calls"
    __table_args__ = {"comment": "智能体工具调用记录。"}

    agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id"),
        nullable=True,
        comment="所属智能体运行 ID。",
    )
    tool_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="工具名称。",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="created",
        nullable=False,
        comment="当前工具调用状态。",
    )
    input: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        comment="序列化后的工具输入载荷。",
    )
    output: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        comment="序列化后的工具输出载荷。",
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
        comment="工具调用扩展元数据。",
    )
