"""Agent 运行记录业务编排服务。

本服务负责协调 Agent 运行记录的轻量控制操作和用户范围读取能力，
控制写操作事务边界，记录尽力而为的审计事件，并让 API 层不直接感知
持久化细节。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.enums import AuditAction, AuditResult
from app.audit.schemas import AuditEvent
from app.audit.service import AuditService
from app.common.context import get_trace_id
from app.common.error_codes import ErrorCode
from app.common.exceptions import AppException
from app.db.models.agent_run import AgentRun
from app.db.repositories.agent_run_repo import AgentRunRepository
from app.db.transaction import transaction
from app.schemas.agent import AgentRunDetail, AgentRunList, AgentRunListItem, AgentStatus
from app.schemas.tool_call import ToolCallRead
from app.services.tool_call_service import ToolCallService
from app.services.user_service import UserService


class AgentRunService:
    """编排用户范围内的 Agent 运行控制与读取行为。"""

    TERMINAL_STATUSES = frozenset({"completed", "failed", "interrupted"})

    def __init__(
        self,
        *,
        session: AsyncSession,
        agent_run_repository: AgentRunRepository,
        user_service: UserService | None = None,
        tool_call_service: ToolCallService | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.session = session
        self.agent_run_repository = agent_run_repository
        self.user_service = user_service
        self.tool_call_service = tool_call_service
        self.audit_service = audit_service or AuditService()

    @staticmethod
    def _to_status(agent_run: AgentRun) -> AgentStatus:
        """将 Agent 运行 ORM 实体映射为 API 响应 Schema。"""

        return AgentStatus(
            status=agent_run.status,
            run_id=agent_run.id,
            metadata=dict(agent_run.metadata_ or {}),
        )

    @staticmethod
    def _to_list_item(agent_run: AgentRun) -> AgentRunListItem:
        """将 Agent 运行 ORM 实体映射为列表项 Schema。"""

        metadata = dict(agent_run.metadata_ or {})
        output = dict(agent_run.output or {})
        finished_at = AgentRunService._finished_at(agent_run)
        return AgentRunListItem(
            id=agent_run.id,
            conversation_id=agent_run.conversation_id,
            status=agent_run.status,
            started_at=agent_run.created_at,
            updated_at=agent_run.updated_at,
            finished_at=finished_at,
            duration_ms=AgentRunService._duration_ms(agent_run.created_at, finished_at),
            trace_id=metadata.get("trace_id"),
            error_message=AgentRunService._error_message(agent_run.status, output),
            error_code=AgentRunService._error_code(agent_run.status, output),
            interruption_reason=AgentRunService._interruption_reason(agent_run.status, metadata),
        )

    @classmethod
    def _finished_at(cls, agent_run: AgentRun) -> datetime | None:
        """在运行不再活跃时返回完成时间戳。

        当前持久化模型只保存运行记录的最新状态，因此当运行进入终态后，
        这里把 ``updated_at`` 视为最接近完成时间的可用标记。
        """

        if agent_run.status not in cls.TERMINAL_STATUSES:
            return None
        return agent_run.updated_at

    @staticmethod
    def _duration_ms(
        started_at: datetime | None,
        finished_at: datetime | None,
    ) -> int | None:
        """计算以毫秒为单位的持久化时长摘要。

        只有在终态时间可用时，API 才返回时长。
        对于仍在运行的记录，这个字段保持为空，避免客户端把静态快照误判为
        实时流逝计时器。
        """

        if started_at is None or finished_at is None:
            return None
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        return max(duration_ms, 0)

    @staticmethod
    def _error_message(status: str, output: dict[str, Any]) -> str | None:
        """仅在失败运行记录中返回失败消息。

        持久化层会根据图执行结果保存不同形态的输出结构。
        API 通过抽取统一失败消息字段来保持前端契约稳定。
        """

        if status != "failed":
            return None
        error = output.get("error")
        return str(error) if isinstance(error, str) and error else None

    @staticmethod
    def _error_code(status: str, output: dict[str, Any]) -> str | None:
        """返回失败运行记录中持久化的项目错误码。"""

        if status != "failed":
            return None
        code = output.get("code")
        return str(code) if isinstance(code, str) and code else None

    @staticmethod
    def _interruption_reason(status: str, metadata: dict[str, Any]) -> str | None:
        """仅在中断运行记录中返回中断原因。"""

        if status != "interrupted":
            return None
        reason = metadata.get("reason")
        return str(reason) if isinstance(reason, str) and reason else None

    @classmethod
    def _to_detail(
        cls,
        agent_run: AgentRun,
        *,
        tool_calls: list[ToolCallRead] | None = None,
    ) -> AgentRunDetail:
        """将 Agent 运行 ORM 实体映射为详情 Schema。"""

        list_item = cls._to_list_item(agent_run)
        return AgentRunDetail(
            **list_item.model_dump(),
            input=dict(agent_run.input or {}),
            output=dict(agent_run.output or {}),
            metadata=dict(agent_run.metadata_ or {}),
            tool_calls=tool_calls or [],
        )

    async def status(self, run_id: str | None, user_id: str) -> AgentStatus:
        """返回 Agent 运行记录的当前控制状态。

        当运行记录尚未持久化时，API 仍返回非报错的 idle 状态，
        让控制面板可以安全轮询。
        """

        if run_id is None:
            return AgentStatus(status="idle", run_id=None)

        agent_run = await self.agent_run_repository.get_by_id_for_user(run_id, user_id)
        if agent_run is None:
            return AgentStatus(status="idle", run_id=run_id)
        return self._to_status(agent_run)

    async def list(
        self,
        user_id: str,
        *,
        limit: int = 20,
        offset: int = 0,
        status: Literal["running", "interrupted", "completed", "failed", "created"] | None = None,
        conversation_id: str | None = None,
    ) -> AgentRunList:
        """列出当前用户拥有的 Agent 运行记录。

        参数：
            user_id: 当前调用方，对应需要返回的运行记录拥有者。
            limit: 最多返回的记录数。
            offset: 返回结果前需要跳过的记录数。
            status: 可选的运行状态过滤条件。
            conversation_id: 可选的会话范围过滤条件。
        """

        items = await self.agent_run_repository.list_by_user(
            user_id,
            limit=limit,
            offset=offset,
            status=status,
            conversation_id=conversation_id,
        )
        total = await self.agent_run_repository.count_by_user(
            user_id,
            status=status,
            conversation_id=conversation_id,
        )
        return AgentRunList(
            items=[self._to_list_item(item) for item in items],
            total=total,
        )

    async def get(self, run_id: str, user_id: str) -> AgentRunDetail:
        """获取当前用户拥有的单条 Agent 运行记录。

        异常：
            AppException: 当运行记录不存在，或不属于当前用户时抛出。
        """

        agent_run = await self.agent_run_repository.get_by_id_for_user(run_id, user_id)
        if agent_run is None:
            raise AppException(
                ErrorCode.NOT_FOUND,
                status_code=404,
                data={"run_id": run_id},
            )
        tool_calls: list[ToolCallRead] = []
        if self.tool_call_service is not None:
            tool_calls = await self.tool_call_service.list_for_run(run_id)
        return self._to_detail(agent_run, tool_calls=tool_calls)

    async def resume(self, run_id: str, payload: dict[str, Any], user_id: str) -> AgentStatus:
        """为当前用户创建或更新一条运行中状态的 Agent 运行记录。

        副作用：
            会持久化最新控制负载，并在运行状态写入成功后尽力记录审计事件。
        """

        if self.user_service is not None:
            await self.user_service.ensure_user(user_id, name=user_id)

        async with transaction(self.session):
            agent_run = await self.agent_run_repository.get_by_id_for_user(run_id, user_id)
            if agent_run is None:
                agent_run = AgentRun(
                    id=run_id,
                    user_id=user_id,
                    status="running",
                    input=dict(payload),
                    output={},
                    metadata_=dict(payload),
                )
                agent_run = await self.agent_run_repository.add(agent_run)
            else:
                agent_run.status = "running"
                agent_run.input = dict(payload)
                agent_run.metadata_ = dict(payload)
                await self.session.flush()

        await self.audit_service.record(
            AuditEvent(
                action=AuditAction.AGENT_RESUME,
                result=AuditResult.SUCCESS,
                actor_id=user_id,
                trace_id=get_trace_id(),
                resource_type="agent_run",
                resource_id=run_id,
                metadata={
                    "status": "running",
                    "input": dict(payload),
                },
            )
        )
        return self._to_status(agent_run)

    async def interrupt(self, run_id: str, reason: str | None, user_id: str) -> AgentStatus:
        """为当前用户创建或更新一条已中断状态的 Agent 运行记录。

        副作用：
            会持久化中断原因，并在运行状态写入成功后尽力记录审计事件。
        """

        metadata = {"reason": reason} if reason is not None else {}

        if self.user_service is not None:
            await self.user_service.ensure_user(user_id, name=user_id)

        async with transaction(self.session):
            agent_run = await self.agent_run_repository.get_by_id_for_user(run_id, user_id)
            if agent_run is None:
                agent_run = AgentRun(
                    id=run_id,
                    user_id=user_id,
                    status="interrupted",
                    input={},
                    output={},
                    metadata_=metadata,
                )
                agent_run = await self.agent_run_repository.add(agent_run)
            else:
                agent_run.status = "interrupted"
                agent_run.metadata_ = metadata
                await self.session.flush()

        await self.audit_service.record(
            AuditEvent(
                action=AuditAction.AGENT_INTERRUPT,
                result=AuditResult.SUCCESS,
                actor_id=user_id,
                trace_id=get_trace_id(),
                resource_type="agent_run",
                resource_id=run_id,
                metadata={
                    "status": "interrupted",
                    "reason": reason,
                },
            )
        )
        return self._to_status(agent_run)
