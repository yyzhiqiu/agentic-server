from __future__ import annotations

from fastapi import FastAPI

from app.api.exception_handlers import register_exception_handlers
from app.api.v1 import router as v1_router
from app.api.v1.health import router as health_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.lifespan import lifespan
from app.middlewares.access_log import AccessLogMiddleware
from app.middlewares.audit_log import AuditLogMiddleware
from app.middlewares.cors import register_cors
from app.middlewares.request_context import RequestContextMiddleware
from app.middlewares.timing import TimingMiddleware


def create_app() -> FastAPI:
    configure_logging(settings.DEBUG)
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )
    register_cors(app)
    app.add_middleware(AuditLogMiddleware)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(v1_router, prefix=settings.API_PREFIX)
    return app
