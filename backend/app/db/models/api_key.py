from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ApiKey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """签发给用户的 API Key 记录。"""

    __tablename__ = "api_keys"
    __table_args__ = {"comment": "签发给用户的 API Key 记录。"}

    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        comment="所属用户 ID。",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="API Key 展示名称。",
    )
    key_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="API Key 哈希值。",
    )
    expires_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="API Key 过期时间。",
    )
