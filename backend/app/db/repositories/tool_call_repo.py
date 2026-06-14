"""工具调用数据访问逻辑。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tool_call import ToolCall
from app.db.repositories.base import BaseRepository


class ToolCallRepository(BaseRepository[ToolCall]):
    """处理单个 Agent 运行记录下工具调用的 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ToolCall)

    async def list_by_agent_run(self, agent_run_id: str) -> list[ToolCall]:
        """列出单个 Agent 运行记录下保存的工具调用。"""

        result = await self.session.execute(
            select(ToolCall)
            .where(ToolCall.agent_run_id == agent_run_id)
            .order_by(ToolCall.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_by_agent_runs(self, agent_run_ids: list[str]) -> list[ToolCall]:
        """批量列出多条 Agent 运行记录下保存的工具调用。

        本方法按创建时间正序返回结果，不负责事务提交。空 ID 列表不会访问数据库。
        """

        if not agent_run_ids:
            return []

        result = await self.session.execute(
            select(ToolCall)
            .where(ToolCall.agent_run_id.in_(agent_run_ids))
            .order_by(ToolCall.created_at.asc())
        )
        return list(result.scalars().all())
