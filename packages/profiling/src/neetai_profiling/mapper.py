"""Deterministic answer → profile mapping.

A small registry of field transforms. Adding a new diagnostic question
requires either reusing an existing transform (most common) or adding one
here. There is intentionally **no LLM** in this layer — slop-prevention by
construction.

Behaviour contract:

    apply_answer(profile, field_name, raw_answer)
        → new profile with `field_name` set (immutable copy)
        → raises `InvalidAnswer` if the answer does not parse into the
          expected type for that field

The returned profile also bumps `profile_confidence` slightly per answered
question. Capped at 1.0. The orchestrator (Phase 3) reads this value to
decide whether to ask a mid-chat diagnostic question.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from neetai_core.errors import ValidationError
from neetai_core.profile import StudentProfile
from neetai_core.types import (
    ClassLevel,
    ExamTarget,
    Language,
    LearningStyle,
    Subject,
)

_CONFIDENCE_PER_ANSWER = 0.10


class InvalidAnswer(ValidationError):
    """Raised when a raw answer can't be coerced to its target field type."""

    code = "invalid_answer"

    def __init__(self, field: str, raw: str, reason: str) -> None:
        super().__init__(f"Cannot map answer for '{field}': {reason}")
        self.field = field
        self.raw = raw


def apply_answer(
    profile: StudentProfile,
    *,
    field_name: str,
    raw_answer: str,
    now: datetime | None = None,
) -> StudentProfile:
    """Return a copy of `profile` with `field_name` set to the parsed answer."""
    transform = _TRANSFORMS.get(field_name)
    if transform is None:
        raise InvalidAnswer(field_name, raw_answer, "no transform registered")

    try:
        value = transform(raw_answer)
    except InvalidAnswer:
        raise
    except (ValueError, KeyError) as exc:
        raise InvalidAnswer(field_name, raw_answer, str(exc)) from exc

    return profile.model_copy(
        update={
            field_name: value,
            "profile_confidence": min(
                1.0,
                profile.profile_confidence + _CONFIDENCE_PER_ANSWER,
            ),
            "updated_at": now or datetime.now(UTC),
        },
    )


# ---------------------------------------------------------------------------
# Transforms: raw_answer (str) → typed value
# ---------------------------------------------------------------------------


def _to_subject(raw: str) -> Subject:
    return Subject(_norm(raw))


def _to_class_level(raw: str) -> ClassLevel:
    return ClassLevel(_norm(raw))


def _to_exam_target(raw: str) -> ExamTarget:
    return ExamTarget(_norm(raw))


def _to_language(raw: str) -> Language:
    return Language(_norm(raw))


def _to_learning_style(raw: str) -> LearningStyle:
    return LearningStyle(_norm(raw))


def _to_int(raw: str) -> int:
    value = int(raw.strip())
    if value < 0:
        raise ValueError("must be non-negative")
    return value


def _to_float_hours(raw: str) -> float:
    value = float(raw.strip())
    if not 0 <= value <= 24:
        raise ValueError("study hours must be between 0 and 24")
    return value


def _to_text(raw: str, *, max_length: int) -> str:
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("answer cannot be empty")
    if len(cleaned) > max_length:
        raise ValueError(f"answer exceeds {max_length} chars")
    return cleaned


def _norm(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


_TRANSFORMS: dict[str, Callable[[str], Any]] = {
    "class_level": _to_class_level,
    "exam_target": _to_exam_target,
    "language": _to_language,
    "weak_subject": _to_subject,
    "strong_subject": _to_subject,
    "learning_style": _to_learning_style,
    "target_rank": _to_int,
    "study_hours_per_day": _to_float_hours,
    "mock_score_range": lambda raw: _to_text(raw, max_length=32),
    "revision_habit": lambda raw: _to_text(raw, max_length=64),
    "main_problem": lambda raw: _to_text(raw, max_length=120),
    "mistake_pattern": lambda raw: _to_text(raw, max_length=120),
    "emotional_state": lambda raw: _to_text(raw, max_length=64),
}


def supported_fields() -> frozenset[str]:
    """The set of profile fields this mapper knows how to fill.

    Used by the question-bank ingestion CLI to validate that every question's
    `maps_to` has a corresponding transform.
    """
    return frozenset(_TRANSFORMS)
