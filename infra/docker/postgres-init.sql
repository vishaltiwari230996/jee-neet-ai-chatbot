-- Postgres initialization. Runs once on first container start.
-- Extensions live here so they're created with superuser; Alembic migrations
-- (Phase 1+) handle the application schema.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- BM25-style lexical search (Phase 4)
CREATE EXTENSION IF NOT EXISTS "vector";     -- pgvector (Phase 4)
