from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """应用用户记录。"""

    __tablename__ = "users"
    __table_args__ = {"comment": "应用用户与访客用户记录。"}

    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        comment="用户邮箱。",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        default=lambda: settings.GUEST_USER_NAME,
        nullable=False,
        comment="应用内展示名称。",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="用户是否处于启用状态。",
    )
