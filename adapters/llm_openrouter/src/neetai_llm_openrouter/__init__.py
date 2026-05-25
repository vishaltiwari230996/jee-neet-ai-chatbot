"""OpenRouter implementation of `LLMClient`.

Why OpenRouter for MVP:
    * One API, one bill, one mental model.
    * Built-in cross-provider fallbacks.
    * Easy A/B between Sonnet / Haiku / Flash / etc.

This adapter:
    * Maps `ModelTier` → configured model id.
    * Forces JSON-schema-constrained output via `response_format` when a schema
      is provided on the request — never freeform-parse the prose.
    * Translates HTTP failures into typed `UpstreamError`s the orchestrator
      knows how to react to.
    * Computes cost from the response's `usage` block + a pricing table —
      the orchestrator reads `response.cost_usd` and enforces budgets.
"""

from neetai_llm_openrouter.client import OpenRouterClient, OpenRouterConfig

__all__ = ["OpenRouterClient", "OpenRouterConfig"]
