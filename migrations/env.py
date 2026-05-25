"""Alembic environment.

Reads the connection URL from `NEETAI_DATABASE_URL`. Always uses the sync
psycopg driver for migrations (Alembic doesn't need async; using the sync
driver keeps the migration command predictable and easy to run from CI).
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR.parent / "adapters" / "db_postgres" / "src"))

from neetai_db_postgres.models import Base  # noqa: E402

alembic_config = context.config
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

# Resolve DB URL: env var first, then alembic.ini. We keep the `+psycopg`
# driver suffix — psycopg (v3) supports both sync and async usage off the
# same URL, and `engine_from_config` below uses sync. We only normalise
# the case where someone passes the bare `postgresql://` form (which would
# otherwise default to psycopg2 and break the missing-driver way).
_raw_url = os.environ.get(
    "NEETAI_DATABASE_URL",
    alembic_config.get_main_option("sqlalchemy.url", ""),
)
if _raw_url.startswith("postgresql://"):
    _raw_url = _raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
alembic_config.set_main_option("sqlalchemy.url", _raw_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=alembic_config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg_section = alembic_config.get_section(alembic_config.config_ini_section) or {}
    connectable = engine_from_config(
        cfg_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
