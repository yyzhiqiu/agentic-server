from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        started_at = time.perf_counter()
        response = await call_next(request)
        cost_ms = (time.perf_counter() - started_at) * 1000
        response.headers["X-Process-Time-Ms"] = f"{cost_ms:.2f}"
        return response
