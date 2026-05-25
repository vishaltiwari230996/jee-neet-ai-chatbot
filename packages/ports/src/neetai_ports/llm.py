"""The single LLM contract.

Every LLM provider — OpenRouter, Anthropic direct, the in-memory fake used in
tests — implements this Protocol. Calling code never imports a provider SDK.

Design choices baked into this interface:

* `ModelTier` (strong / cheap) instead of model names. Calling code says
  "I need a cheap classification" and the adapter resolves to the configured
  model. Swapping Haiku → Flash → fine-tuned later is a config change.
* `response_schema` forces JSON-schema-constrained output. The adapter is
  responsible for using the provider's native structured-output feature
  (Anthropic tool use, OpenAI JSON mode, etc.) — never freeform parsing.
* `usage` and `cost_usd` come back on every response so the orchestrator can
  budget per request and per user without instrumenting providers separately.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ModelTier(StrEnum):
    STRONG = "strong"  # final answers, complex reasoning
    CHEAP = "cheap"  # classification, critique, safety
    EMBEDDING = "embedding"  # vectorization


class LLMRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(BaseModel):
    role: LLMRole
    content: str


class CompletionRequest(BaseModel):
    """Everything an adapter needs to make one call.

    Adapters MUST translate `response_schema` into provider-native structured
    output. They MUST NOT fall back to "parse the prose" — that is how slop
    enters the system.
    """

    tier: ModelTier
    messages: list[LLMMessage]
    temperature: float = Field(ge=0.0, le=2.0, default=0.2)
    max_output_tokens: int = Field(gt=0, le=8192, default=1024)
    response_schema: dict[str, Any] | None = None
    stop: list[str] | None = None

    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Free-form labels for tracing — student_id, doubt_type, etc.",
    )


class LLMUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0


class CompletionResponse(BaseModel):
    content: str
    structured: dict[str, Any] | None = None
    model_id: str  # the concrete model the adapter resolved the tier to
    usage: LLMUsage
    cost_usd: float = 0.0
    latency_ms: int = 0
    trace_id: str | None = None  # set when Langfuse/equivalent is wired in


class StreamChunk(BaseModel):
    """One incremental piece of a streamed completion.

    `delta` is the new text since the previous chunk (already de-cumulated).
    The final chunk has `done=True` and may include `usage`/`cost_usd` once
    the provider reports them.
    """

    delta: str = ""
    done: bool = False
    model_id: str | None = None
    usage: LLMUsage | None = None
    cost_usd: float | None = None


@runtime_checkable
class LLMClient(Protocol):
    """The only LLM interface the rest of the system knows about."""

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Make a single completion call. Adapter handles retries internally."""

    def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        """Stream a completion as a sequence of `StreamChunk`s.

        Yields incremental `delta`s, then exactly one terminal chunk with
        `done=True` carrying usage/cost. Cancellation propagates to the
        provider — the adapter MUST close the upstream connection if the
        consumer stops iterating.
        """

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, batched."""
