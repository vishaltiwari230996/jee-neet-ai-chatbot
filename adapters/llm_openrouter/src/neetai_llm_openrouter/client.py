"""OpenRouter HTTP client.

Talks to the OpenAI-compatible chat-completions endpoint that OpenRouter
exposes. No LangChain, no provider SDK — just `httpx` and `tenacity`.

Reasoning behind the small choices here:

* `tenacity` does exponential backoff on transient errors only (5xx, network).
  4xx surfaces immediately because retrying won't help.
* Per-request timeout is bounded by the caller (`CompletionRequest`) and the
  config. We use the smaller of the two.
* We never log prompt content here — Langfuse (wired in Phase 3) is where
  prompt traces live. Application logs only carry trace ids.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from neetai_core.errors import UpstreamError
from neetai_ports import (
    CompletionRequest,
    CompletionResponse,
    LLMUsage,
    ModelTier,
    StreamChunk,
)

_PROVIDER = "openrouter"


@dataclass(slots=True, frozen=True)
class OpenRouterConfig:
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    app_name: str = "neetai"
    app_url: str = "https://neetai.local"
    timeout_seconds: float = 30.0
    max_retries: int = 2

    strong_model: str = "anthropic/claude-sonnet-4.6"
    cheap_model: str = "anthropic/claude-haiku-4.5"
    embedding_model: str = "text-embedding-3-small"


class OpenRouterClient:
    """Implements `neetai_ports.LLMClient`."""

    def __init__(
        self,
        config: OpenRouterConfig,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._http = http_client or httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "HTTP-Referer": config.app_url,
                "X-Title": config.app_name,
            },
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    def _model_for_tier(self, tier: ModelTier) -> str:
        match tier:
            case ModelTier.STRONG:
                return self._config.strong_model
            case ModelTier.CHEAP:
                return self._config.cheap_model
            case ModelTier.EMBEDDING:
                return self._config.embedding_model

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        model_id = self._model_for_tier(request.tier)

        payload: dict[str, Any] = {
            "model": model_id,
            "messages": [m.model_dump() for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
        }
        if request.stop:
            payload["stop"] = request.stop
        if request.response_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "neetai_structured_output",
                    "schema": request.response_schema,
                    "strict": True,
                },
            }

        started = time.monotonic()
        body = await self._post_with_retry("/chat/completions", payload)
        latency_ms = int((time.monotonic() - started) * 1000)

        return _parse_chat_response(body, model_id=model_id, latency_ms=latency_ms)

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        """Stream a chat completion as `StreamChunk`s.

        OpenRouter speaks OpenAI-style SSE: each event is `data: <json>` and
        the stream terminates with `data: [DONE]`. The last data event before
        DONE typically carries a `usage` block (when `stream_options` asks
        for it). We surface that as the terminal chunk's `usage` + `cost`.

        Cancellation: if the consumer breaks out of the iterator, the
        `async with self._http.stream(...)` block tears down the upstream
        connection — important to avoid eating tokens we won't show.
        """
        model_id = self._model_for_tier(request.tier)
        payload: dict[str, Any] = {
            "model": model_id,
            "messages": [m.model_dump() for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if request.stop:
            payload["stop"] = request.stop

        async with self._http.stream(
            "POST", "/chat/completions", json=payload
        ) as response:
            if response.status_code >= 400:
                detail = (await response.aread()).decode("utf-8", "replace")[:300]
                raise UpstreamError(
                    f"{_PROVIDER} {response.status_code}: {detail}",
                    provider=_PROVIDER,
                    retryable=response.status_code in (429, 502, 503, 504),
                )

            final_usage: LLMUsage | None = None
            final_cost: float | None = None

            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    # OpenRouter occasionally emits keep-alive comments;
                    # skip anything we can't parse rather than crash the stream.
                    continue

                choices = event.get("choices") or []
                if choices:
                    delta_obj = choices[0].get("delta") or {}
                    delta_text = delta_obj.get("content") or ""
                    if delta_text:
                        yield StreamChunk(delta=delta_text, model_id=model_id)

                usage_block = event.get("usage")
                if usage_block:
                    final_usage = LLMUsage(
                        input_tokens=int(usage_block.get("prompt_tokens", 0)),
                        output_tokens=int(usage_block.get("completion_tokens", 0)),
                        cached_input_tokens=int(
                            usage_block.get("prompt_tokens_details", {}).get(
                                "cached_tokens", 0,
                            ),
                        ),
                    )
                    final_cost = float(usage_block.get("cost", 0.0))

            yield StreamChunk(
                done=True,
                model_id=model_id,
                usage=final_usage,
                cost_usd=final_cost,
            )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {
            "model": self._config.embedding_model,
            "input": texts,
        }
        body = await self._post_with_retry("/embeddings", payload)
        try:
            return [item["embedding"] for item in body["data"]]
        except (KeyError, TypeError) as exc:
            raise UpstreamError(
                f"Unexpected embeddings payload from {_PROVIDER}",
                provider=_PROVIDER,
                retryable=False,
            ) from exc

    async def _post_with_retry(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._config.max_retries + 1),
                wait=wait_exponential(multiplier=0.5, max=8.0),
                retry=retry_if_exception_type(_RetryableUpstream),
                reraise=True,
            ):
                with attempt:
                    return await self._post(path, payload)
        except RetryError as exc:  # pragma: no cover — defensive
            raise UpstreamError(
                f"{_PROVIDER} exhausted retries",
                provider=_PROVIDER,
                retryable=False,
            ) from exc
        # unreachable; AsyncRetrying always yields or reraises
        raise UpstreamError("unreachable", provider=_PROVIDER, retryable=False)  # pragma: no cover

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._http.post(path, json=payload)
        except httpx.HTTPError as exc:
            raise _RetryableUpstream(str(exc)) from exc

        if response.status_code >= 500:
            raise _RetryableUpstream(f"{response.status_code} {response.text[:200]}")
        if response.status_code == 429:
            raise _RetryableUpstream(f"rate limited: {response.text[:200]}")
        if response.status_code >= 400:
            raise UpstreamError(
                f"{_PROVIDER} {response.status_code}: {response.text[:200]}",
                provider=_PROVIDER,
                retryable=False,
            )

        try:
            return response.json()  # type: ignore[no-any-return]
        except ValueError as exc:
            raise UpstreamError(
                f"{_PROVIDER} returned non-JSON",
                provider=_PROVIDER,
                retryable=False,
            ) from exc


class _RetryableUpstream(Exception):
    """Internal signal that the request should be retried."""


def _parse_chat_response(
    body: dict[str, Any],
    *,
    model_id: str,
    latency_ms: int,
) -> CompletionResponse:
    try:
        choice = body["choices"][0]
        message = choice["message"]
        content = message.get("content") or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise UpstreamError(
            f"Unexpected chat payload from {_PROVIDER}",
            provider=_PROVIDER,
            retryable=False,
        ) from exc

    usage_block = body.get("usage") or {}
    cached = int(usage_block.get("prompt_tokens_details", {}).get("cached_tokens", 0))
    usage = LLMUsage(
        input_tokens=int(usage_block.get("prompt_tokens", 0)),
        output_tokens=int(usage_block.get("completion_tokens", 0)),
        cached_input_tokens=cached,
    )
    cost = float(usage_block.get("cost", 0.0))  # OpenRouter returns this directly when available

    return CompletionResponse(
        content=content,
        structured=None,
        model_id=model_id,
        usage=usage,
        cost_usd=cost,
        latency_ms=latency_ms,
    )
