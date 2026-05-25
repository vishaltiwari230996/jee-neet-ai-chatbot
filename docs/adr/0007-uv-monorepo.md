# ADR 0007 — uv workspace as the monorepo model

* **Status:** Accepted
* **Date:** 2026-05-20

## Context

We need a way to organize multiple Python packages (apps, domain
packages, adapters) in one repository with:

* single lockfile across all packages
* fast install in CI
* clear package boundaries
* a path to also host TypeScript apps (web, admin) later

Options:

1. **Single large package** — everything in one `src/` directory.
2. **Poetry workspaces / Rye / PDM** — established but slower.
3. **uv workspace** — newest, fastest, increasingly the standard.
4. **Pants / Bazel** — too heavy for our team size.

## Decision

Use a **uv workspace**. Each member package has its own `pyproject.toml`;
the root `pyproject.toml` declares `[tool.uv.workspace]` with the member
list. One `uv.lock` covers everything.

TypeScript apps (Phase 2 onwards) live under `apps/web` and `apps/admin`
in the same repo, managed by `pnpm` workspace as a parallel monorepo
tool. Cross-language coordination is by convention, not tooling.

## Consequences

**Positive**

* Single repo to clone, one lockfile to review.
* `uv sync` is order-of-magnitude faster than pip/poetry — meaningful
  in CI and for local onboarding.
* Each package can be released or extracted independently if we ever
  need to split.

**Negative**

* `uv` is younger than poetry; minor breaking changes still possible.
  Mitigation: pin a tested version in CI and dev (`UV_VERSION`).
* Some IDEs need a touch of config to recognise workspace members. We
  document this in the README.

## Alternatives considered

* **Poetry workspaces** — works, but ~10× slower install times in CI.
* **Single `src/` layout** — works for now, but the boundary discipline
  we want (import-linter) is much harder to enforce without separate
  packages.
