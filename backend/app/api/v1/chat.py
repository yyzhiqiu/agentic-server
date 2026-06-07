"""聊天相关 API 接口。

API 层负责接收聊天请求，并把同步与流式编排委托给 Service 层处理。
这里不直接实现图执行、持久化或 SSE 生命周期管理逻辑。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from app.api.dependencies import get_chat_service, get_current_user
from app.common.responses import success_response
from app.core.security import CurrentUser
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat(
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """为当前用户执行一次非流式聊天请求。

    该接口作为兼容入口保留，默认调用 ``chat_agent``。
    """

    response = await service.chat(payload, user)
    return success_response(response.model_dump())


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    """通过 SSE 为当前用户持续返回聊天事件。

    该接口作为兼容入口保留，默认调用 ``chat_agent``。
    """

    return StreamingResponse(
        service.stream_chat(payload, user),
        media_type="text/event-stream",
    )
