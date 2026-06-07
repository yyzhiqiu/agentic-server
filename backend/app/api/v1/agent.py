"""Agent 控制与运行记录查询接口。

API 层对外暴露轻量控制操作和用户范围内的运行记录查询，
具体持久化和业务编排仍由 Service 层负责。
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends

from app.api.dependencies import get_agent_run_service, get_current_user
from app.common.responses import success_response
from app.core.security import CurrentUser
from app.schemas.agent import AgentInterruptRequest, AgentResumeRequest
from app.services.agent_run_service import AgentRunService

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/runs")
async def list_agent_runs(
    limit: int = 20,
    offset: int = 0,
    status: Literal["running", "interrupted", "completed", "failed", "created"] | None = None,
    conversation_id: str | None = None,
    service: AgentRunService = Depends(get_agent_run_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """列出当前用户可见的 Agent 运行记录。"""

    data = await service.list(
        user.id,
        limit=limit,
        offset=offset,
        status=status,
        conversation_id=conversation_id,
    )
    return success_response(data.model_dump())


@router.get("/runs/{run_id}")
async def get_agent_run(
    run_id: str,
    service: AgentRunService = Depends(get_agent_run_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """获取当前用户可见的单条 Agent 运行记录。"""

    data = await service.get(run_id, user.id)
    return success_response(data.model_dump())


@router.get("/status")
async def agent_status(
    run_id: str | None = None,
    service: AgentRunService = Depends(get_agent_run_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """返回当前用户可见 Agent 运行记录的控制状态。"""

    data = await service.status(run_id, user.id)
    return success_response(data.model_dump())


@router.post("/resume")
async def resume_agent(
    payload: AgentResumeRequest,
    service: AgentRunService = Depends(get_agent_run_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """将当前用户的 Agent 运行记录标记为恢复执行。"""

    data = await service.resume(payload.run_id, payload.input, user.id)
    return success_response(data.model_dump())


@router.post("/interrupt")
async def interrupt_agent(
    payload: AgentInterruptRequest,
    service: AgentRunService = Depends(get_agent_run_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """将当前用户的 Agent 运行记录标记为已中断。"""

    data = await service.interrupt(payload.run_id, payload.reason, user.id)
    return success_response(data.model_dump())
