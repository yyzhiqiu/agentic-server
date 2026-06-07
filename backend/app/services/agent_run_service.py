"""Agent 运行记录业务编排服务。"""

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
from app.graph.default import DEFAULT_AGENT_ID
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
    def _agent_id(agent_run: AgentRun) -> str | None:
        """从一等字段或兼容负载中提取 Agent 标识。"""

        if isinstance(agent_run.agent_id, str) and agent_run.agent_id:
            return agent_run.agent_id

        metadata = dict(agent_run.metadata_ or {})
        output = dict(agent_run.output or {})
        candidates = [
            metadata.get("agent_id"),
            output.get("agent_id"),
        ]
        output_metadata = output.get("metadata")
        if isinstance(output_metadata, dict):
            candidates.append(output_metadata.get("agent_id"))

        for candidate in candidates:
            if isinstance(candidate, str) and candidate:
                return candidate
        return None

    @staticmethod
    def _resolve_agent_id(
        *,
        requested_agent_id: str | None = None,
        payload: dict[str, Any] | None = None,
        existing_run: AgentRun | None = None,
    ) -> str:
        """为运行记录写入可持久化的 Agent 标识。

        优先级：
        1. 显式请求参数中的 ``agent_id``
        2. 输入载荷根字段或 ``metadata`` 中的 ``agent_id``
        3. 已存在运行记录上的一等字段或兼容元数据
        4. 默认 ``chat_agent``
        """

        candidates: list[Any] = [requested_agent_id]
        payload_data = dict(payload or {})
        candidates.append(payload_data.get("agent_id"))
        payload_metadata = payload_data.get("metadata")
        if isinstance(payload_metadata, dict):
            candidates.append(payload_metadata.get("agent_id"))
        if existing_run is not None:
            candidates.append(AgentRunService._agent_id(existing_run))

        for candidate in candidates:
            if isinstance(candidate, str) and candidate:
                return candidate
        return DEFAULT_AGENT_ID

    @staticmethod
    def _to_status(agent_run: AgentRun) -> AgentStatus:
        """将 Agent 运行 ORM 实体映射为状态响应。"""

        return AgentStatus(
            status=agent_run.status,
            run_id=agent_run.id,
            agent_id=AgentRunService._agent_id(agent_run),
            metadata=dict(agent_run.metadata_ or {}),
        )

    @staticmethod
    def _to_list_item(agent_run: AgentRun) -> AgentRunListItem:
        """将 Agent 运行 ORM 实体映射为列表项响应。"""

        metadata = dict(agent_run.metadata_ or {})
        output = dict(agent_run.output or {})
        finished_at = AgentRunService._finished_at(agent_run)
        return AgentRunListItem(
            id=agent_run.id,
            conversation_id=agent_run.conversation_id,
            agent_id=AgentRunService._agent_id(agent_run),
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
        """在运行进入终态后返回最接近完成时刻的时间。"""

        if agent_run.status not in cls.TERMINAL_STATUSES:
            return None
        return agent_run.updated_at

    @staticmethod
    def _duration_ms(
        started_at: datetime | None,
        finished_at: datetime | None,
    ) -> int | None:
        """计算以毫秒为单位的持久化时长摘要。"""

        if started_at is None or finished_at is None:
            return None
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        return max(duration_ms, 0)

    @staticmethod
    def _error_message(status: str, output: dict[str, Any]) -> str | None:
        """仅在失败运行中返回失败消息。"""

        if status != "failed":
            return None
        error = output.get("error")
        return str(error) if isinstance(error, str) and error else None

    @staticmethod
    def _error_code(status: str, output: dict[str, Any]) -> str | None:
        """返回失败运行记录中的错误码。"""

        if status != "failed":
            return None
        code = output.get("code")
        return str(code) if isinstance(code, str) and code else None

    @staticmethod
    def _interruption_reason(status: str, metadata: dict[str, Any]) -> str | None:
        """仅在中断运行中返回中断原因。"""

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
        """将 Agent 运行 ORM 实体映射为详情响应。"""

        list_item = cls._to_list_item(agent_run)
        return AgentRunDetail(
            **list_item.model_dump(),
            input=dict(agent_run.input or {}),
            output=dict(agent_run.output or {}),
            metadata=dict(agent_run.metadata_ or {}),
            tool_calls=tool_calls or [],
        )

    async def status(self, run_id: str | None, user_id: str) -> AgentStatus:
        """返回 Agent 运行记录的当前控制状态。"""

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
        """列出当前用户拥有的 Agent 运行记录。"""

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
        """获取当前用户拥有的单条 Agent 运行记录。"""

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

    async def resume(
        self,
        run_id: str,
        payload: dict[str, Any],
        user_id: str,
        *,
        agent_id: str | None = None,
    ) -> AgentStatus:
        """为当前用户创建或更新一条运行中状态的 Agent 运行记录。"""

        if self.user_service is not None:
            await self.user_service.ensure_user(user_id, name=user_id)

        async with transaction(self.session):
            agent_run = await self.agent_run_repository.get_by_id_for_user(run_id, user_id)
            resolved_agent_id = self._resolve_agent_id(
                requested_agent_id=agent_id,
                payload=payload,
                existing_run=agent_run,
            )
            if agent_run is None:
                agent_run = AgentRun(
                    id=run_id,
                    agent_id=resolved_agent_id,
                    user_id=user_id,
                    status="running",
                    input=dict(payload),
                    output={},
                    metadata_=dict(payload),
                )
                agent_run = await self.agent_run_repository.add(agent_run)
            else:
                agent_run.agent_id = resolved_agent_id
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
                agent_id=self._agent_id(agent_run),
                resource_type="agent_run",
                resource_id=run_id,
                metadata={
                    "status": "running",
                    "input": dict(payload),
                },
            )
        )
        return self._to_status(agent_run)

    async def interrupt(
        self,
        run_id: str,
        reason: str | None,
        user_id: str,
        *,
        agent_id: str | None = None,
    ) -> AgentStatus:
        """为当前用户创建或更新一条已中断状态的 Agent 运行记录。"""

        metadata = {"reason": reason} if reason is not None else {}

        if self.user_service is not None:
            await self.user_service.ensure_user(user_id, name=user_id)

        async with transaction(self.session):
            agent_run = await self.agent_run_repository.get_by_id_for_user(run_id, user_id)
            resolved_agent_id = self._resolve_agent_id(
                requested_agent_id=agent_id,
                existing_run=agent_run,
            )
            if agent_run is None:
                agent_run = AgentRun(
                    id=run_id,
                    agent_id=resolved_agent_id,
                    user_id=user_id,
                    status="interrupted",
                    input={},
                    output={},
                    metadata_=metadata,
                )
                agent_run = await self.agent_run_repository.add(agent_run)
            else:
                agent_run.agent_id = resolved_agent_id
                agent_run.status = "interrupted"
                agent_run.metadata_ = metadata
                await self.session.flush()

        await self.audit_service.record(
            AuditEvent(
                action=AuditAction.AGENT_INTERRUPT,
                result=AuditResult.SUCCESS,
                actor_id=user_id,
                trace_id=get_trace_id(),
                agent_id=self._agent_id(agent_run),
                resource_type="agent_run",
                resource_id=run_id,
                metadata={
                    "status": "interrupted",
                    "reason": reason,
                },
            )
        )
        return self._to_status(agent_run)
