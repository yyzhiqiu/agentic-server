"""上传文件元数据的 ORM 模型。

`files` 表用于保存上传文件的元数据、归属信息以及定位二进制内容的
对象存储键。真实文件内容保存在数据库之外的对象存储中。
"""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class File(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """归属于用户的上传文件元数据。"""

    __tablename__ = "files"
    __table_args__ = {"comment": "上传文件元数据。"}

    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        comment="所属用户 ID。",
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="原始文件名。",
    )
    content_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="文件 MIME 类型。",
    )
    storage_key: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="文件内容的对象存储键。",
    )
    size: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="文件大小（字节）。",
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
        comment="文件扩展元数据。",
    )
