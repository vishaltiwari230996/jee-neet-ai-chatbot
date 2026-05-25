# ADR 0004 — No LangChain core; scoped LangGraph

* **Status:** Accepted
* **Date:** 2026-05-20

## Context

LangChain and LangGraph are the default frameworks reached for in LLM
projects. We seriously evaluated both.

LangChain:

* Heavy dependency tree (~80 transitive packages).
* History of breaking API changes (Runnable, LCEL, vector store
  interfaces).
* Leaky abstractions — debugging requires stepping through framework
  internals.
* Encourages tight coupling to its types throughout the codebase, which
  directly conflicts with ADR 0003.

LangGraph:

* Genuine state-machine / graph executor with a much more stable API.
* Native checkpointing, human-in-the-loop interrupts, conditional
  edges — these are real value for stateful flows.
* Can be used with minimal LangChain-core type coupling.

Most of what we are building is not "an agent." It is a
*deterministic pipeline* with LLM calls inside it (doubt
classification, retrieval, structured generation, safety). The control
flow is decided by us, not by an LLM choosing tools.

## Decision

* **Do not** depend on `langchain` (the core framework).
* **Do** use `langgraph`, but only when state-machine semantics earn it:
  1. **Onboarding flow (Phase 1):** _**Deferred.**_ During Phase 1 we
     realised the flow is genuinely linear — pick → present → record →
     pick — with idempotency at each step. Modelling it as a graph added
     ceremony without removing branching. Implemented instead as plain
     async methods on `OnboardingService` and ~100 lines of pure
     selector/mapper functions. Re-evaluate if the flow grows real
     conditional branches (e.g. adaptive difficulty paths).
  2. **Critique-revise sub-loop (Phase 5):** still planned for
     LangGraph. Conditional edges + max-iteration guard + checkpointing
     are exactly what it gives us, and the iteration count is bounded
     and small.
* The main answer pipeline (Phase 3) is plain Python async functions in
  `neetai_orchestrator.pipeline`. ~200 lines of readable, debuggable code.
* The `LLMClient` Protocol in `neetai_ports.llm` is the only LLM
  abstraction the system uses. Any LangGraph nodes we add later call it
  the same way every other component does — no LangChain types leak
  past the orchestrator boundary.

## Consequences

**Positive**

* When an answer goes wrong, debugging walks through our code, not
  through `Runnable.invoke` internals.
* We control upgrades to LLM features (prompt caching, structured
  output) directly; no waiting for framework releases.
* The eval harness can inspect every step of the pipeline because there
  is no opaque framework in the way.

**Negative**

* We reimplement small conveniences (chunkers, retry wrappers, model
  routers). Cost: a few hundred lines we own.
* Future hires may expect LangChain idioms. Onboarding doc should
  explain the choice (this ADR plus the README).

## Revisit

* If LangChain ships a markedly more stable 1.0 with the coupling concerns
  addressed, reassess in 6 months.
* If the onboarding flow gains adaptive branching (e.g. different
  question paths per archetype prediction, mid-flow backtracking),
  revisit the LangGraph adoption decision for Phase 1 too.
