"""Mapper tests = the spec for answer → profile-field translation.

Each transform gets a happy-path test and the most likely failure mode.
"""

from __future__ import annotations

import pytest

from neetai_core.types import LearningStyle, Subject
from neetai_profiling.mapper import (
    InvalidAnswer,
    apply_answer,
    supported_fields,
)

from .conftest import ProfileFactory


def test_supported_fields_includes_critical_profile_fields() -> None:
    fields = supported_fields()
    for required in ("weak_subject", "main_problem", "learning_style"):
        assert required in fields


def test_apply_answer_returns_new_profile_unchanged_original(
    make_profile: ProfileFactory,
) -> None:
    profile = make_profile()
    updated = apply_answer(profile, field_name="weak_subject", raw_answer="physics")
    assert profile.weak_subject is None
    assert updated.weak_subject is Subject.PHYSICS


def test_apply_answer_increments_confidence(make_profile: ProfileFactory) -> None:
    profile = make_profile()
    updated = apply_answer(profile, field_name="weak_subject", raw_answer="physics")
    assert updated.profile_confidence == pytest.approx(0.1)


def test_apply_answer_caps_confidence_at_one(make_profile: ProfileFactory) -> None:
    profile = make_profile(profile_confidence=0.95)
    updated = apply_answer(profile, field_name="weak_subject", raw_answer="physics")
    assert updated.profile_confidence == pytest.approx(1.0)


def test_unknown_field_raises_invalid_answer(make_profile: ProfileFactory) -> None:
    with pytest.raises(InvalidAnswer) as info:
        apply_answer(make_profile(), field_name="not_a_real_field", raw_answer="x")
    assert info.value.field == "not_a_real_field"


def test_subject_transform_is_case_insensitive(make_profile: ProfileFactory) -> None:
    updated = apply_answer(make_profile(), field_name="weak_subject", raw_answer="  PHYSICS  ")
    assert updated.weak_subject is Subject.PHYSICS


def test_subject_transform_rejects_unknown(make_profile: ProfileFactory) -> None:
    with pytest.raises(InvalidAnswer):
        apply_answer(make_profile(), field_name="weak_subject", raw_answer="basket weaving")


def test_learning_style_transform(make_profile: ProfileFactory) -> None:
    updated = apply_answer(make_profile(), field_name="learning_style", raw_answer="step by step")
    assert updated.learning_style is LearningStyle.STEP_BY_STEP


def test_study_hours_accepts_valid_float(make_profile: ProfileFactory) -> None:
    updated = apply_answer(make_profile(), field_name="study_hours_per_day", raw_answer="6.5")
    assert updated.study_hours_per_day == pytest.approx(6.5)


def test_study_hours_rejects_negative(make_profile: ProfileFactory) -> None:
    with pytest.raises(InvalidAnswer):
        apply_answer(make_profile(), field_name="study_hours_per_day", raw_answer="-1")


def test_study_hours_rejects_over_24(make_profile: ProfileFactory) -> None:
    with pytest.raises(InvalidAnswer):
        apply_answer(make_profile(), field_name="study_hours_per_day", raw_answer="30")


def test_target_rank_accepts_positive_int(make_profile: ProfileFactory) -> None:
    updated = apply_answer(make_profile(), field_name="target_rank", raw_answer="1500")
    assert updated.target_rank == 1500


def test_target_rank_rejects_non_numeric(make_profile: ProfileFactory) -> None:
    with pytest.raises(InvalidAnswer):
        apply_answer(make_profile(), field_name="target_rank", raw_answer="top 1000")


def test_text_field_rejects_empty(make_profile: ProfileFactory) -> None:
    with pytest.raises(InvalidAnswer):
        apply_answer(make_profile(), field_name="main_problem", raw_answer="   ")


def test_text_field_rejects_too_long(make_profile: ProfileFactory) -> None:
    with pytest.raises(InvalidAnswer):
        apply_answer(make_profile(), field_name="main_problem", raw_answer="x" * 500)


def test_text_field_trims_whitespace(make_profile: ProfileFactory) -> None:
    updated = apply_answer(
        make_profile(), field_name="main_problem", raw_answer="  Low mock score  "
    )
    assert updated.main_problem == "Low mock score"
