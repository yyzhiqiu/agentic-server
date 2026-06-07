"""会话业务编排服务。

本服务为 API 层协调会话的增删改查行为，负责写操作的事务边界、
删除类动作的尽力而为审计记录，并把所有数据库访问委托给 Repository 层。
"""

from __future__ import annotations

from app.audit.enums import AuditAction, AuditResult
from app.audit.schemas import AuditEvent
from app.audit.service import AuditService
from app.common.context import get_trace_id
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_codes import ErrorCode
from app.common.exceptions import AppException
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.repositories.conversation_repo import ConversationRepository
from app.db.repositories.message_repo import MessageRepository
from app.db.transaction import transaction
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationList,
    ConversationRead,
)
from app.schemas.message import MessageRead
from app.services.user_service import UserService


class ConversationService:
    """编排当前用户的会话增删改查操作。

    本服务负责控制写操作的事务边界，并将 ORM 实体转换为响应 Schema。
    Repository 层内部不主动提交事务。
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository | None = None,
        user_service: UserService | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.session = session
        self.conversation_repository = conversation_repository
        self.message_repository = message_repository
        self.user_service = user_service
        self.audit_service = audit_service or AuditService()

    @staticmethod
    def _to_read(conversation: Conversation) -> ConversationRead:
        """将会话 ORM 实体映射为 API 响应 Schema。"""

        return ConversationRead(
            id=conversation.id,
            title=conversation.title,
            user_id=conversation.user_id,
            metadata=dict(conversation.metadata_ or {}),
            created_at=conversation.created_at,
        )

    @staticmethod
    def _message_to_read(message: Message) -> MessageRead:
        """将已持久化的消息实体映射为 API 响应 Schema。"""

        metadata = dict(message.metadata_ or {})
        return MessageRead(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            metadata=metadata,
            created_at=message.created_at,
        )

    async def create(self, payload: ConversationCreate, user_id: str) -> ConversationRead:
        """为当前用户创建会话。

        参数：
            payload: 用于初始化会话的请求数据。
            user_id: 新会话的拥有者 ID。

        返回：
            已持久化的会话响应数据。

        副作用：
            会在 Service 层管理的事务中向 conversations 表写入新记录。
        """

        if self.user_service is not None:
            await self.user_service.ensure_user(user_id, name=user_id)

        async with transaction(self.session):
            conversation = Conversation(
                user_id=user_id,
                title=payload.title,
                metadata_=dict(payload.metadata),
            )
            created = await self.conversation_repository.add(conversation)
        return self._to_read(created)

    async def list(
        self,
        user_id: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> ConversationList:
        """列出当前用户拥有的会话。"""

        items = await self.conversation_repository.list_by_user(
            user_id,
            limit=limit,
            offset=offset,
        )
        total = await self.conversation_repository.count_by_user(user_id)
        return ConversationList(
            items=[self._to_read(item) for item in items],
            total=total,
        )

    async def get(self, conversation_id: str, user_id: str) -> ConversationDetail:
        """获取当前用户拥有的单个会话。

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

        messages: list[MessageRead] = []
        if self.message_repository is not None:
            items = await self.message_repository.list_by_conversation(
                conversation.id,
                limit=200,
                offset=0,
            )
            messages = [self._message_to_read(item) for item in items]

        return ConversationDetail(
            **self._to_read(conversation).model_dump(),
            messages=messages,
        )

    async def delete(self, conversation_id: str, user_id: str) -> dict[str, str]:
        """软删除当前用户拥有的会话。

        副作用：
            会将会话标记为已删除，并在写入成功后尽力记录一条审计事件。
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

        async with transaction(self.session):
            await self.conversation_repository.soft_delete(conversation)

        await self.audit_service.record(
            AuditEvent(
                action=AuditAction.DELETE,
                result=AuditResult.SUCCESS,
                actor_id=user_id,
                trace_id=get_trace_id(),
                resource_type="conversation",
                resource_id=conversation_id,
                metadata={"status": "deleted"},
            )
        )
        return {"id": conversation_id, "status": "deleted"}
