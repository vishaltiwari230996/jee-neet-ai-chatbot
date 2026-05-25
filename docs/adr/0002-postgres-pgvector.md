# ADR 0002 — PostgreSQL + pgvector as the primary store

* **Status:** Accepted
* **Date:** 2026-05-20

## Context

We need: relational data (students, profiles, sessions, messages,
question bank), vector embeddings (knowledge-base chunks), and lexical
search (BM25-style for hybrid retrieval).

Options:

* **Postgres + pgvector** for everything (relational + vectors); native
  trigram indexes for lexical.
* **Postgres + dedicated vector DB** (Qdrant / Weaviate / Pinecone).
* **Single-purpose stores** for each concern.

## Decision

Use **PostgreSQL 16 + pgvector + pg_trgm** for all persistence at MVP.

We will reassess only if benchmarks at >5k QPS show pgvector latency
exceeds budget. At our anticipated traffic this is extremely unlikely.

## Consequences

**Positive**

* Single ops surface, single backup story, single transactional model.
* Joins between metadata and vector results stay in the database — no
  application-side fan-out.
* Free tier on Neon is generous; production migration to Cloud SQL or
  RDS is straightforward.

**Negative**

* pgvector HNSW performance lags Qdrant at very high QPS / very large
  corpora. Acceptable for our scale.
* Some advanced reranking pipelines that rely on dedicated vector DBs'
  filtering languages are unavailable; we'll handle with SQL.

## Alternatives considered

* **Qdrant from day one** — rejected; adds a second store with no
  measurable benefit at our scale, plus extra dev complexity (separate
  client, separate auth, separate backups).
