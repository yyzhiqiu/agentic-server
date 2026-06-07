"""用户数据访问辅助逻辑。

本 Repository 只负责当前轻量身份模型使用的用户持久化基础能力，
不提交事务，必须由 Service 层统一编排。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """处理轻量用户记录的 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)
