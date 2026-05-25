"""Direct-Anthropic adapter — stub.

See `__init__.py` for the policy on when to flesh this out. The class is
present (and registers in the workspace) so the import-linter contract for
adapters is exercised across the board.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from neetai_ports import CompletionRequest, CompletionResponse, StreamChunk


@dataclass(slots=True, frozen=True)
class AnthropicConfig:
    api_key: str
    base_url: str = "https://api.anthropic.com/v1"
    timeout_seconds: float = 30.0

    strong_model: str = "claude-sonnet-4-20250514"
    cheap_model: str = "claude-haiku-4-20250514"
    embedding_model: str = "voyage-3"  # Anthropic recommends Voyage for embeddings


class AnthropicClient:
    """Implements `neetai_ports.LLMClient` — full implementation deferred."""

    def __init__(self, config: AnthropicConfig) -> None:
        self._config = config

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        raise NotImplementedError(
            "Direct-Anthropic adapter is intentionally a stub at Phase 0. "
            "Set NEETAI_LLM_PROVIDER=openrouter or =fake.",
        )

    async def stream(
        self,
        request: CompletionRequest,  # noqa: ARG002 — stub conforms to LLMClient
    ) -> AsyncIterator[StreamChunk]:
        raise NotImplementedError(
            "Direct-Anthropic adapter is intentionally a stub at Phase 0.",
        )
        yield StreamChunk(done=True)  # type: ignore[unreachable]  # keeps this an async generator for the Protocol

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "Direct-Anthropic adapter is intentionally a stub at Phase 0.",
        )
