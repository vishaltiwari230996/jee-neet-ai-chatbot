"""SQLAlchemy ORM models.

Layout principles:
    * Every row has a `created_at` (UTC). `updated_at` lives on aggregates
      that actually mutate.
    * Enums are stored as TEXT with a CHECK constraint added by the
      migration — easier to evolve than native pg enums.
    * Foreign keys use ON DELETE CASCADE only when the child genuinely has
      no meaning without the parent. Asked-questions cascade with the
      student; questions and profiles do not.
    * No raw SQL outside this module + migrations.
"""

from __future__ import annotations

import typing
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)
from sqlalchemy.types import TypeEngine


class Base(MappedAsDataclass, DeclarativeBase):
    """Project-wide declarative base.

    `type_annotation_map` is SQLAlchemy ORM API — declaring it as a ClassVar
    tells ruff this dict is shared by design, not a mutable default to a
    constructor.
    """

    type_annotation_map: typing.ClassVar[dict[type, type[TypeEngine[Any]]]] = {
        dict[str, Any]: JSONB,
        list[str]: JSON,
    }


class StudentRow(Base):
    __tablename__ = "students"

    student_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True, default=None)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        init=False,
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        init=False,
    )

    profile: Mapped[ProfileRow] = relationship(
        back_populates="student",
        uselist=False,
        cascade="all, delete-orphan",
        init=False,
    )


class ProfileRow(Base):
    __tablename__ = "student_profiles"

    student_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("students.student_id", ondelete="CASCADE"),
        primary_key=True,
    )
    class_level: Mapped[str] = mapped_column(String(16))
    exam_target: Mapped[str] = mapped_column(String(32))
    language: Mapped[str] = mapped_column(String(8))

    weak_subject: Mapped[str | None] = mapped_column(String(16), nullable=True, default=None)
    strong_subject: Mapped[str | None] = mapped_column(String(16), nullable=True, default=None)
    mock_score_range: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)
    target_rank: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    study_hours_per_day: Mapped[float | None] = mapped_column(nullable=True, default=None)
    revision_habit: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    main_problem: Mapped[str | None] = mapped_column(String(120), nullable=True, default=None)
    mistake_pattern: Mapped[str | None] = mapped_column(String(120), nullable=True, default=None)
    emotional_state: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    learning_style: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)

    archetype: Mapped[str] = mapped_column(String(48), default="unclassified")
    archetype_version: Mapped[int] = mapped_column(Integer, default=1)
    profile_confidence: Mapped[float] = mapped_column(default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        init=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        init=False,
    )

    student: Mapped[StudentRow] = relationship(back_populates="profile", init=False)


class QuestionRow(Base):
    __tablename__ = "question_bank"

    question_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32))
    exam_targets: Mapped[list[str]] = mapped_column(JSONB)
    audience: Mapped[list[str]] = mapped_column(JSONB)
    answer_type: Mapped[str] = mapped_column(String(24))
    maps_to: Mapped[str] = mapped_column(String(64))
    # Fields with defaults must follow fields without (dataclass ordering rule).
    options: Mapped[list[str]] = mapped_column(JSONB, default_factory=list)
    priority: Mapped[int] = mapped_column(Integer, default=50)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        init=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        init=False,
    )

    __table_args__ = (Index("ix_question_bank_active_priority", "is_active", "priority"),)


class AskedQuestionRow(Base):
    __tablename__ = "asked_questions"

    student_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("students.student_id", ondelete="CASCADE"),
        primary_key=True,
    )
    question_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("question_bank.question_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    raw_answer: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    asked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        init=False,
    )
    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "question_id",
            name="uq_asked_questions_student_question",
        ),
    )
