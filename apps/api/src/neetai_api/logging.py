"""Structured logging.

Two output modes:
    * text — colorized, multi-line, for local dev
    * json — single-line, machine-parseable, for prod log aggregation

Every log line carries a `request_id`. Routers attach one via middleware so
downstream calls (including LLM traces) can be correlated end to end.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from neetai_api.settings import LogFormat, Settings


def configure_logging(settings: Settings) -> None:
    """Configure stdlib + structlog. Idempotent — safe to call multiple times."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stdout,
        force=True,
    )

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.log_format is LogFormat.JSON:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]
