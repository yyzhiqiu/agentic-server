"""会话相关接口。

本模块提供会话创建、查询、删除以及会话消息读取能力。
API 层只负责 HTTP 输入输出适配，具体业务编排交由 Service 层完成。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_conversation_service,
    get_current_user,
    get_message_service,
)
from app.common.responses import success_response
from app.core.security import CurrentUser
from app.schemas.conversation import ConversationCreate
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("")
async def create_conversation(
    payload: ConversationCreate,
    service: ConversationService = Depends(get_conversation_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """创建一个由当前用户拥有的新会话。"""

    data = await service.create(payload, user.id)
    return success_response(data.model_dump())


@router.get("")
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    service: ConversationService = Depends(get_conversation_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """列出当前用户可见的会话。"""

    data = await service.list(user.id, limit=limit, offset=offset)
    return success_response(data.model_dump())


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """获取当前用户可见的单个会话。"""

    data = await service.get(conversation_id, user.id)
    return success_response(data.model_dump())


@router.get("/{conversation_id}/messages")
async def list_conversation_messages(
    conversation_id: str,
    limit: int = 50,
    offset: int = 0,
    service: MessageService = Depends(get_message_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """列出当前用户可见会话下已持久化的消息。"""

    data = await service.list_by_conversation(
        conversation_id,
        user.id,
        limit=limit,
        offset=offset,
    )
    return success_response(data.model_dump())


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """软删除当前用户拥有的会话。"""

    return success_response(await service.delete(conversation_id, user.id))
