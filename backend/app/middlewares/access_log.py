from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        started_at = time.perf_counter()
        response = await call_next(request)
        cost_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "request method=%s path=%s status_code=%s cost_ms=%.2f trace_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            cost_ms,
            getattr(request.state, "trace_id", "-"),
        )
        return response
