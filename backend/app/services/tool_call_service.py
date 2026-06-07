"""工具调用编排辅助服务。"""

from __future__ import annotations

from app.db.models.tool_call import ToolCall
from app.db.repositories.tool_call_repo import ToolCallRepository
from app.schemas.tool_call import ToolCallPayload, ToolCallRead


class ToolCallService:
    """持久化并读取单个 Agent 运行记录关联的工具调用。"""

    def __init__(self, *, tool_call_repository: ToolCallRepository) -> None:
        self.tool_call_repository = tool_call_repository

    @staticmethod
    def _to_read(tool_call: ToolCall) -> ToolCallRead:
        """将已持久化工具调用实体映射为读取 Schema。"""

        metadata = dict(tool_call.metadata_ or {})
        agent_id = metadata.get("agent_id")
        return ToolCallRead(
            id=tool_call.id,
            agent_run_id=tool_call.agent_run_id,
            agent_id=agent_id if isinstance(agent_id, str) and agent_id else None,
            tool_name=tool_call.tool_name,
            status=tool_call.status,
            input=dict(tool_call.input or {}),
            output=dict(tool_call.output or {}),
            metadata=metadata,
            created_at=tool_call.created_at,
            updated_at=tool_call.updated_at,
        )

    async def record_for_run(
        self,
        agent_run_id: str,
        tool_calls: list[ToolCallPayload],
        *,
        agent_id: str | None = None,
    ) -> list[ToolCallRead]:
        """持久化单次 Agent 运行过程中产生的工具调用。"""

        persisted: list[ToolCallRead] = []
        for payload in tool_calls:
            metadata = dict(payload.metadata)
            if agent_id is not None:
                metadata.setdefault("agent_id", agent_id)
            created = await self.tool_call_repository.add(
                ToolCall(
                    agent_run_id=agent_run_id,
                    tool_name=payload.tool_name,
                    status=payload.status,
                    input=dict(payload.input),
                    output=dict(payload.output),
                    metadata_=metadata,
                )
            )
            persisted.append(self._to_read(created))
        return persisted

    async def list_for_run(self, agent_run_id: str) -> list[ToolCallRead]:
        """返回单个 Agent 运行记录下的已持久化工具调用。"""

        items = await self.tool_call_repository.list_by_agent_run(agent_run_id)
        return [self._to_read(item) for item in items]
