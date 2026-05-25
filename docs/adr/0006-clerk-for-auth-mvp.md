# ADR 0006 — Clerk for auth (MVP)

* **Status:** Accepted
* **Date:** 2026-05-20

## Context

Auth is high-stakes and time-consuming to build correctly (sessions,
password reset, social login, MFA, JWT validation, rotation). Many of
our users will be minors, which raises the bar further.

Options:

1. **Roll our own** (FastAPI-Users / Authlib / sessions).
2. **Clerk** — managed auth with React/Next.js SDKs.
3. **Supabase Auth** — managed auth tied to Supabase as a platform.

## Decision

Use **Clerk** for MVP. Auth lives behind the `AuthProvider` Protocol in
`neetai_ports.auth`, so the rest of the system depends on the interface,
not on Clerk.

A **fake** auth adapter is used in local dev and tests.

## Consequences

**Positive**

* 2–3 weeks of build time saved at MVP.
* Standard security primitives (rate limiting, breach detection, MFA) are
  there from day one.
* Easy social login when we need it.

**Negative**

* Vendor cost scales with MAU (~$25 / 1000 MAU at Clerk's current
  pricing; budget accordingly).
* Per-environment vendor account management.
* Migration cost if we self-host later (mitigated by the port + the fact
  that we never store auth state directly).

## Migration strategy

If we hit a price threshold or a sovereignty requirement, swap the Clerk
adapter for a self-hosted Keycloak / Authentik adapter. The rest of the
system does not change.
