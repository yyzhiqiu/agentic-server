from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Message(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """会话消息记录。"""

    __tablename__ = "messages"
    __table_args__ = {"comment": "会话中的消息记录。"}

    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=False,
        comment="所属会话 ID。",
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="消息角色，如 user 或 assistant。",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息内容。",
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
        comment="消息扩展元数据。",
    )
