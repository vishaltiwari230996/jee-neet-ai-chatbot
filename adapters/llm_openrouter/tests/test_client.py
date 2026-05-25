"""Tests for the OpenRouter adapter.

Uses httpx.MockTransport — exercises the real adapter code path against a
controlled fake HTTP layer. No network, fully deterministic.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from neetai_core.errors import UpstreamError
from neetai_llm_openrouter import OpenRouterClient, OpenRouterConfig
from neetai_ports import (
    CompletionRequest,
    LLMClient,
    LLMMessage,
    LLMRole,
    ModelTier,
)


def _build_client(handler: httpx.MockTransport) -> OpenRouterClient:
    config = OpenRouterConfig(api_key="test-key", max_retries=1)
    http = httpx.AsyncClient(
        transport=handler,
        base_url=config.base_url,
        headers={"Authorization": f"Bearer {config.api_key}"},
    )
    return OpenRouterClient(config, http_client=http)


def _ok_chat_body(content: str) -> dict[str, Any]:
    return {
        "id": "test",
        "model": "anthropic/claude-haiku-4.5",
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 42, "completion_tokens": 7, "cost": 0.001},
    }


async def test_openrouter_satisfies_llm_client_protocol() -> None:
    config = OpenRouterConfig(api_key="x")
    client = OpenRouterClient(config, http_client=httpx.AsyncClient())
    assert isinstance(client, LLMClient)
    await client.aclose()


async def test_complete_returns_typed_response() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json=_ok_chat_body("hello there"))

    client = _build_client(httpx.MockTransport(handler))

    resp = await client.complete(
        CompletionRequest(
            tier=ModelTier.CHEAP,
            messages=[LLMMessage(role=LLMRole.USER, content="hi")],
        ),
    )

    assert resp.content == "hello there"
    assert resp.model_id == "anthropic/claude-haiku-4.5"
    assert resp.usage.input_tokens == 42
    assert resp.usage.output_tokens == 7
    assert resp.cost_usd == pytest.approx(0.001)
    assert captured["payload"]["model"] == "anthropic/claude-haiku-4.5"
    await client.aclose()


async def test_strong_tier_routes_to_strong_model() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json=_ok_chat_body("ok"))

    client = _build_client(httpx.MockTransport(handler))
    await client.complete(
        CompletionRequest(
            tier=ModelTier.STRONG,
            messages=[LLMMessage(role=LLMRole.USER, content="hi")],
        ),
    )
    assert captured["payload"]["model"] == "anthropic/claude-sonnet-4.6"
    await client.aclose()


async def test_response_schema_translated_to_provider_format() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json=_ok_chat_body("{}"))

    client = _build_client(httpx.MockTransport(handler))
    schema = {"type": "object", "properties": {"x": {"type": "string"}}}
    await client.complete(
        CompletionRequest(
            tier=ModelTier.CHEAP,
            messages=[LLMMessage(role=LLMRole.USER, content="hi")],
            response_schema=schema,
        ),
    )
    assert captured["payload"]["response_format"]["type"] == "json_schema"
    assert captured["payload"]["response_format"]["json_schema"]["schema"] == schema
    await client.aclose()


async def test_4xx_raises_non_retryable_upstream_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="bad request")

    client = _build_client(httpx.MockTransport(handler))
    with pytest.raises(UpstreamError) as info:
        await client.complete(
            CompletionRequest(
                tier=ModelTier.CHEAP,
                messages=[LLMMessage(role=LLMRole.USER, content="hi")],
            ),
        )
    assert info.value.provider == "openrouter"
    assert info.value.retryable is False
    await client.aclose()


async def test_5xx_retries_then_succeeds() -> None:
    calls: list[int] = []

    def handler(_: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(503, text="busy")
        return httpx.Response(200, json=_ok_chat_body("ok"))

    client = _build_client(httpx.MockTransport(handler))
    resp = await client.complete(
        CompletionRequest(
            tier=ModelTier.CHEAP,
            messages=[LLMMessage(role=LLMRole.USER, content="hi")],
        ),
    )
    assert resp.content == "ok"
    assert len(calls) == 2
    await client.aclose()


async def test_embed_returns_vectors() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]},
        )

    client = _build_client(httpx.MockTransport(handler))
    vectors = await client.embed(["a", "b"])
    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    await client.aclose()
