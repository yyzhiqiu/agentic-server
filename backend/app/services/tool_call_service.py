"""工具调用编排辅助服务。"""

from __future__ import annotations

import json

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

    @staticmethod
    def _identity(payload: ToolCallPayload) -> str:
        """构建同一次运行内可稳定比较的工具调用标识。

        优先使用模型协议提供的 ``tool_call_id``。旧数据缺少该字段时，使用工具名、
        输入和输出生成结构化签名，避免中断恢复后把同一调用重复写入。
        """

        tool_call_id = payload.metadata.get("tool_call_id")
        if isinstance(tool_call_id, str) and tool_call_id:
            return f"id:{tool_call_id}"
        return json.dumps(
            {
                "tool_name": payload.tool_name,
                "input": payload.input,
                "output": payload.output,
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )

    async def record_for_run(
        self,
        agent_run_id: str,
        tool_calls: list[ToolCallPayload],
        *,
        agent_id: str | None = None,
    ) -> list[ToolCallRead]:
        """幂等持久化单次 Agent 运行过程中产生的工具调用。

        中断运行恢复后，Graph 响应可能再次携带中断前已经记录的工具调用。本方法
        会在同一 ``agent_run_id`` 内按协议 ID 或结构化内容去重，不主动提交事务。
        """

        existing = await self.tool_call_repository.list_by_agent_run(agent_run_id)
        identities = {
            self._identity(
                ToolCallPayload(
                    tool_name=item.tool_name,
                    status=item.status,
                    input=dict(item.input or {}),
                    output=dict(item.output or {}),
                    metadata=dict(item.metadata_ or {}),
                )
            )
            for item in existing
        }
        persisted: list[ToolCallRead] = []
        for payload in tool_calls:
            identity = self._identity(payload)
            if identity in identities:
                continue
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
            identities.add(identity)
        return persisted

    async def list_for_run(self, agent_run_id: str) -> list[ToolCallRead]:
        """返回单个 Agent 运行记录下的已持久化工具调用。"""

        items = await self.tool_call_repository.list_by_agent_run(agent_run_id)
        return [self._to_read(item) for item in items]

    async def list_for_runs(
        self,
        agent_run_ids: list[str],
    ) -> dict[str, list[ToolCallRead]]:
        """批量返回多条运行记录关联的工具调用，并按运行 ID 分组。"""

        grouped = {run_id: [] for run_id in agent_run_ids}
        items = await self.tool_call_repository.list_by_agent_runs(agent_run_ids)
        for item in items:
            if item.agent_run_id is None:
                continue
            grouped.setdefault(item.agent_run_id, []).append(self._to_read(item))
        return grouped
