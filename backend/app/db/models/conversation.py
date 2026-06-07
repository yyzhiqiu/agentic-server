"""会话 ORM 模型。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """会话记录。"""

    __tablename__ = "conversations"
    __table_args__ = {"comment": "用户与智能体的会话记录。"}

    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        comment="所属用户 ID。",
    )
    agent_id: Mapped[str] = mapped_column(
        String(100),
        default="chat_agent",
        nullable=False,
        comment="绑定的智能体 ID。",
    )
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="会话标题。",
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
        comment="会话扩展元数据。",
    )
