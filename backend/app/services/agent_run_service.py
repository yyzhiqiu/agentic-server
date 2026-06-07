"""Agent 运行记录业务编排服务。"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.enums import AuditAction, AuditResult
from app.audit.schemas import AuditEvent
from app.audit.service import AuditService
from app.audit.writer import DatabaseAuditWriter
from app.common.context import get_trace_id
from app.common.error_codes import ErrorCode
from app.common.exceptions import AppException
from app.core.config import settings
from app.core.security import CurrentUser
from app.db.models.agent_run import AgentRun
from app.db.repositories.agent_run_repo import AgentRunRepository
from app.db.repositories.conversation_repo import ConversationRepository
from app.db.repositories.message_repo import MessageRepository
from app.db.repositories.tool_call_repo import ToolCallRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import AsyncSessionLocal
from app.db.transaction import transaction
from app.graph.default import DEFAULT_AGENT_ID
from app.graph.types import AgentRegistry
from app.schemas.agent import AgentRunDetail, AgentRunList, AgentRunListItem, AgentStatus
from app.schemas.tool_call import ToolCallRead
from app.services.agent_runtime_registry import AgentRuntimeRegistry
from app.services.chat_service import ChatService
from app.services.graph_runner import GraphRunner
from app.services.tool_call_service import ToolCallService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class AgentRunService:
    """编排用户范围内的 Agent 运行控制与读取行为。"""

    TERMINAL_STATUSES = frozenset({"completed", "failed", "interrupted", "cancelled"})
    RESUMABLE_STATUSES = frozenset({"interrupted"})

    def __init__(
        self,
        *,
        session: AsyncSession,
        agent_run_repository: AgentRunRepository,
        user_service: UserService | None = None,
        agent_registry: AgentRegistry | None = None,
        runtime_registry: AgentRuntimeRegistry | None = None,
        tool_call_service: ToolCallService | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.session = session
        self.agent_run_repository = agent_run_repository
        self.user_service = user_service
        self.agent_registry = agent_registry
        self.runtime_registry = runtime_registry
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
        """为运行记录解析稳定的 Agent 标识。"""

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
        """把 Agent 运行 ORM 实体映射为状态响应。"""

        return AgentStatus(
            status=agent_run.status,
            run_id=agent_run.id,
            agent_id=AgentRunService._agent_id(agent_run),
            metadata=dict(agent_run.metadata_ or {}),
        )

    @staticmethod
    def _to_list_item(agent_run: AgentRun) -> AgentRunListItem:
        """把 Agent 运行 ORM 实体映射为列表项响应。"""

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
        """返回中断或取消运行的控制原因。

        这里复用历史字段名 ``interruption_reason``，是为了兼容前端与既有响应结构。
        """

        if status not in {"interrupted", "cancelled"}:
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
        """把 Agent 运行 ORM 实体映射为详情响应。"""

        list_item = cls._to_list_item(agent_run)
        return AgentRunDetail(
            **list_item.model_dump(),
            input=dict(agent_run.input or {}),
            output=dict(agent_run.output or {}),
            metadata=dict(agent_run.metadata_ or {}),
            tool_calls=tool_calls or [],
        )

    @staticmethod
    def _build_control_output(
        status: str,
        *,
        reason: str | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        """构造暂停或取消时的运行输出摘要。"""

        output: dict[str, Any] = {"status": status}
        if reason is not None:
            output["reason"] = reason
        if agent_id is not None:
            output["agent_id"] = agent_id
        return output

    @staticmethod
    def _synthetic_status(
        *,
        status: str,
        run_id: str,
        agent_id: str | None,
        reason: str | None = None,
        pending: bool = False,
    ) -> AgentStatus:
        """在后台任务尚未完全落库时返回一个面向控制接口的临时状态。"""

        metadata: dict[str, Any] = {}
        if reason is not None:
            metadata["reason"] = reason
        if pending:
            metadata["pending"] = True
        return AgentStatus(
            status=status,
            run_id=run_id,
            agent_id=agent_id,
            metadata=metadata,
        )

    @staticmethod
    def _background_user(user_id: str) -> CurrentUser:
        """为后台恢复任务构造最小用户身份。"""

        return CurrentUser(id=user_id, name=user_id)

    async def _refresh_session_view(self) -> None:
        """尽量让当前会话在下一次查询时看到其他任务刚提交的最新状态。"""

        expire_all = getattr(self.session, "expire_all", None)
        if callable(expire_all):
            expire_all()

    def _require_runtime_registry(self) -> AgentRuntimeRegistry:
        """确保运行控制依赖已通过应用级依赖注入提供。"""

        if self.runtime_registry is None:
            raise AppException(
                ErrorCode.SERVICE_UNAVAILABLE,
                message="当前环境未启用运行时任务注册表。",
                status_code=503,
            )
        return self.runtime_registry

    def _get_agent_graph_runner(self, agent_id: str) -> GraphRunner:
        """根据 Agent 标识获取用于后台恢复的 GraphRunner。"""

        if self.agent_registry is None:
            raise AppException(
                ErrorCode.SERVICE_UNAVAILABLE,
                message="当前环境未加载 Agent 注册表。",
                status_code=503,
            )

        agent_definition = self.agent_registry.get(agent_id)
        if agent_definition is None:
            raise AppException(
                ErrorCode.NOT_FOUND,
                status_code=404,
                data={"agent_id": agent_id},
            )

        return GraphRunner(
            agent_definition.graph,
            agent_id=agent_definition.metadata.agent_id,
        )

    async def _persist_control_state(
        self,
        session: AsyncSession,
        *,
        run_id: str,
        user_id: str,
        agent_id: str,
        status: str,
        reason: str | None,
    ) -> None:
        """在任意会话中持久化暂停或取消后的最终状态。"""

        repository = AgentRunRepository(session)
        agent_run = await repository.get_by_id_for_user(run_id, user_id)
        if agent_run is None:
            return

        async with transaction(session):
            metadata = dict(agent_run.metadata_ or {})
            metadata["agent_id"] = agent_id
            metadata["resume_available"] = status == "interrupted"
            if reason is None:
                metadata.pop("reason", None)
            else:
                metadata["reason"] = reason

            agent_run.agent_id = agent_id
            agent_run.status = status
            agent_run.metadata_ = metadata
            if status == "cancelled":
                agent_run.output = self._build_control_output(
                    "cancelled",
                    reason=reason,
                    agent_id=agent_id,
                )
            else:
                agent_run.output = {}
            await session.flush()

    async def _persist_background_failure(
        self,
        session: AsyncSession,
        *,
        run_id: str,
        user_id: str,
        agent_id: str,
        exc: Exception,
    ) -> None:
        """在后台恢复任务自身失败时，把运行记录标记为失败。"""

        repository = AgentRunRepository(session)
        agent_run = await repository.get_by_id_for_user(run_id, user_id)
        if agent_run is None:
            return

        async with transaction(session):
            metadata = dict(agent_run.metadata_ or {})
            metadata["agent_id"] = agent_id
            metadata["resume_available"] = False
            metadata.pop("reason", None)

            output: dict[str, Any] = {
                "error": str(exc),
                "type": exc.__class__.__name__,
                "agent_id": agent_id,
            }
            if isinstance(exc, AppException):
                output["code"] = exc.code.value
                output["details"] = exc.data

            agent_run.agent_id = agent_id
            agent_run.status = "failed"
            agent_run.metadata_ = metadata
            agent_run.output = output
            await session.flush()

    def _build_background_chat_service(
        self,
        session: AsyncSession,
        *,
        agent_id: str,
    ) -> ChatService:
        """为后台恢复任务构建独立的 ChatService。"""

        return ChatService(
            session=session,
            graph_runner=self._get_agent_graph_runner(agent_id),
            conversation_repository=ConversationRepository(session),
            message_repository=MessageRepository(session),
            agent_run_repository=AgentRunRepository(session),
            user_service=UserService(
                session=session,
                user_repository=UserRepository(session),
            ),
            agent_id=agent_id,
            runtime_registry=self.runtime_registry,
            tool_call_service=ToolCallService(
                tool_call_repository=ToolCallRepository(session),
            ),
            audit_service=AuditService(
                writer=DatabaseAuditWriter(session),
            ),
        )

    async def _resume_in_background(
        self,
        *,
        run_id: str,
        user_id: str,
        agent_id: str,
    ) -> None:
        """在后台独立恢复一条已中断运行。"""

        try:
            async with AsyncSessionLocal() as session:
                chat_service = self._build_background_chat_service(
                    session,
                    agent_id=agent_id,
                )
                await chat_service.resume_run(
                    run_id,
                    self._background_user(user_id),
                )
        except asyncio.CancelledError:
            action = "interrupt"
            reason = "运行任务已中断，可稍后恢复"
            if self.runtime_registry is not None:
                control_request = await self.runtime_registry.get_control_request(run_id)
                if control_request is not None:
                    action = control_request.action
                    reason = control_request.reason or reason

            async with AsyncSessionLocal() as session:
                await self._persist_control_state(
                    session,
                    run_id=run_id,
                    user_id=user_id,
                    agent_id=agent_id,
                    status="cancelled" if action == "cancel" else "interrupted",
                    reason=reason,
                )
            raise
        except Exception as exc:
            logger.warning("后台恢复 Agent 运行失败", exc_info=True)
            async with AsyncSessionLocal() as session:
                await self._persist_background_failure(
                    session,
                    run_id=run_id,
                    user_id=user_id,
                    agent_id=agent_id,
                    exc=exc,
                )
        finally:
            if self.runtime_registry is not None:
                task = asyncio.current_task()
                if task is not None:
                    await self.runtime_registry.unregister(run_id, task)

    async def _schedule_resume(
        self,
        *,
        run_id: str,
        user_id: str,
        agent_id: str,
    ) -> None:
        """创建后台恢复任务，并尽量缩小 resume 后立即被控制时的竞态窗口。"""

        task = asyncio.create_task(
            self._resume_in_background(
                run_id=run_id,
                user_id=user_id,
                agent_id=agent_id,
            ),
            name=f"agent-resume-{run_id}",
        )

        if self.runtime_registry is not None:
            await self.runtime_registry.register(run_id, task)

    async def _record_audit(
        self,
        *,
        action: AuditAction,
        user_id: str,
        run_id: str,
        agent_id: str | None,
        metadata: dict[str, Any],
    ) -> None:
        """统一记录运行控制审计事件。"""

        await self.audit_service.record(
            AuditEvent(
                action=action,
                result=AuditResult.SUCCESS,
                actor_id=user_id,
                trace_id=get_trace_id(),
                agent_id=agent_id,
                resource_type="agent_run",
                resource_id=run_id,
                metadata=metadata,
            )
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
        status: Literal[
            "running",
            "interrupted",
            "cancelled",
            "completed",
            "failed",
            "created",
        ]
        | None = None,
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
        """从已中断运行恢复执行。

        Why:
            真实恢复必须建立在已有运行记录、已有 checkpoint 与同一个 ``thread_id`` 之上，
            因此这里不再承担“无中生有创建一条 running 记录”的职责，新的运行仍应由
            聊天入口创建。
        """

        if not settings.AGENT_CHECKPOINT_ENABLED:
            raise AppException(
                ErrorCode.SERVICE_UNAVAILABLE,
                message="当前环境未启用 Agent checkpoint，无法恢复运行。",
                status_code=503,
            )

        runtime_registry = self._require_runtime_registry()

        if self.user_service is not None:
            await self.user_service.ensure_user(user_id, name=user_id)

        agent_run = await self.agent_run_repository.get_by_id_for_user(run_id, user_id)
        if agent_run is None:
            raise AppException(
                ErrorCode.NOT_FOUND,
                status_code=404,
                data={"run_id": run_id},
            )

        if await runtime_registry.has_active_task(run_id):
            raise AppException(
                ErrorCode.REQUEST_VALIDATION_ERROR,
                message="当前运行仍在执行，无需恢复。",
                status_code=409,
                data={"run_id": run_id},
            )

        if agent_run.status not in self.RESUMABLE_STATUSES:
            raise AppException(
                ErrorCode.REQUEST_VALIDATION_ERROR,
                message="只有已中断的运行才允许恢复。",
                status_code=409,
                data={
                    "run_id": run_id,
                    "status": agent_run.status,
                },
            )

        if not dict(agent_run.input or {}):
            raise AppException(
                ErrorCode.REQUEST_VALIDATION_ERROR,
                message="当前运行缺少原始输入，无法恢复。",
                status_code=409,
                data={"run_id": run_id},
            )

        resolved_agent_id = self._resolve_agent_id(
            requested_agent_id=agent_id,
            payload=payload,
            existing_run=agent_run,
        )
        self._get_agent_graph_runner(resolved_agent_id)

        async with transaction(self.session):
            metadata = dict(agent_run.metadata_ or {})
            metadata["agent_id"] = resolved_agent_id
            metadata["resume_available"] = False
            metadata.pop("reason", None)
            if payload:
                metadata["resume_payload"] = dict(payload)
            else:
                metadata.pop("resume_payload", None)

            agent_run.agent_id = resolved_agent_id
            agent_run.status = "running"
            agent_run.output = {}
            agent_run.metadata_ = metadata
            await self.session.flush()

        await self._schedule_resume(
            run_id=run_id,
            user_id=user_id,
            agent_id=resolved_agent_id,
        )

        await self._record_audit(
            action=AuditAction.AGENT_RESUME,
            user_id=user_id,
            run_id=run_id,
            agent_id=self._agent_id(agent_run),
            metadata={
                "status": "running",
                "resume_payload": dict(payload),
            },
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
        """把运行标记为可恢复中断，并尽量真正停止其后台任务。"""

        runtime_registry = self._require_runtime_registry()

        if self.user_service is not None:
            await self.user_service.ensure_user(user_id, name=user_id)

        agent_run = await self.agent_run_repository.get_by_id_for_user(run_id, user_id)
        if agent_run is None:
            raise AppException(
                ErrorCode.NOT_FOUND,
                status_code=404,
                data={"run_id": run_id},
            )

        resolved_agent_id = self._resolve_agent_id(
            requested_agent_id=agent_id,
            existing_run=agent_run,
        )

        if agent_run.status in {"completed", "failed", "cancelled"}:
            raise AppException(
                ErrorCode.REQUEST_VALIDATION_ERROR,
                message="当前运行已进入不可中断状态。",
                status_code=409,
                data={
                    "run_id": run_id,
                    "status": agent_run.status,
                },
            )

        if await runtime_registry.has_active_task(run_id):
            await runtime_registry.request_interrupt(run_id, reason)
            settled = await runtime_registry.wait_for_task(run_id, timeout=10.0)
            await self._refresh_session_view()
            reloaded = await self.agent_run_repository.get_by_id_for_user(run_id, user_id)
            if reloaded is not None and reloaded.status == "interrupted":
                await self._record_audit(
                    action=AuditAction.AGENT_INTERRUPT,
                    user_id=user_id,
                    run_id=run_id,
                    agent_id=self._agent_id(reloaded),
                    metadata={
                        "status": "interrupted",
                        "reason": reason,
                    },
                )
                return self._to_status(reloaded)

            synthetic = self._synthetic_status(
                status="interrupted",
                run_id=run_id,
                agent_id=resolved_agent_id,
                reason=reason,
                pending=not settled,
            )
            await self._record_audit(
                action=AuditAction.AGENT_INTERRUPT,
                user_id=user_id,
                run_id=run_id,
                agent_id=resolved_agent_id,
                metadata={
                    "status": "interrupted",
                    "reason": reason,
                    "pending": not settled,
                },
            )
            return synthetic

        async with transaction(self.session):
            metadata = dict(agent_run.metadata_ or {})
            metadata["agent_id"] = resolved_agent_id
            metadata["resume_available"] = True
            if reason is None:
                metadata.pop("reason", None)
            else:
                metadata["reason"] = reason

            agent_run.agent_id = resolved_agent_id
            agent_run.status = "interrupted"
            agent_run.metadata_ = metadata
            agent_run.output = {}
            await self.session.flush()

        await self._record_audit(
            action=AuditAction.AGENT_INTERRUPT,
            user_id=user_id,
            run_id=run_id,
            agent_id=self._agent_id(agent_run),
            metadata={
                "status": "interrupted",
                "reason": reason,
            },
        )
        return self._to_status(agent_run)

    async def cancel(
        self,
        run_id: str,
        reason: str | None,
        user_id: str,
        *,
        agent_id: str | None = None,
    ) -> AgentStatus:
        """彻底取消一条运行，并阻止后续恢复。"""

        runtime_registry = self._require_runtime_registry()

        if self.user_service is not None:
            await self.user_service.ensure_user(user_id, name=user_id)

        agent_run = await self.agent_run_repository.get_by_id_for_user(run_id, user_id)
        if agent_run is None:
            raise AppException(
                ErrorCode.NOT_FOUND,
                status_code=404,
                data={"run_id": run_id},
            )

        resolved_agent_id = self._resolve_agent_id(
            requested_agent_id=agent_id,
            existing_run=agent_run,
        )

        if agent_run.status == "cancelled":
            return self._to_status(agent_run)

        if agent_run.status in {"completed", "failed"}:
            raise AppException(
                ErrorCode.REQUEST_VALIDATION_ERROR,
                message="当前运行已进入不可取消状态。",
                status_code=409,
                data={
                    "run_id": run_id,
                    "status": agent_run.status,
                },
            )

        if await runtime_registry.has_active_task(run_id):
            await runtime_registry.request_cancel(run_id, reason)
            settled = await runtime_registry.wait_for_task(run_id, timeout=10.0)
            await self._refresh_session_view()
            reloaded = await self.agent_run_repository.get_by_id_for_user(run_id, user_id)
            if reloaded is not None and reloaded.status == "cancelled":
                await self._record_audit(
                    action=AuditAction.AGENT_CANCEL,
                    user_id=user_id,
                    run_id=run_id,
                    agent_id=self._agent_id(reloaded),
                    metadata={
                        "status": "cancelled",
                        "reason": reason,
                    },
                )
                return self._to_status(reloaded)

            synthetic = self._synthetic_status(
                status="cancelled",
                run_id=run_id,
                agent_id=resolved_agent_id,
                reason=reason,
                pending=not settled,
            )
            await self._record_audit(
                action=AuditAction.AGENT_CANCEL,
                user_id=user_id,
                run_id=run_id,
                agent_id=resolved_agent_id,
                metadata={
                    "status": "cancelled",
                    "reason": reason,
                    "pending": not settled,
                },
            )
            return synthetic

        async with transaction(self.session):
            metadata = dict(agent_run.metadata_ or {})
            metadata["agent_id"] = resolved_agent_id
            metadata["resume_available"] = False
            if reason is None:
                metadata.pop("reason", None)
            else:
                metadata["reason"] = reason

            agent_run.agent_id = resolved_agent_id
            agent_run.status = "cancelled"
            agent_run.metadata_ = metadata
            agent_run.output = self._build_control_output(
                "cancelled",
                reason=reason,
                agent_id=resolved_agent_id,
            )
            await self.session.flush()

        await self._record_audit(
            action=AuditAction.AGENT_CANCEL,
            user_id=user_id,
            run_id=run_id,
            agent_id=self._agent_id(agent_run),
            metadata={
                "status": "cancelled",
                "reason": reason,
            },
        )
        return self._to_status(agent_run)
