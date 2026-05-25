"""End-to-end smoke tests for the FastAPI app.

These run against an in-process ASGI client — no network, no docker, no
real LLM. They prove that:
    * the app starts up cleanly
    * the DI container assembles successfully with the fake provider
    * health endpoints behave
    * the request-id middleware sets the response header
"""

from __future__ import annotations

import httpx


async def test_root_serves_meta(client: httpx.AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "neetai-api"


async def test_liveness_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "env": "local", "version": "0.1.0"}


async def test_readiness_reports_llm_provider(client: httpx.AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["llm_provider"] == "fake"


async def test_request_id_round_trips(client: httpx.AsyncClient) -> None:
    response = await client.get("/health/live", headers={"X-Request-Id": "abc-123"})
    assert response.headers["x-request-id"] == "abc-123"


async def test_request_id_generated_when_missing(client: httpx.AsyncClient) -> None:
    response = await client.get("/health/live")
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) >= 16
