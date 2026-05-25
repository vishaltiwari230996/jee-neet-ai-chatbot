"""HTTP error translation.

Domain errors travel up uncaught; this layer turns them into stable JSON
problem payloads. Routers never construct HTTPException themselves — they
raise the appropriate `DomainError` and let this handler shape the response.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from neetai_core.errors import (
    DomainError,
    NotFoundError,
    SafetyViolation,
    UpstreamError,
    ValidationError,
)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValidationError)
    async def _validation(_: Request, exc: ValidationError) -> JSONResponse:
        return _problem(400, exc)

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return _problem(404, exc)

    @app.exception_handler(SafetyViolation)
    async def _safety(_: Request, exc: SafetyViolation) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "code": exc.code,
                "message": str(exc),
                "rule_id": exc.rule_id,
            },
        )

    @app.exception_handler(UpstreamError)
    async def _upstream(_: Request, exc: UpstreamError) -> JSONResponse:
        status = 503 if exc.retryable else 502
        return JSONResponse(
            status_code=status,
            content={
                "code": exc.code,
                "message": str(exc),
                "provider": exc.provider,
                "retryable": exc.retryable,
            },
        )

    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError) -> JSONResponse:
        return _problem(500, exc)


def _problem(status: int, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"code": exc.code, "message": str(exc)},
    )
