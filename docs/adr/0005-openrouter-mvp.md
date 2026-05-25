# ADR 0005 — OpenRouter as primary LLM gateway (MVP)

* **Status:** Accepted
* **Date:** 2026-05-20

## Context

We need an LLM access strategy that:

* lets us A/B between Anthropic, OpenAI, Google models cheaply
* is operationally simple at MVP
* doesn't lock us in

Options:

1. **Direct-provider SDKs** (one integration per provider).
2. **OpenRouter** — single API, single bill, built-in fallbacks.
3. **LiteLLM-as-a-library** — multi-provider routing as a Python lib,
   we host nothing extra.

## Decision

* Use **OpenRouter** as the primary LLM gateway for MVP, with Anthropic
  Sonnet (strong tier) and Anthropic Haiku (cheap tier).
* All access goes through the `LLMClient` Protocol; OpenRouter is one
  adapter (`adapters/llm_openrouter`).
* Maintain a stubbed-but-real direct-Anthropic adapter
  (`adapters/llm_anthropic`) so the swap is one config flip if
  OpenRouter cost, latency, or reliability becomes a problem.

## Consequences

**Positive**

* Single integration unblocks experimentation across providers.
* OpenRouter's built-in cross-provider fallback improves uptime.
* Cost reporting per request is exposed by the gateway — feeds budgets
  and the admin dashboard.

**Negative**

* ~5% markup over direct pricing. At 5k students this is ~₹8–20 lakh/yr.
  We accept this for now in exchange for ops simplicity; revisit at
  Phase 7.
* Extra network hop (~50–150ms). Acceptable given target P95.
* PII surface increases by one party. Mitigated by the PII redaction
  layer that runs before the LLM call (Phase 5).
* Anthropic prompt caching support: VERIFY OpenRouter exposes cache
  breakpoints before relying on it.

## Revisit triggers

* OpenRouter monthly cost > $5k and direct pricing would save >20%.
* Sustained latency overhead measurably hurts P95 SLO.
* OpenRouter reliability drops below 99.5% over a rolling 30-day window.
* Anthropic prompt caching unavailable through OpenRouter.

When any of these triggers fires, flip `NEETAI_LLM_PROVIDER=anthropic`
and finish the direct adapter implementation.
