"""工具调用编排辅助服务。

本服务负责把结构化工具调用负载转换为可持久化数据行，
并将数据库实体重新映射为面向 API 的 Schema。事务边界仍由调用方控制，
这样工具调用写入就能参与更大的聊天生命周期事务。
"""

from __future__ import annotations

from app.db.models.tool_call import ToolCall
from app.db.repositories.tool_call_repo import ToolCallRepository
from app.schemas.tool_call import ToolCallPayload, ToolCallRead


class ToolCallService:
    """持久化并读取与 Agent 运行记录关联的工具调用。"""

    def __init__(self, *, tool_call_repository: ToolCallRepository) -> None:
        self.tool_call_repository = tool_call_repository

    @staticmethod
    def _to_read(tool_call: ToolCall) -> ToolCallRead:
        """将已持久化工具调用实体映射为读取 Schema。"""

        return ToolCallRead(
            id=tool_call.id,
            agent_run_id=tool_call.agent_run_id,
            tool_name=tool_call.tool_name,
            status=tool_call.status,
            input=dict(tool_call.input or {}),
            output=dict(tool_call.output or {}),
            metadata=dict(tool_call.metadata_ or {}),
            created_at=tool_call.created_at,
            updated_at=tool_call.updated_at,
        )

    async def record_for_run(
        self,
        agent_run_id: str,
        tool_calls: list[ToolCallPayload],
    ) -> list[ToolCallRead]:
        """持久化单次 Agent 运行过程中产生的工具调用。

        参数：
            agent_run_id: 持久化 Agent 运行记录的拥有者标识。
            tool_calls: 图执行过程中产出的结构化工具调用负载。

        返回：
            已持久化并映射为读取 Schema 的工具调用列表。

        副作用：
            会通过 Repository 刷入新的工具调用记录。外围事务边界由调用方负责。
        """

        persisted: list[ToolCallRead] = []
        for payload in tool_calls:
            created = await self.tool_call_repository.add(
                ToolCall(
                    agent_run_id=agent_run_id,
                    tool_name=payload.tool_name,
                    status=payload.status,
                    input=dict(payload.input),
                    output=dict(payload.output),
                    metadata_=dict(payload.metadata),
                )
            )
            persisted.append(self._to_read(created))
        return persisted

    async def list_for_run(self, agent_run_id: str) -> list[ToolCallRead]:
        """返回单个 Agent 运行记录下的已持久化工具调用。"""

        items = await self.tool_call_repository.list_by_agent_run(agent_run_id)
        return [self._to_read(item) for item in items]
