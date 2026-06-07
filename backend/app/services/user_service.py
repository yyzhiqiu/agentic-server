"""轻量身份模型使用的用户准备服务。

本服务负责衔接请求级身份与 ``users`` 表中的轻量用户记录，
让这些记录可以作为资源归属外键使用。服务职责刻意保持收敛，
不实现完整认证系统或用户资料管理流程。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.user import User
from app.db.repositories.user_repo import UserRepository
from app.db.transaction import transaction
from app.schemas.user import UserRead


class UserService:
    """准备资源归属所需的轻量用户记录。

    当前脚手架通过“配置的游客身份 + 基于 API Key 派生的身份”来保持认证逻辑
    轻量，同时允许这些身份拥有会话、文件和 Agent 运行记录。
    本服务负责确保这些资源拥有者在业务流程依赖它们之前就已经被持久化。
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        user_repository: UserRepository,
    ) -> None:
        self.session = session
        self.user_repository = user_repository

    @staticmethod
    def _to_read(user: User) -> UserRead:
        """将已持久化用户记录映射为面向 API 的 Schema。"""

        return UserRead(
            id=user.id,
            name=user.name,
            email=user.email,
        )

    async def ensure_user(self, user_id: str, *, name: str | None = None) -> UserRead:
        """确保指定身份对应的轻量用户记录存在。

        参数：
            user_id: 用于拥有会话、文件与 Agent 运行记录的稳定标识。
            name: 当用户记录需要新建时使用的展示名。

        返回：
            已存在或新创建的轻量用户负载。

        副作用：
            当身份尚未持久化时，会在 Service 层控制的事务中新增一条
            ``users`` 记录。
        """

        user = await self.user_repository.get(user_id)
        if user is not None:
            return self._to_read(user)

        async with transaction(self.session):
            created = await self.user_repository.add(
                User(
                    id=user_id,
                    name=name or user_id,
                )
            )

        return self._to_read(created)

    async def get_anonymous(self) -> UserRead:
        """返回配置中的游客身份。

        这里保留 ``get_anonymous`` 方法名，是为了兼容旧调用点中仍将游客流程
        表述为匿名访问的写法。
        """

        return UserRead(
            id=settings.GUEST_USER_ID,
            name=settings.GUEST_USER_NAME,
        )
