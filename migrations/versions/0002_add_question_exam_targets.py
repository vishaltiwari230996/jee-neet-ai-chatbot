"""add exam targets to question bank

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_ALL_TARGETS = '["jee_main", "jee_advanced", "neet", "jee_main_advanced"]'


def upgrade() -> None:
    op.add_column(
        "question_bank",
        sa.Column("exam_targets", JSONB(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE question_bank "
            "SET exam_targets = CAST(:targets AS jsonb) "
            "WHERE exam_targets IS NULL",
        ).bindparams(targets=_ALL_TARGETS),
    )
    op.alter_column("question_bank", "exam_targets", nullable=False)


def downgrade() -> None:
    op.drop_column("question_bank", "exam_targets")
