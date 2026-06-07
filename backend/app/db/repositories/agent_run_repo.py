"""Agent 运行记录的数据访问辅助逻辑。

本 Repository 只负责 Agent 运行记录的查询拼装和持久化基础能力，
不负责事务提交，必须由 Service 层统一编排。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_run import AgentRun
from app.db.repositories.base import BaseRepository


class AgentRunRepository(BaseRepository[AgentRun]):
    """面向用户范围 Agent 运行记录查询的 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AgentRun)

    async def list_by_user(
        self,
        user_id: str,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        conversation_id: str | None = None,
    ) -> list[AgentRun]:
        """列出指定用户拥有的 Agent 运行记录。

        参数：
            user_id: 需要查询的运行记录所属用户。
            limit: 最多返回的记录数。
            offset: 返回结果前需要跳过的记录数。
            status: 可选的运行状态过滤条件。
            conversation_id: 可选的会话范围过滤条件。

        返回：
            按创建时间倒序排列的 Agent 运行记录列表。
        """

        statement = select(AgentRun).where(AgentRun.user_id == user_id)
        if status is not None:
            statement = statement.where(AgentRun.status == status)
        if conversation_id is not None:
            statement = statement.where(AgentRun.conversation_id == conversation_id)

        result = await self.session.execute(
            statement.order_by(AgentRun.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_user(
        self,
        user_id: str,
        *,
        status: str | None = None,
        conversation_id: str | None = None,
    ) -> int:
        """统计指定用户拥有的 Agent 运行记录数量。

        参数：
            user_id: 需要统计的运行记录所属用户。
            status: 可选的运行状态过滤条件。
            conversation_id: 可选的会话范围过滤条件。
        """

        statement = select(func.count()).select_from(AgentRun).where(AgentRun.user_id == user_id)
        if status is not None:
            statement = statement.where(AgentRun.status == status)
        if conversation_id is not None:
            statement = statement.where(AgentRun.conversation_id == conversation_id)

        result = await self.session.execute(statement)
        return int(result.scalar_one())

    async def get_by_id_for_user(
        self,
        run_id: str,
        user_id: str,
    ) -> AgentRun | None:
        """在运行记录归属于指定用户时返回该记录。"""

        result = await self.session.execute(
            select(AgentRun).where(
                AgentRun.id == run_id,
                AgentRun.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
