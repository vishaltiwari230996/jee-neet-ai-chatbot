#!/usr/bin/env python3
"""LLM smoke test.

Runs one tiny round-trip through the OpenRouter adapter for each tier and
prints the response + token usage + cost. Read this when you want to know,
in 10 seconds, "is the LLM end-to-end actually working from my machine?"

Usage:
    python scripts/smoke_llm.py
"""

from __future__ import annotations

import asyncio
import sys

from neetai_api.container import Container, build_container
from neetai_api.settings import LLMProvider, Settings
from neetai_ports import CompletionRequest, LLMMessage, LLMRole, ModelTier


async def _one_call(container: Container, *, tier: ModelTier, label: str) -> None:
    request = CompletionRequest(
        tier=tier,
        messages=[
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=(
                    "You are a JEE/NEET tutor. Reply in one short sentence."
                ),
            ),
            LLMMessage(
                role=LLMRole.USER,
                content="Why does a free-falling object feel weightless?",
            ),
        ],
        max_output_tokens=120,
        temperature=0.2,
    )

    response = await container.llm.complete(request)
    print(f"\n=== {label} ({tier.value}) ===")
    print(f"model:    {response.model_id}")
    print(f"latency:  {response.latency_ms} ms")
    print(
        f"tokens:   in={response.usage.input_tokens} "
        f"out={response.usage.output_tokens} "
        f"cost=${response.cost_usd:.5f}",
    )
    print(f"content:  {response.content}")


async def main() -> int:
    settings = Settings()
    if settings.llm_provider is LLMProvider.FAKE:
        print(
            "NEETAI_LLM_PROVIDER is 'fake' — set it to 'openrouter' in .env "
            "to run a real LLM smoke test.",
            file=sys.stderr,
        )
        return 1

    container = build_container(settings)
    try:
        await _one_call(container, tier=ModelTier.CHEAP, label="Cheap tier")
        await _one_call(container, tier=ModelTier.STRONG, label="Strong tier")
    finally:
        await container.aclose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
