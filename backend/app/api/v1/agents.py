"""统一 Agent 能力查询与调用接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from app.api.dependencies import get_agent_service, get_chat_service, get_current_user
from app.common.responses import success_response
from app.core.security import CurrentUser
from app.schemas.agent import AgentChatRequest, AgentListResponse
from app.services.agent_service import AgentService
from app.services.chat_service import ChatService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
async def list_agents(
    service: AgentService = Depends(get_agent_service),
) -> dict:
    """返回当前服务可用的全部 Agent 元信息。"""

    data = AgentListResponse(root=service.list_metadata())
    return success_response(data.model_dump())


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    service: AgentService = Depends(get_agent_service),
) -> dict:
    """返回指定 Agent 的元信息。"""

    data = service.get_metadata(agent_id)
    return success_response(data.model_dump())


@router.post("/{agent_id}/chat")
async def agent_chat(
    agent_id: str,
    payload: AgentChatRequest,
    service: ChatService = Depends(get_chat_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """使用指定 Agent 执行一次非流式聊天。"""

    _ = agent_id
    response = await service.chat(payload, user)
    return success_response(response.model_dump())


@router.post("/{agent_id}/chat/stream")
async def agent_chat_stream(
    agent_id: str,
    payload: AgentChatRequest,
    service: ChatService = Depends(get_chat_service),
    user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    """使用指定 Agent 通过 SSE 返回流式聊天事件。"""

    _ = agent_id
    return StreamingResponse(
        service.stream_chat(payload, user),
        media_type="text/event-stream",
    )
