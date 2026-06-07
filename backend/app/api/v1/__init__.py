"""V1 版本 API 路由聚合模块。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.agent import router as agent_router
from app.api.v1.agents import router as agents_router
from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.files import router as files_router


router = APIRouter()
router.include_router(agents_router)
router.include_router(chat_router)
router.include_router(conversations_router)
router.include_router(agent_router)
router.include_router(files_router)
