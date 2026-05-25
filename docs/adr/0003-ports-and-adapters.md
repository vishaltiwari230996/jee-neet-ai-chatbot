# ADR 0003 — Ports-and-adapters for external dependencies

* **Status:** Accepted
* **Date:** 2026-05-20

## Context

LLM provider, vector DB, cache, auth, and event bus are all things we
will swap, fall back to, or A/B test over the project's lifetime. We
need the domain code to be decoupled from any specific implementation.

## Decision

Adopt **ports and adapters** (hexagonal):

* Every external dependency has a `Protocol` in `packages/ports`.
* Implementations live in `adapters/*` and depend on `ports` + `core`
  only.
* Domain packages (`profiling`, `retrieval`, `orchestrator`, …) depend
  on `ports`, never on adapters or third-party SDKs.
* The DI container in `apps/api/container.py` is the sole place that
  knows which adapter is wired behind each port.

`import-linter` enforces this at lint time.

## Consequences

**Positive**

* Swapping providers is a single-file change in the container.
* Unit tests drop in `FakeLLMClient` / `InMemoryCache` without any
  monkeypatching.
* The shape of the interface forces us to think about the *contract*
  before the implementation.

**Negative**

* One layer of indirection for every external call.
* New engineers must learn the discipline of "no SDK imports outside
  adapters." Lint catches it, but it's an upfront mental cost.

## Alternatives considered

* **Use SDKs directly everywhere** — rejected; couples domain logic to
  vendor implementations and makes testing painful.
