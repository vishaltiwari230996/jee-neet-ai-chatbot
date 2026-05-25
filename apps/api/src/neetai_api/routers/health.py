"""Health & readiness endpoints.

`/health/live`  — is the process up? Used by orchestrator restart policy.
`/health/ready` — is the process able to serve traffic? Probes DB.
`/`             — meta information for humans hitting the URL.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from neetai_api.container import Container
from neetai_api.deps import get_container
from neetai_api.settings import Settings, get_settings


class HealthResponse(BaseModel):
    status: Literal["ok"]
    env: str
    version: str


class ReadyResponse(BaseModel):
    status: Literal["ok", "degraded"]
    llm_provider: str
    database: Literal["ok", "down"]


router = APIRouter()


@router.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "service": "neetai-api",
        "docs": "/docs",
        "health": "/health/live",
    }


@router.get("/health/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    settings: Settings = get_settings()
    return HealthResponse(status="ok", env=str(settings.env), version="0.1.0")


@router.get("/health/ready", response_model=ReadyResponse)
async def readiness(
    response: Response,
    container: Annotated[Container, Depends(get_container)],
) -> ReadyResponse:
    settings = container.settings
    db_ok = False
    try:
        db_ok = await container.healthcheck_db()
    except Exception:
        db_ok = False

    overall: Literal["ok", "degraded"] = "ok" if db_ok else "degraded"
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadyResponse(
        status=overall,
        llm_provider=str(settings.llm_provider),
        database="ok" if db_ok else "down",
    )
