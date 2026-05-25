from datetime import UTC, datetime

import pytest
from pydantic import ValidationError as PydanticValidationError

from neetai_core import (
    Archetype,
    ClassLevel,
    ExamTarget,
    LearningStyle,
    StudentId,
    Subject,
)
from neetai_core.profile import StudentProfile


def _fresh_profile(**overrides: object) -> StudentProfile:
    now = datetime.now(UTC)
    base: dict[str, object] = {
        "student_id": StudentId("stu_test_001"),
        "class_level": ClassLevel.DROPPER,
        "exam_target": ExamTarget.JEE_MAIN_ADVANCED,
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return StudentProfile.model_validate(base)


def test_profile_is_immutable() -> None:
    profile = _fresh_profile()
    with pytest.raises(PydanticValidationError):
        profile.weak_subject = Subject.PHYSICS  # type: ignore[misc]


def test_missing_critical_fields_lists_unset_fields() -> None:
    profile = _fresh_profile()
    missing = profile.missing_critical_fields()
    assert set(missing) == {"weak_subject", "main_problem", "learning_style"}


def test_missing_critical_fields_empty_when_complete() -> None:
    profile = _fresh_profile(
        weak_subject=Subject.PHYSICS,
        main_problem="Low mock score",
        learning_style=LearningStyle.STEP_BY_STEP,
    )
    assert profile.missing_critical_fields() == []


def test_profile_evolves_via_model_copy() -> None:
    profile = _fresh_profile()
    evolved = profile.model_copy(update={"archetype": Archetype.DROPPER})
    assert profile.archetype is Archetype.UNCLASSIFIED
    assert evolved.archetype is Archetype.DROPPER


def test_profile_confidence_bounded() -> None:
    with pytest.raises(PydanticValidationError):
        _fresh_profile(profile_confidence=1.5)


def test_study_hours_bounded() -> None:
    with pytest.raises(PydanticValidationError):
        _fresh_profile(study_hours_per_day=30)
