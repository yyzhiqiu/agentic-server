"""智能体运行记录 ORM 模型。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AgentRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """智能体运行记录。"""

    __tablename__ = "agent_runs"
    __table_args__ = {"comment": "智能体运行记录。"}

    conversation_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=True,
        comment="关联会话 ID。",
    )
    agent_id: Mapped[str] = mapped_column(
        String(100),
        default="chat_agent",
        nullable=False,
        comment="执行该次运行的智能体 ID。",
    )
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        comment="发起用户 ID。",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="created",
        nullable=False,
        comment="当前运行状态。",
    )
    input: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        comment="序列化后的输入载荷。",
    )
    output: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        comment="序列化后的输出载荷。",
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
        comment="运行扩展元数据。",
    )
