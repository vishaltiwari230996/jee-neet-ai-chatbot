# ADR 0008 — Persistence: SQLAlchemy 2.0 async + Alembic + repository protocols

* **Status:** Accepted
* **Date:** 2026-05-20

## Context

Phase 1 needs real persistence: the onboarding flow has to survive a
process restart, two API replicas have to see the same profile, and the
question bank has to be shared across deploys. We had to pick a stack
for ORM, migrations, and the seam between domain code and the database.

Constraints:

* The domain layer (`packages/core`, `packages/profiling`, …) must not
  know it's talking to Postgres. That's ADR 0003.
* The codebase is async (FastAPI, httpx). Sync DB calls would block the
  event loop and forfeit our scalability target (5k concurrent students).
* Schema changes have to be reviewable in PRs and deterministic to
  apply across environments.
* Re-running the question-CSV ingest must be safe (idempotent).

Options considered:

1. **`asyncpg` raw + hand-rolled migrations.** Fast, minimal magic.
   Loses the typed query builder, makes joins/upserts noisier, no
   ecosystem for migrations beyond ad-hoc SQL files.
2. **`SQLModel` (Pydantic + SQLAlchemy).** Tempting because Pydantic
   models are already pervasive. But blurs domain and persistence
   models into one class, which contradicts ADR 0003 — every time we
   needed a DB-only column (created_at, soft-delete flags) it would
   leak into the domain.
3. **`Tortoise ORM` / `Piccolo`.** Async-native but smaller community,
   weaker migration story, fewer Postgres-specific features
   (`ON CONFLICT`, `JSONB`, vector types) than SQLAlchemy 2.0.
4. **SQLAlchemy 2.0 + `psycopg[async]` + Alembic.** _Chosen._

## Decision

* **ORM:** SQLAlchemy 2.0 with the new typed `Mapped[]` API,
  `DeclarativeBase`, and `async_sessionmaker`. Lives in
  `adapters/db_postgres/models.py` — never imported by domain code.
* **Driver:** `psycopg[binary,pool]` v3 (the modern async-first driver
  that replaces `psycopg2` + `asyncpg`). Single dependency, native
  async, full Postgres feature support including `JSONB` and the
  pgvector extension we'll need in Phase 4.
* **Migrations:** Alembic, with hand-written initial revision rather
  than `autogenerate`. The initial schema has CHECK constraints for
  enum fields and explicit indexes that autogen can't infer correctly.
  All future revisions can use `autogenerate` once the baseline is
  truthful.
* **Domain ↔ ORM separation enforced by three layers:**
  1. **Repository Protocols** in `neetai_ports.repositories` define
     the contract — `StudentRepository`, `ProfileRepository`,
     `QuestionBankRepository`, `AskedQuestionRepository`. Domain code
     depends on these.
  2. **ORM models** in `adapters/db_postgres/models.py` are
     SQLAlchemy `DeclarativeBase` subclasses. The domain never sees
     them.
  3. **Mappers** in `adapters/db_postgres/mappers.py` are the only
     place the two ever touch. ORM → domain and back, one function
     per direction per aggregate. When the domain changes a field,
     mypy points at the mapper.
* **Two adapter implementations** of every repository:
  * `adapters/db_postgres/` — production, real Postgres.
  * `adapters/db_fake/` — in-memory dict-based; used by every unit
    test and by `database_backend=memory` for local smoke tests.
  Both are tested against the same `runtime_checkable` Protocols, so
  they cannot drift.
* **Session lifecycle:** `SessionFactory.session()` is an async
  context manager that commits on clean exit and rolls back on any
  exception. One session per call (not per request) at MVP — the
  acquire/release overhead is dwarfed by the LLM round-trips that
  follow. When that becomes hot, we'll move to one session per HTTP
  request via FastAPI dependencies.
* **Upserts use `INSERT ... ON CONFLICT DO UPDATE`** (Postgres-native
  via `sqlalchemy.dialects.postgresql.insert`). This makes the CSV
  ingest CLI re-runnable and gives us idempotent record-asked semantics.
* **`list_answered_question_ids` (not `list_asked_ids`):** the
  selector filters on the *answered* set so a question shown but not
  answered is re-offered on resume. The asked-vs-answered distinction
  is preserved on the row (`asked_at`, `answered_at`) for audit.
* **DB backend choice via `NEETAI_DATABASE_BACKEND`** (`postgres` |
  `memory`). The container picks the implementation at startup. No
  code reads `os.environ` outside `settings.py`.

## Consequences

**Positive**

* The domain test suite runs in ~1.5 s without Docker because every
  test uses the in-memory adapter — and exercises *the same Protocol*
  the Postgres adapter satisfies.
* Schema changes are reviewable: each Alembic file is a tiny diff in
  PR review. Rollback is a one-liner.
* Swapping Postgres for another SQL store later (we won't, but the
  option exists) means writing a third adapter — no domain changes.
* `JSONB`, `pgvector`, full-text search, etc. are first-class via the
  SQLAlchemy Postgres dialect. We never have to pick "ORM features"
  vs "real Postgres" — we get both.

**Negative**

* Two-adapter discipline costs duplication. Every repository method
  exists three times (Protocol, in-memory, Postgres). We accept the
  cost because the in-memory adapter pays for itself in test latency
  and runs-on-a-laptop-with-no-docker friendliness.
* `Mapped[]` API with `MappedAsDataclass` is new enough that two of the
  lint rules (RUF012, dataclass field ordering) caught us in Phase 1.
  Documented the gotchas in `CONTRIBUTING.md`.

## Revisit

* If the domain grows multi-aggregate transactions (e.g. "save
  profile + append asked question atomically"), introduce a
  `UnitOfWork` Protocol rather than letting routers manage commits.
* If we ever need horizontal sharding by student_id, the repository
  layer is where we'd thread a shard key. Currently a single primary
  with read replicas comfortably handles the 5k-student target.
* If async query latency becomes a bottleneck, evaluate `asyncpg` as
  a drop-in driver swap under SQLAlchemy 2.0.
