"""消息数据访问辅助逻辑。

本 Repository 只负责消息查询拼装和持久化基础能力，不负责事务边界，
也不会直接提交数据库会话。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.message import Message
from app.db.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """处理已持久化会话消息的 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Message)

    async def list_by_conversation(
        self,
        conversation_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Message]:
        """按时间顺序列出某个会话下未被软删除的消息。

        参数：
            conversation_id: 需要返回消息的会话 ID。
            limit: 最多返回的记录数。
            offset: 返回结果前需要跳过的记录数。

        返回：
            按创建时间正序排列的未删除消息列表。

        说明：
            本方法不负责做用户范围校验。调用方在读取消息历史前，
            应先校验会话归属。
        """

        result = await self.session.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
            )
            .order_by(Message.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_conversation(self, conversation_id: str) -> int:
        """统计某个会话下未被软删除的已存储消息数量。

        参数：
            conversation_id: 需要统计已持久化消息的会话 ID。

        返回：
            该会话下未被软删除的消息数量。

        说明：
            本方法不负责做用户范围校验。调用方在向客户端暴露结果前，
            应先校验会话归属。
        """

        result = await self.session.execute(
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
            )
        )
        return int(result.scalar_one())
