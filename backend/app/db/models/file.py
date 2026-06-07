"""上传文件元数据的 ORM 模型。

`files` 表负责保存上传层面的元数据、资源归属信息，以及定位二进制内容的
对象存储键。真实文件内容保存在配置好的对象存储后端中，而不是直接写入
数据库行。
"""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class File(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """归属于用户的上传文件元数据。"""

    __tablename__ = "files"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
