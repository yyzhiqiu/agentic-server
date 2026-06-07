"""后端应用入口。

本模块只负责创建并暴露 FastAPI 应用实例，不承载业务逻辑或资源初始化。
应用级资源应由工厂函数和 lifespan 机制统一管理。
"""

from __future__ import annotations

import asyncio
import sys
import warnings

from app.core.app_factory import create_app


def _configure_windows_event_loop_policy() -> None:
    """在 Windows 上切换为 SelectorEventLoopPolicy 以兼容异步 checkpoint。"""

    if sys.platform != "win32":
        return

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        policy_factory = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
        if policy_factory is None:
            return

        current_policy = asyncio.get_event_loop_policy()
        if isinstance(current_policy, policy_factory):
            return

        asyncio.set_event_loop_policy(policy_factory())


_configure_windows_event_loop_policy()

app = create_app()
