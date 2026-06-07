from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.common.error_codes import ErrorCode
from app.common.exceptions import AppException
from app.common.responses import error_response

logger = logging.getLogger("app.exceptions")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.code, exc.message, exc.data),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_response(
                ErrorCode.REQUEST_VALIDATION_ERROR,
                data={"errors": exc.errors()},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = ErrorCode.NOT_FOUND if exc.status_code == 404 else ErrorCode.INTERNAL_ERROR
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(code, str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def unknown_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception path=%s", request.url.path)
        return JSONResponse(
            status_code=500,
            content=error_response(ErrorCode.INTERNAL_ERROR),
        )
