from __future__ import annotations

from collections.abc import Generator

import pytest

from app.api.dependencies import get_conversation_service, get_message_service
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationList,
    ConversationRead,
)
from app.schemas.message import MessageList, MessageRead


class InMemoryConversationService:
    def __init__(self) -> None:
        self.items: dict[str, ConversationRead] = {}
        self.messages: dict[str, list[MessageRead]] = {}

    async def create(self, payload: ConversationCreate, user_id: str) -> ConversationRead:
        conversation_id = f"conversation-{len(self.items) + 1}"
        agent_id = payload.agent_id or payload.metadata.get("agent_id") or "chat_agent"
        conversation = ConversationRead(
            id=conversation_id,
            title=payload.title,
            user_id=user_id,
            agent_id=agent_id,
            metadata={**payload.metadata, "agent_id": agent_id},
        )
        self.items[conversation_id] = conversation
        self.messages[conversation_id] = [
            MessageRead(
                id=f"{conversation_id}-message-1",
                conversation_id=conversation_id,
                role="user",
                content="hello",
                metadata={},
            ),
            MessageRead(
                id=f"{conversation_id}-message-2",
                conversation_id=conversation_id,
                role="assistant",
                content="world",
                metadata={"source": "in-memory"},
            ),
        ]
        return conversation

    async def list(self, user_id: str, *, limit: int = 20, offset: int = 0) -> ConversationList:
        conversations = [
            conversation
            for conversation in self.items.values()
            if conversation.user_id == user_id
        ]
        return ConversationList(
            items=conversations[offset : offset + limit],
            total=len(conversations),
        )

    async def get(self, conversation_id: str, user_id: str) -> ConversationDetail:
        conversation = self.items[conversation_id]
        assert conversation.user_id == user_id
        return ConversationDetail(
            **conversation.model_dump(),
            messages=self.messages[conversation_id],
        )

    async def delete(self, conversation_id: str, user_id: str) -> dict[str, str]:
        conversation = self.items[conversation_id]
        assert conversation.user_id == user_id
        self.items.pop(conversation_id, None)
        return {"id": conversation_id, "status": "deleted"}


class InMemoryMessageService:
    def __init__(self, conversation_service: InMemoryConversationService) -> None:
        self.conversation_service = conversation_service

    async def list_by_conversation(
        self,
        conversation_id: str,
        user_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> MessageList:
        conversation = self.conversation_service.items[conversation_id]
        assert conversation.user_id == user_id
        items = self.conversation_service.messages[conversation_id]
        return MessageList(
            items=items[offset : offset + limit],
            total=len(items),
        )


@pytest.fixture
def conversation_service(client) -> Generator[InMemoryConversationService, None, None]:
    service = InMemoryConversationService()
    client.app.dependency_overrides[get_conversation_service] = lambda: service
    try:
        yield service
    finally:
        client.app.dependency_overrides.pop(get_conversation_service, None)


@pytest.fixture
def message_service(
    client,
    conversation_service: InMemoryConversationService,
) -> Generator[InMemoryMessageService, None, None]:
    service = InMemoryMessageService(conversation_service)
    client.app.dependency_overrides[get_message_service] = lambda: service
    try:
        yield service
    finally:
        client.app.dependency_overrides.pop(get_message_service, None)


def test_create_conversation_endpoint(client, conversation_service: InMemoryConversationService) -> None:
    response = client.post(
        "/v1/conversations",
        json={"title": "Demo Conversation", "agent_id": "code_agent"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["id"] == "conversation-1"
    assert payload["data"]["title"] == "Demo Conversation"
    assert payload["data"]["agent_id"] == "code_agent"


def test_list_and_get_conversation_endpoints(
    client,
    conversation_service: InMemoryConversationService,
    message_service: InMemoryMessageService,
) -> None:
    created = client.post(
        "/v1/conversations",
        json={"title": "Demo Conversation", "agent_id": "chat_agent"},
    )
    conversation_id = created.json()["data"]["id"]

    list_response = client.get("/v1/conversations")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["success"] is True
    assert list_payload["data"]["total"] == 1
    assert list_payload["data"]["items"][0]["id"] == conversation_id
    assert list_payload["data"]["items"][0]["agent_id"] == "chat_agent"

    get_response = client.get(f"/v1/conversations/{conversation_id}")
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["success"] is True
    assert get_payload["data"]["id"] == conversation_id
    assert [message["role"] for message in get_payload["data"]["messages"]] == ["user", "assistant"]
    assert get_payload["data"]["messages"][1]["metadata"] == {"source": "in-memory"}

    messages_response = client.get(f"/v1/conversations/{conversation_id}/messages")
    assert messages_response.status_code == 200
    messages_payload = messages_response.json()
    assert messages_payload["success"] is True
    assert messages_payload["data"]["total"] == 2
    assert [message["role"] for message in messages_payload["data"]["items"]] == [
        "user",
        "assistant",
    ]


def test_delete_conversation_endpoint(
    client,
    conversation_service: InMemoryConversationService,
) -> None:
    created = client.post(
        "/v1/conversations",
        json={"title": "Demo Conversation", "agent_id": "chat_agent"},
    )
    conversation_id = created.json()["data"]["id"]

    response = client.delete(f"/v1/conversations/{conversation_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"] == {"id": conversation_id, "status": "deleted"}
