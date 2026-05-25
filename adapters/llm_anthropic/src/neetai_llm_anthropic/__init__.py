"""Direct-Anthropic implementation of `LLMClient`.

Intentionally minimal at Phase 0. We ship the *interface satisfaction* and
configuration plumbing now so that swapping providers in production is a
single environment variable flip. The full implementation lands when (and
only when) we hit one of:

    * OpenRouter pricing/latency becomes the dominant cost
    * We need Anthropic-native prompt caching exposure that OpenRouter doesn't relay
    * OpenRouter reliability drops below our SLO

Until then this raises `NotImplementedError` if instantiated and called —
loud failure beats silent fallback.
"""

from neetai_llm_anthropic.client import AnthropicClient, AnthropicConfig

__all__ = ["AnthropicClient", "AnthropicConfig"]
