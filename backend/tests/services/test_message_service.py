"""消息读取服务的测试。"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.common.exceptions import AppException
from app.db.models.message import Message
from app.services.message_service import MessageService


class _FakeSession:
    """供只读消息服务测试使用的最小会话占位对象。"""


class _FakeConversation:
    """消息服务测试中使用的最小会话实体。"""

    def __init__(self, *, id: str, user_id: str) -> None:
        self.id = id
        self.user_id = user_id
        self.deleted_at = None


class _FakeConversationRepository:
    """用于归属校验的内存版会话 Repository 替身。"""

    def __init__(self) -> None:
        self.items: dict[str, _FakeConversation] = {}

    async def get_by_id_for_user(self, conversation_id: str, user_id: str):
        item = self.items.get(conversation_id)
        if item is None or item.user_id != user_id or item.deleted_at is not None:
            return None
        return item


class _FakeMessageRepository:
    """用于分页读取的内存版消息 Repository 替身。"""

    def __init__(self) -> None:
        self.items: list[Message] = []

    async def list_by_conversation(
        self,
        conversation_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Message]:
        items = [
            item
            for item in self.items
            if item.conversation_id == conversation_id and item.deleted_at is None
        ]
        items.sort(key=lambda item: item.created_at or datetime.now(timezone.utc))
        return items[offset : offset + limit]

    async def count_by_conversation(self, conversation_id: str) -> int:
        return len(
            [
                item
                for item in self.items
                if item.conversation_id == conversation_id and item.deleted_at is None
            ]
        )


@pytest.mark.asyncio
async def test_message_service_lists_user_conversation_messages() -> None:
    conversation_repository = _FakeConversationRepository()
    conversation_repository.items["conversation-1"] = _FakeConversation(
        id="conversation-1",
        user_id="user-1",
    )
    message_repository = _FakeMessageRepository()
    message_repository.items.extend(
        [
            Message(
                id="message-1",
                conversation_id="conversation-1",
                role="user",
                content="hello",
                metadata_={},
                created_at=datetime(2026, 6, 7, 10, 0, 0, tzinfo=timezone.utc),
            ),
            Message(
                id="message-2",
                conversation_id="conversation-1",
                role="assistant",
                content="world",
                metadata_={"source": "mock"},
                created_at=datetime(2026, 6, 7, 10, 0, 1, tzinfo=timezone.utc),
            ),
        ]
    )
    service = MessageService(
        session=_FakeSession(),  # type: ignore[arg-type]
        conversation_repository=conversation_repository,  # type: ignore[arg-type]
        message_repository=message_repository,  # type: ignore[arg-type]
    )

    listed = await service.list_by_conversation("conversation-1", "user-1")
    assert listed.total == 2
    assert [item.role for item in listed.items] == ["user", "assistant"]
    assert listed.items[1].metadata == {"source": "mock"}


@pytest.mark.asyncio
async def test_message_service_enforces_conversation_ownership() -> None:
    service = MessageService(
        session=_FakeSession(),  # type: ignore[arg-type]
        conversation_repository=_FakeConversationRepository(),  # type: ignore[arg-type]
        message_repository=_FakeMessageRepository(),  # type: ignore[arg-type]
    )

    with pytest.raises(AppException) as exc_info:
        await service.list_by_conversation("missing", "user-1")

    assert exc_info.value.status_code == 404
