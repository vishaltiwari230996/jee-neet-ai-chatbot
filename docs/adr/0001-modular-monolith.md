# ADR 0001 — Modular monolith over microservices

* **Status:** Accepted
* **Date:** 2026-05-20

## Context

Target scale: 5,000 active students, ~10 messages/day each. We're a small
team, no dedicated SRE, and we need to ship MVP fast.

We considered three topologies:

1. **Microservices** (separate processes for profiling, retrieval, chat,
   admin, etc.).
2. **Modular monolith** — one deployable, hard module boundaries enforced
   by lint rules and code review.
3. **Big ball of mud** (no enforced boundaries).

## Decision

We ship as a **modular monolith**, with module boundaries enforced by
`import-linter` contracts (see `.importlinter`). Each domain area is its
own Python package and communicates through `neetai_ports` interfaces.

We split into separate services *only* when one of these is true:

* A workload has fundamentally different scaling needs (e.g. embedding
  workers vs. request handlers — already separated as `apps/workers/`).
* Two parts of the system need independent release cadence and conflict
  in practice.
* Compliance forces isolation (e.g. PII processor isolation).

## Consequences

**Positive**

* One deployable to operate; one tracing context end to end.
* Refactoring is trivial — moving code between modules is in-process.
* No premature gRPC/protobuf/service-mesh tax.
* Domain boundaries are still real (lint-enforced), so the splitting cost
  later is bounded.

**Negative**

* A bug in one module can theoretically take down the whole process. We
  mitigate via: per-route timeouts, circuit-breaking on adapters, sentry
  alerting on unhandled exceptions.
* Scaling one module hot-spots the whole binary. Acceptable until we hit
  a real bottleneck under load test.

## Alternatives considered

* **Microservices from day one** — rejected; ops cost and serialization
  overhead are not justified at our scale, and would slow MVP delivery.
