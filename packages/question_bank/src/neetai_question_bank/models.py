"""Question value objects.

`Question` is immutable. Mutation = ingesting a new CSV revision and
inserting/updating rows; we never edit a question in place.

Each question carries:
    * a stable `question_id` (the CSV's natural key — used as the primary key
      in the database too, so re-importing the same CSV is idempotent)
    * a `maps_to` field — the *single* profile attribute this answer feeds.
      Mapping logic lives in `neetai_profiling.mapper`. We keep the mapping
      declarative so non-engineers can edit the CSV without touching code.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from neetai_core.ids import QuestionId
from neetai_core.types import ClassLevel, ExamTarget


class AnswerType(StrEnum):
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    SHORT_TEXT = "short_text"
    NUMBER = "number"


class QuestionCategory(StrEnum):
    """Mirrors the categories teachers/PMs care about when curating the bank."""

    BASIC_DETAILS = "basic_details"
    ACADEMIC_DIAGNOSIS = "academic_diagnosis"
    BEHAVIOUR = "behaviour"
    MISTAKE_PATTERN = "mistake_pattern"
    EMOTIONAL = "emotional"
    LEARNING_STYLE = "learning_style"


class Question(BaseModel):
    """A single diagnostic question.

    Why immutable: we want one canonical version per ID so that historical
    profile data (asked_questions) stays interpretable. To replace a question,
    create a new ID and deprecate the old one in the CSV.
    """

    model_config = ConfigDict(frozen=True)

    question_id: QuestionId
    text: str = Field(min_length=1, max_length=400)
    category: QuestionCategory
    exam_targets: frozenset[ExamTarget]
    audience: frozenset[ClassLevel]
    answer_type: AnswerType
    options: tuple[str, ...] = Field(default_factory=tuple)
    maps_to: str = Field(
        min_length=1,
        description=("Name of the `StudentProfile` field this question's answer maps to."),
    )
    priority: int = Field(ge=0, le=100, default=50)
    is_required: bool = True

    def applies_to(self, class_level: ClassLevel) -> bool:
        """Whether this question is meaningful for the given student type."""
        return class_level in self.audience

    def applies_to_exam(self, exam_target: ExamTarget) -> bool:
        """Whether this question is meaningful for the given exam target."""
        return exam_target in self.exam_targets
