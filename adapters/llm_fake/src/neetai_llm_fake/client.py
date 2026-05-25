"""A scriptable LLM client for tests.

Tests load a list of expected responses; calls pop from the front. If the
script is empty when called, the test fails fast — no silent fallthrough to
"hello world" output that masks bugs.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from neetai_core.errors import DomainError
from neetai_ports import (
    CompletionRequest,
    CompletionResponse,
    LLMUsage,
    StreamChunk,
)


@dataclass(slots=True)
class ScriptedResponse:
    content: str
    structured: dict[str, Any] | None = None
    model_id: str = "fake/model"


@dataclass(slots=True)
class FakeLLMClient:
    """Deterministic LLM client. Pop responses in order, record calls for assertions."""

    completions: list[ScriptedResponse] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)
    recorded_requests: list[CompletionRequest] = field(default_factory=list)
    recorded_embed_inputs: list[list[str]] = field(default_factory=list)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.recorded_requests.append(request)
        if not self.completions:
            raise DomainError(
                "FakeLLMClient script exhausted — test asked for more completions than scripted",
            )
        scripted = self.completions.pop(0)
        return CompletionResponse(
            content=scripted.content,
            structured=scripted.structured,
            model_id=scripted.model_id,
            usage=LLMUsage(input_tokens=10, output_tokens=20),
            cost_usd=0.0,
            latency_ms=0,
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        """Stream the next scripted response as 8-char chunks.

        Useful for tests that exercise the streaming path without needing
        a real provider. Chunk size is small but deterministic.
        """
        self.recorded_requests.append(request)
        if not self.completions:
            raise DomainError(
                "FakeLLMClient script exhausted — test asked for more streams than scripted",
            )
        scripted = self.completions.pop(0)
        content = scripted.content
        step = 8
        for i in range(0, len(content), step):
            yield StreamChunk(
                delta=content[i : i + step],
                model_id=scripted.model_id,
            )
        yield StreamChunk(
            done=True,
            model_id=scripted.model_id,
            usage=LLMUsage(input_tokens=10, output_tokens=20),
            cost_usd=0.0,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.recorded_embed_inputs.append(list(texts))
        if not self.embeddings:
            raise DomainError(
                "FakeLLMClient embedding script exhausted",
            )
        return [self.embeddings.pop(0) for _ in texts]
