from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Document(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """与文件关联的文档记录。"""

    __tablename__ = "documents"
    __table_args__ = {"comment": "与文件关联的文档内容。"}

    file_id: Mapped[str | None] = mapped_column(
        ForeignKey("files.id"),
        nullable=True,
        comment="来源文件 ID。",
    )
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="文档标题。",
    )
    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="标准化后的文档内容。",
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
        comment="文档扩展元数据。",
    )
