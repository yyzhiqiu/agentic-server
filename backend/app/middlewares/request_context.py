from __future__ import annotations

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.common.context import reset_context, set_request_id, set_trace_id, set_user_id


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get("X-Trace-Id") or str(uuid4())
        request_id = request.headers.get("X-Request-Id") or str(uuid4())
        user_id = request.headers.get("X-User-Id")

        request.state.trace_id = trace_id
        request.state.request_id = request_id
        request.state.user_id = user_id

        trace_token = set_trace_id(trace_id)
        request_token = set_request_id(request_id)
        user_token = set_user_id(user_id)
        try:
            response = await call_next(request)
            response.headers["X-Trace-Id"] = trace_id
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            reset_context(trace_token, request_token, user_token)
