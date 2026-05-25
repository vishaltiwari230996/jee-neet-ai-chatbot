"""Archetype classifier tests = the spec for blueprint §5.

Plus a hypothesis property test that proves the classifier is total — every
syntactically-valid profile produces some `Archetype`, never an exception.
"""

from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import given
from hypothesis import strategies as st

from neetai_core.ids import StudentId
from neetai_core.profile import StudentProfile
from neetai_core.types import (
    Archetype,
    ClassLevel,
    ExamTarget,
    LearningStyle,
    Subject,
)
from neetai_profiling.archetype import classify_archetype

from .conftest import ProfileFactory


def test_no_signal_means_unclassified(make_profile: ProfileFactory) -> None:
    assert classify_archetype(make_profile()) is Archetype.UNCLASSIFIED


def test_class_11_with_minimal_signal_is_foundation(
    make_profile: ProfileFactory,
) -> None:
    profile = make_profile(
        class_level=ClassLevel.CLASS_11,
        weak_subject=Subject.PHYSICS,
    )
    assert classify_archetype(profile) is Archetype.CLASS_11_FOUNDATION


def test_class_12_with_minimal_signal_is_balanced(
    make_profile: ProfileFactory,
) -> None:
    profile = make_profile(
        class_level=ClassLevel.CLASS_12,
        weak_subject=Subject.PHYSICS,
    )
    assert classify_archetype(profile) is Archetype.CLASS_12_BALANCED


def test_dropper_with_minimal_signal_is_dropper(
    make_profile: ProfileFactory,
) -> None:
    profile = make_profile(
        class_level=ClassLevel.DROPPER,
        weak_subject=Subject.PHYSICS,
    )
    assert classify_archetype(profile) is Archetype.DROPPER


def test_strong_concepts_poor_execution_overrides_class_fallback(
    make_profile: ProfileFactory,
) -> None:
    profile = make_profile(
        class_level=ClassLevel.CLASS_12,
        study_hours_per_day=7.0,
        main_problem="Low mock score",
        mistake_pattern="Silly mistake + time pressure",
        learning_style=LearningStyle.STEP_BY_STEP,
    )
    assert classify_archetype(profile) is Archetype.STRONG_CONCEPTS_POOR_EXECUTION


def test_weak_concepts_hardworking_overrides_class_fallback(
    make_profile: ProfileFactory,
) -> None:
    profile = make_profile(
        class_level=ClassLevel.CLASS_12,
        study_hours_per_day=8.0,
        main_problem="Backlog and concept gaps",
    )
    assert classify_archetype(profile) is Archetype.WEAK_CONCEPTS_HARDWORKING


def test_dropper_with_strong_concepts_poor_execution_still_uses_behavioural(
    make_profile: ProfileFactory,
) -> None:
    """Behavioural rule fires before class-level fallback — even for droppers."""
    profile = make_profile(
        class_level=ClassLevel.DROPPER,
        study_hours_per_day=6.0,
        main_problem="Low mock score",
        mistake_pattern="Silly calculation mistakes during timed tests",
    )
    assert classify_archetype(profile) is Archetype.STRONG_CONCEPTS_POOR_EXECUTION


def test_low_study_hours_disqualifies_behavioural_archetype(
    make_profile: ProfileFactory,
) -> None:
    """Behavioural archetypes require sustained study; ≤5 hrs falls back."""
    profile = make_profile(
        class_level=ClassLevel.CLASS_12,
        study_hours_per_day=2.0,
        main_problem="Low mock score",
        mistake_pattern="Silly mistakes",
    )
    assert classify_archetype(profile) is Archetype.CLASS_12_BALANCED


def test_classifier_is_deterministic(make_profile: ProfileFactory) -> None:
    profile = make_profile(
        class_level=ClassLevel.DROPPER,
        weak_subject=Subject.PHYSICS,
        main_problem="Backlog",
        study_hours_per_day=8.0,
    )
    first = classify_archetype(profile)
    second = classify_archetype(profile)
    assert first is second


# ---------------------------------------------------------------------------
# Property test: the classifier is total — every valid profile gets *some*
# Archetype, the function never raises and never returns None.
# ---------------------------------------------------------------------------


@st.composite
def _profiles(draw: st.DrawFn) -> StudentProfile:
    now = datetime.now(UTC)
    return StudentProfile(
        student_id=StudentId(draw(st.text(min_size=1, max_size=8))),
        class_level=draw(st.sampled_from(list(ClassLevel))),
        exam_target=draw(st.sampled_from(list(ExamTarget))),
        weak_subject=draw(st.one_of(st.none(), st.sampled_from(list(Subject)))),
        strong_subject=draw(st.one_of(st.none(), st.sampled_from(list(Subject)))),
        study_hours_per_day=draw(st.one_of(st.none(), st.floats(min_value=0.0, max_value=24.0))),
        main_problem=draw(st.one_of(st.none(), st.text(max_size=80))),
        mistake_pattern=draw(st.one_of(st.none(), st.text(max_size=80))),
        learning_style=draw(st.one_of(st.none(), st.sampled_from(list(LearningStyle)))),
        created_at=now,
        updated_at=now,
    )


@given(_profiles())
def test_classifier_is_total(profile: StudentProfile) -> None:
    result = classify_archetype(profile)
    assert isinstance(result, Archetype)
