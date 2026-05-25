"""Postgres adapters.

* `models`        — SQLAlchemy ORM models (one file, full schema)
* `mappers`       — ORM ↔ domain translation, isolated so neither side leaks
* `repositories`  — implementations of every repository Protocol
* `session`       — async engine + session factory

Why ORM models live *here* (in the adapter) and not in core: ORM models are
infrastructure. They know about column types, foreign keys, indexes, and
PostgreSQL specifics. The domain models (`StudentProfile`, `Question`) are
free of all that. The `mappers` module is the only place the two ever meet.
"""

from neetai_db_postgres.repositories import (
    PgAskedQuestionRepository,
    PgProfileRepository,
    PgQuestionBankRepository,
    PgStudentRepository,
)
from neetai_db_postgres.session import (
    DatabaseConfig,
    SessionFactory,
    create_session_factory,
)

__all__ = [
    "DatabaseConfig",
    "PgAskedQuestionRepository",
    "PgProfileRepository",
    "PgQuestionBankRepository",
    "PgStudentRepository",
    "SessionFactory",
    "create_session_factory",
]
