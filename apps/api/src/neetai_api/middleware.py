"""Request-id middleware.

Stamps every incoming request with a uuid (or uses an inbound X-Request-Id
when present, so traces can be correlated across services). The id is bound
to structlog's contextvars so every log line in the request scope carries it.
"""

from __future__ import annotations

import uuid

import structlog
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_HEADER = "X-Request-Id"


class RequestIdMiddleware:
    """Pure ASGI middleware — avoids the overhead of BaseHTTPMiddleware."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        request_id = request.headers.get(_HEADER) or uuid.uuid4().hex

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                headers.append((_HEADER.lower().encode(), request_id.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_header)
