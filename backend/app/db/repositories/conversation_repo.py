"""会话数据访问辅助逻辑。

本 Repository 只负责会话的持久化和查询拼装，不负责事务边界，
也不会直接提交数据库会话。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mixins import utc_now
from app.db.models.conversation import Conversation
from app.db.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """面向用户范围会话查询的 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Conversation)

    async def list_by_user(self, user_id: str, *, limit: int = 20, offset: int = 0) -> list[Conversation]:
        """列出指定用户拥有且未被软删除的会话。

        参数：
            user_id: 需要读取会话的所属用户。
            limit: 最多返回的记录数。
            offset: 返回结果前需要跳过的记录数。

        返回：
            按创建时间倒序排列的未删除会话列表。
        """

        result = await self.session.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
            .order_by(Conversation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_user(self, user_id: str) -> int:
        """统计指定用户拥有且未被软删除的会话数量。"""

        result = await self.session.execute(
            select(func.count())
            .select_from(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
        )
        return int(result.scalar_one())

    async def get_by_id_for_user(
        self,
        conversation_id: str,
        user_id: str,
    ) -> Conversation | None:
        """当拥有者匹配时返回未被软删除的会话。"""

        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def soft_delete(self, conversation: Conversation) -> Conversation:
        """将会话标记为已删除，而不是物理删除数据行。"""

        conversation.deleted_at = utc_now()
        await self.session.flush()
        return conversation
