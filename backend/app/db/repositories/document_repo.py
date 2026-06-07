"""文档数据访问辅助逻辑。

本 Repository 只负责与上传文件关联的文档行查询拼装和软删除基础能力，
事务边界仍由 Service 层控制。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mixins import utc_now
from app.db.models.document import Document
from app.db.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """处理文件关联文档记录的 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Document)

    async def get_active_by_id(self, document_id: str) -> Document | None:
        """根据标识返回一条有效的文档记录。"""

        result = await self.session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_file_id(self, file_id: str) -> list[Document]:
        """返回与单个文件关联的有效文档记录。"""

        result = await self.session.execute(
            select(Document).where(
                Document.file_id == file_id,
                Document.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def soft_delete(self, document: Document) -> Document:
        """将文档记录标记为已删除，而不是物理移除。"""

        document.deleted_at = utc_now()
        await self.session.flush()
        return document
