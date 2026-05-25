"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_CLASS_LEVELS = ("class_11", "class_12", "dropper")
_EXAM_TARGETS = ("jee_main", "jee_advanced", "neet", "jee_main_advanced")
_LANGUAGES = ("en", "hi", "hi-en")
_SUBJECTS = ("physics", "chemistry", "mathematics", "biology")
_LEARNING_STYLES = (
    "basic_explanation",
    "examples",
    "tricks",
    "step_by_step",
    "visual",
)
_ARCHETYPES = (
    "weak_concepts_hardworking",
    "strong_concepts_poor_execution",
    "class_11_foundation",
    "class_12_balanced",
    "dropper",
    "unclassified",
)
_ANSWER_TYPES = ("single_choice", "multi_choice", "short_text", "number")


def _check(name: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    quoted = ",".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(f"{column} IN ({quoted})", name=name)


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("student_id", sa.String(64), primary_key=True),
        sa.Column("email", sa.String(320), nullable=True, unique=True),
        sa.Column("display_name", sa.String(120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "student_profiles",
        sa.Column(
            "student_id",
            sa.String(64),
            sa.ForeignKey("students.student_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("class_level", sa.String(16), nullable=False),
        sa.Column("exam_target", sa.String(32), nullable=False),
        sa.Column("language", sa.String(8), nullable=False, server_default="en"),
        sa.Column("weak_subject", sa.String(16), nullable=True),
        sa.Column("strong_subject", sa.String(16), nullable=True),
        sa.Column("mock_score_range", sa.String(32), nullable=True),
        sa.Column("target_rank", sa.Integer, nullable=True),
        sa.Column("study_hours_per_day", sa.Float, nullable=True),
        sa.Column("revision_habit", sa.String(64), nullable=True),
        sa.Column("main_problem", sa.String(120), nullable=True),
        sa.Column("mistake_pattern", sa.String(120), nullable=True),
        sa.Column("emotional_state", sa.String(64), nullable=True),
        sa.Column("learning_style", sa.String(32), nullable=True),
        sa.Column(
            "archetype",
            sa.String(48),
            nullable=False,
            server_default="unclassified",
        ),
        sa.Column(
            "archetype_version",
            sa.Integer,
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "profile_confidence",
            sa.Float,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        _check("ck_profiles_class_level", "class_level", _CLASS_LEVELS),
        _check("ck_profiles_exam_target", "exam_target", _EXAM_TARGETS),
        _check("ck_profiles_language", "language", _LANGUAGES),
        sa.CheckConstraint(
            "weak_subject IS NULL OR weak_subject IN ("
            + ",".join(f"'{s}'" for s in _SUBJECTS)
            + ")",
            name="ck_profiles_weak_subject",
        ),
        sa.CheckConstraint(
            "strong_subject IS NULL OR strong_subject IN ("
            + ",".join(f"'{s}'" for s in _SUBJECTS)
            + ")",
            name="ck_profiles_strong_subject",
        ),
        sa.CheckConstraint(
            "learning_style IS NULL OR learning_style IN ("
            + ",".join(f"'{s}'" for s in _LEARNING_STYLES)
            + ")",
            name="ck_profiles_learning_style",
        ),
        _check("ck_profiles_archetype", "archetype", _ARCHETYPES),
        sa.CheckConstraint(
            "profile_confidence >= 0 AND profile_confidence <= 1",
            name="ck_profiles_confidence_range",
        ),
        sa.CheckConstraint(
            "study_hours_per_day IS NULL OR (study_hours_per_day >= 0 AND study_hours_per_day <= 24)",
            name="ck_profiles_study_hours_range",
        ),
    )

    op.create_table(
        "question_bank",
        sa.Column("question_id", sa.String(32), primary_key=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("audience", JSONB, nullable=False),
        sa.Column("answer_type", sa.String(24), nullable=False),
        sa.Column("options", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("maps_to", sa.String(64), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="50"),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        _check("ck_question_bank_answer_type", "answer_type", _ANSWER_TYPES),
        sa.CheckConstraint(
            "priority >= 0 AND priority <= 100",
            name="ck_question_bank_priority_range",
        ),
    )
    op.create_index(
        "ix_question_bank_active_priority",
        "question_bank",
        ["is_active", "priority"],
    )

    op.create_table(
        "asked_questions",
        sa.Column(
            "student_id",
            sa.String(64),
            sa.ForeignKey("students.student_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "question_id",
            sa.String(32),
            sa.ForeignKey("question_bank.question_id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("raw_answer", sa.Text, nullable=True),
        sa.Column(
            "asked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_asked_questions_student",
        "asked_questions",
        ["student_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_asked_questions_student", table_name="asked_questions")
    op.drop_table("asked_questions")
    op.drop_index("ix_question_bank_active_priority", table_name="question_bank")
    op.drop_table("question_bank")
    op.drop_table("student_profiles")
    op.drop_table("students")
