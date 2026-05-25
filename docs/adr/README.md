# Architecture Decision Records

Every non-trivial architectural decision is captured here. ADRs are immutable
once **Accepted** — to change a decision, write a new ADR that supersedes it.

Status values: **Proposed** | **Accepted** | **Superseded** | **Deprecated**

## Index

| #    | Title                              | Status   |
| ---- | ---------------------------------- | -------- |
| 0001 | Modular monolith over microservices | Accepted |
| 0002 | PostgreSQL + pgvector as the primary store | Accepted |
| 0003 | Ports-and-adapters for external deps | Accepted |
| 0004 | No LangChain core; scoped LangGraph | Accepted |
| 0005 | OpenRouter for LLM access (MVP)    | Accepted |
| 0006 | Clerk for auth (MVP)               | Accepted |
| 0007 | uv workspace as the monorepo model | Accepted |
| 0008 | Persistence: SQLAlchemy 2.0 async + Alembic + repository protocols | Accepted |
