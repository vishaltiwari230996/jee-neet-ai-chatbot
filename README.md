# NeetAI

A personalized JEE/NEET AI tutor. Understands the student first, then teaches.

> Status: **Phase 0 — foundation.** No business endpoints yet; the goal of
> this phase is a hard, clean substrate for the next six phases.

---

## What this is

The product blueprint (`neetaichatbot.md`) describes a chatbot that:

1. Profiles each student through a short diagnostic.
2. Classifies their doubts (concept / strategy / emotional / etc.).
3. Retrieves verified academic content (RAG).
4. Generates a personalized, structured answer like a real teacher would.

The engineering challenge is delivering that **without AI slop** — without
generic, hallucinated, "feels like ChatGPT" answers. That requirement
drives nearly every design choice in this repo.

---

## How the system is organized

```
apps/
  api/        FastAPI transport layer (thin: routing + DI)
packages/
  core/       Shared domain types, errors, value objects
  ports/      Pure Protocol interfaces for every external dependency
  profiling/         (Phase 1)
  question_bank/     (Phase 1)
  doubt_classifier/  (Phase 3)
  retrieval/         (Phase 4)
  orchestrator/      (Phase 3 — the answer pipeline)
  safety/            (Phase 5)
  feedback/          (Phase 3)
  analytics/         (Phase 6)
adapters/
  llm_openrouter/  Real LLM provider (default for MVP)
  llm_anthropic/   Direct-Anthropic adapter (fallback)
  llm_fake/        Scripted client for tests
docs/adr/          Architecture Decision Records
infra/docker/      Local stack init
evals/             Eval harness + golden datasets (Phase 3+)
migrations/        Alembic migrations (Phase 1+)
```

The dependency rules are enforced by `import-linter` in CI:

* **Domain packages** depend on `core` + `ports` only. No FastAPI, no SDKs.
* **Ports** depend on `core` only.
* **Adapters** depend on `core` + `ports`. Not on each other, not on domain.
* **The API app** depends on everything (it composes them).

This is what "no tight coupling" means here in practice.

---

## Anti-AI-slop strategy

See [`docs/adr/0004-no-langchain-scoped-langgraph.md`](docs/adr/0004-no-langchain-scoped-langgraph.md)
and the project blueprint for the full plan. In short:

1. Deterministic > AI. Rules first, LLM only where rules fail.
2. Every LLM call returns **JSON-schema-validated** output (no prose parsing).
3. Every answer carries **citations** to retrieved chunks; the orchestrator
   verifies citations exist before sending the response.
4. A **golden eval set** gates prompt / model changes in CI.
5. A separate **safety layer** scans inputs and outputs for distress signals,
   banned phrases, and false guarantees (blueprint §13).

LangChain is intentionally absent. LangGraph is used only for the onboarding
state machine and the critique-revise loop — places where state machines
genuinely earn their keep.

---

## Getting started

Prerequisites: Docker, Python 3.12, and `uv` (`pip install --user uv`).

```bash
# 1. Bootstrap
cp .env.example .env
make bootstrap          # installs workspace + pre-commit hooks

# 2. Start local infra
make dev                # postgres + redis in docker

# 3. Run the API on the host (reloads on save)
make api

# 4. Verify
curl http://localhost:8000/health/live
open  http://localhost:8000/docs
```

All commands:

```bash
make           # menu
make check     # ruff lint + mypy + import-linter
make test      # unit tests (no integration, no LLM)
make fmt       # auto-format
```

---

## Phase plan

| Phase | What lands                                           | Status   |
| ----- | ---------------------------------------------------- | -------- |
| 0     | Workspace, ports, adapters, API skeleton, CI         | ✓ Done   |
| 1     | Question bank ingestion, profiling, archetype rules  | Up next  |
| 2     | Next.js web onboarding UI                            | Planned  |
| 3     | Chat MVP without RAG (orchestrator + structured LLM) | Planned  |
| 4     | RAG knowledge base (chunk → embed → hybrid search)   | Planned  |
| 5     | Safety + eval harness                                | Planned  |
| 6     | Beta with 100 students + admin dashboard             | Planned  |
| 7     | Scale to 5,000 + production hardening                | Planned  |

See the project blueprint (`neetaichatbot.md`) for the product vision and
the ADRs in `docs/adr/` for the engineering choices.

---

## Contributing

* Read `CONTRIBUTING.md` before opening a PR.
* Every PR runs lint, types, import-linter, and unit tests.
* New external dependencies require an ADR.
