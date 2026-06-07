"""消息读取编排服务。

本服务位于 API 层与 Repository 层之间，对外暴露清晰的用户范围消息读取契约。
它会先校验会话归属，再返回分页消息历史，从而让权限判断不落入 Repository
代码中。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_codes import ErrorCode
from app.common.exceptions import AppException
from app.db.models.message import Message
from app.db.repositories.conversation_repo import ConversationRepository
from app.db.repositories.message_repo import MessageRepository
from app.schemas.message import MessageList, MessageRead


class MessageService:
    """编排用户范围内的消息读取行为。"""

    def __init__(
        self,
        *,
        session: AsyncSession,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
    ) -> None:
        self.session = session
        self.conversation_repository = conversation_repository
        self.message_repository = message_repository

    @staticmethod
    def _to_read(message: Message) -> MessageRead:
        """将已持久化消息实体映射为 API Schema。"""

        return MessageRead(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            metadata=dict(message.metadata_ or {}),
            created_at=message.created_at,
        )

    async def list_by_conversation(
        self,
        conversation_id: str,
        user_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> MessageList:
        """列出当前用户拥有会话下的已持久化消息。

        参数：
            conversation_id: 需要读取消息的会话 ID。
            user_id: 用于做归属校验的当前调用方用户 ID。
            limit: 最多返回的消息记录数。
            offset: 返回结果前需要跳过的记录数。

        返回：
            按时间顺序排列的分页消息负载。

        异常：
            AppException: 当会话不存在，或不属于当前用户时抛出。
        """

        conversation = await self.conversation_repository.get_by_id_for_user(
            conversation_id,
            user_id,
        )
        if conversation is None:
            raise AppException(
                ErrorCode.NOT_FOUND,
                status_code=404,
                data={"conversation_id": conversation_id},
            )

        items = await self.message_repository.list_by_conversation(
            conversation_id,
            limit=limit,
            offset=offset,
        )
        total = await self.message_repository.count_by_conversation(conversation_id)
        return MessageList(
            items=[self._to_read(item) for item in items],
            total=total,
        )
