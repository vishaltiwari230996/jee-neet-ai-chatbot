"""Student profile value objects.

The profile is the single source of truth used by the orchestrator to
personalize answers. Splitting it from the persistence model lets us evolve
the storage layer (Postgres schema, migrations) without rippling changes
through domain code.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from neetai_core.ids import StudentId
from neetai_core.types import (
    Archetype,
    ClassLevel,
    ExamTarget,
    Language,
    LearningStyle,
    Subject,
)


class StudentProfile(BaseModel):
    """Immutable snapshot of what we know about a student.

    Mutations happen by producing a new instance via `model_copy(update=...)`;
    callers persist the new version. Pure-functional profile evolution keeps
    the orchestrator easy to reason about.
    """

    model_config = ConfigDict(frozen=True)

    student_id: StudentId

    class_level: ClassLevel
    exam_target: ExamTarget
    language: Language = Language.ENGLISH

    weak_subject: Subject | None = None
    strong_subject: Subject | None = None

    mock_score_range: str | None = Field(default=None, max_length=32)
    target_rank: int | None = Field(default=None, ge=1)

    study_hours_per_day: float | None = Field(default=None, ge=0, le=24)
    revision_habit: str | None = Field(default=None, max_length=64)
    main_problem: str | None = Field(default=None, max_length=120)
    mistake_pattern: str | None = Field(default=None, max_length=120)
    emotional_state: str | None = Field(default=None, max_length=64)
    learning_style: LearningStyle | None = None

    archetype: Archetype = Archetype.UNCLASSIFIED
    archetype_version: int = 1

    profile_confidence: float = Field(ge=0.0, le=1.0, default=0.0)

    created_at: datetime
    updated_at: datetime

    def missing_critical_fields(self) -> list[str]:
        """Field names that must be filled before personalized answering.

        The orchestrator uses this in step 4 of the answer pipeline to decide
        whether to ask a diagnostic question instead of answering.
        """
        critical = (
            "weak_subject",
            "main_problem",
            "learning_style",
        )
        return [name for name in critical if getattr(self, name) is None]
