"""在响应返回后记录最小请求上下文的审计中间件。"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

logger = logging.getLogger("app.audit.middleware")


class AuditLogMiddleware(BaseHTTPMiddleware):
    """输出请求审计日志，但不负责业务侧持久化。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        """在下游处理器返回响应后记录请求上下文。"""

        response = await call_next(request)
        logger.info(
            "审计日志 请求方法=%s 路径=%s 状态码=%s 链路ID=%s 用户ID=%s",
            request.method,
            request.url.path,
            response.status_code,
            getattr(request.state, "trace_id", "-"),
            getattr(request.state, "user_id", None) or settings.GUEST_USER_ID,
        )
        return response
