"""文件元数据的数据访问辅助逻辑。

本 Repository 只负责文件元数据的查询拼装和持久化基础能力，
事务边界仍由 Service 层统一管理。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mixins import utc_now
from app.db.models.file import File
from app.db.repositories.base import BaseRepository


class FileRepository(BaseRepository[File]):
    """面向用户范围文件元数据查询的 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, File)

    async def list_by_user(
        self,
        user_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[File]:
        """列出指定用户拥有且未被软删除的文件。"""

        result = await self.session.execute(
            select(File)
            .where(
                File.user_id == user_id,
                File.deleted_at.is_(None),
            )
            .order_by(File.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_user(self, user_id: str) -> int:
        """统计指定用户拥有且未被软删除的文件数量。"""

        result = await self.session.execute(
            select(func.count())
            .select_from(File)
            .where(
                File.user_id == user_id,
                File.deleted_at.is_(None),
            )
        )
        return int(result.scalar_one())

    async def get_active_by_id(self, file_id: str) -> File | None:
        """根据标识返回未被软删除的文件记录。"""

        result = await self.session.execute(
            select(File).where(
                File.id == file_id,
                File.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_user(self, file_id: str, user_id: str) -> File | None:
        """当文件归属于指定用户时返回未被软删除的文件。"""

        result = await self.session.execute(
            select(File).where(
                File.id == file_id,
                File.user_id == user_id,
                File.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def soft_delete(self, file: File) -> File:
        """将文件标记为已删除，而不是物理删除数据行。"""

        file.deleted_at = utc_now()
        await self.session.flush()
        return file
