"""后端应用入口。

本模块只负责创建并暴露 FastAPI 应用实例，不承载业务逻辑或资源初始化。
应用级资源应由工厂函数和 lifespan 机制统一管理。
"""

from __future__ import annotations

from app.core.app_factory import create_app


app = create_app()
