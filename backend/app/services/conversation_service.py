"""会话业务编排服务。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.enums import AuditAction, AuditResult
from app.audit.schemas import AuditEvent
from app.audit.service import AuditService
from app.common.context import get_trace_id
from app.common.error_codes import ErrorCode
from app.common.exceptions import AppException
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.repositories.conversation_repo import ConversationRepository
from app.db.repositories.message_repo import MessageRepository
from app.db.transaction import transaction
from app.graph.default import DEFAULT_AGENT_ID
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationList,
    ConversationRead,
)
from app.schemas.message import MessageRead
from app.services.user_service import UserService


class ConversationService:
    """编排当前用户的会话增删改查操作。"""

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
    def _agent_id(conversation: Conversation) -> str:
        """从一等字段或兼容元数据中提取绑定的 Agent 标识。"""

        if isinstance(conversation.agent_id, str) and conversation.agent_id:
            return conversation.agent_id

        metadata = dict(conversation.metadata_ or {})
        agent_id = metadata.get("agent_id")
        if isinstance(agent_id, str) and agent_id:
            return agent_id
        return DEFAULT_AGENT_ID

    @classmethod
    def _to_read(cls, conversation: Conversation) -> ConversationRead:
        """将会话 ORM 实体映射为 API 响应 Schema。"""

        return ConversationRead(
            id=conversation.id,
            title=conversation.title,
            user_id=conversation.user_id,
            agent_id=cls._agent_id(conversation),
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
        """为当前用户创建会话。"""

        if self.user_service is not None:
            await self.user_service.ensure_user(user_id, name=user_id)

        async with transaction(self.session):
            metadata = dict(payload.metadata)
            agent_id = payload.agent_id or metadata.get("agent_id") or DEFAULT_AGENT_ID
            metadata.setdefault("agent_id", agent_id)
            conversation = Conversation(
                user_id=user_id,
                agent_id=agent_id,
                title=payload.title,
                metadata_=metadata,
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
        """获取当前用户拥有的单个会话。"""

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
        """软删除当前用户拥有的会话。"""

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
                agent_id=self._agent_id(conversation),
                resource_type="conversation",
                resource_id=conversation_id,
                metadata={"status": "deleted"},
            )
        )
        return {"id": conversation_id, "status": "deleted"}
