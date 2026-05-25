"""FastAPI app factory.

Kept as a factory (not a module-level `app = FastAPI()`) because:
    * tests instantiate isolated app instances
    * configuration is injected, not imported
    * the container is built once per app lifetime
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from neetai_api.container import Container, build_container
from neetai_api.errors import install_error_handlers
from neetai_api.logging import configure_logging, get_logger
from neetai_api.middleware import RequestIdMiddleware
from neetai_api.routers import chat, health, onboarding, profile, webhooks
from neetai_api.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)
    log = get_logger("neetai_api")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container: Container = build_container(settings)
        app.state.container = container
        log.info(
            "app.startup",
            env=str(settings.env),
            llm_provider=str(settings.llm_provider),
        )
        try:
            yield
        finally:
            await container.aclose()
            log.info("app.shutdown")

    app = FastAPI(
        title="NeetAI API",
        version="0.1.0",
        description="Personalized JEE/NEET AI tutor — modular monolith.",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
    )

    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)

    app.include_router(health.router, tags=["health"])
    app.include_router(onboarding.router)
    app.include_router(profile.router)
    app.include_router(chat.router)
    app.include_router(webhooks.router)

    return app
