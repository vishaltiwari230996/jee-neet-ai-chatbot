"""Async engine + session factory.

The factory exposes a single `session()` async-context-manager. Repositories
take a session per call; the API layer manages session lifecycle per
request (one session per HTTP request, one transaction per response).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@dataclass(slots=True, frozen=True)
class DatabaseConfig:
    url: str
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 5
    pool_timeout_seconds: int = 30


class SessionFactory:
    """Encapsulates engine + sessionmaker so callers don't manage either."""

    def __init__(self, config: DatabaseConfig) -> None:
        self._engine = create_async_engine(
            config.url,
            echo=config.echo,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout_seconds,
            pool_pre_ping=True,
        )
        self._sessionmaker = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """One session per `async with`. Commits on clean exit, rolls back on error."""
        async with self._sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def healthcheck(self) -> bool:
        """Cheap probe for the readiness endpoint."""
        async with self._engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True

    async def aclose(self) -> None:
        await self._engine.dispose()


def create_session_factory(config: DatabaseConfig) -> SessionFactory:
    return SessionFactory(config)
