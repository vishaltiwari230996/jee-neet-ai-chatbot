"""FastAPI dependency helpers.

Routers receive their collaborators via these functions, never by importing
the container directly. That keeps routers trivially testable — swap a
single dependency in `app.dependency_overrides` without rewiring globals.
"""

from __future__ import annotations

from fastapi import Request

from neetai_api.container import Container


def get_container(request: Request) -> Container:
    container: Container | None = getattr(request.app.state, "container", None)
    if container is None:
        # This only happens if a route runs before the lifespan started —
        # almost always a misconfigured test. Better a loud error than a
        # confusing AttributeError downstream.
        raise RuntimeError("Container not initialized on app.state")
    return container
