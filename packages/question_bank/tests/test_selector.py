"""Selector tests = selection-rule specification.

If a rule changes, a test here must change. That is the point — the rules
are the product, not the implementation.
"""

from __future__ import annotations

from neetai_core.ids import QuestionId
from neetai_core.types import ClassLevel, LearningStyle, Subject
from neetai_question_bank.selector import select_next_question

from .conftest import ProfileFactory, QuestionFactory


def test_returns_none_when_no_questions_available(make_profile: ProfileFactory) -> None:
    assert (
        select_next_question(
            profile=make_profile(),
            asked_question_ids=[],
            available_questions=[],
        )
        is None
    )


def test_returns_none_when_profile_already_complete(
    make_profile: ProfileFactory,
    make_question: QuestionFactory,
) -> None:
    profile = make_profile(weak_subject=Subject.PHYSICS)
    question = make_question("Q1", maps_to="weak_subject")
    assert (
        select_next_question(
            profile=profile,
            asked_question_ids=[],
            available_questions=[question],
        )
        is None
    )


def test_skips_questions_already_asked(
    make_profile: ProfileFactory,
    make_question: QuestionFactory,
) -> None:
    q1 = make_question("Q1", maps_to="weak_subject", priority=90)
    q2 = make_question("Q2", maps_to="main_problem", priority=10)
    result = select_next_question(
        profile=make_profile(),
        asked_question_ids=[QuestionId("Q1")],
        available_questions=[q1, q2],
    )
    assert result is not None
    assert result.question_id == "Q2"


def test_picks_highest_priority(
    make_profile: ProfileFactory,
    make_question: QuestionFactory,
) -> None:
    low = make_question("Q_low", maps_to="weak_subject", priority=10)
    high = make_question("Q_high", maps_to="main_problem", priority=90)
    result = select_next_question(
        profile=make_profile(),
        asked_question_ids=[],
        available_questions=[low, high],
    )
    assert result is not None
    assert result.question_id == "Q_high"


def test_priority_ties_broken_deterministically_by_id(
    make_profile: ProfileFactory,
    make_question: QuestionFactory,
) -> None:
    qa = make_question("Q_a", maps_to="weak_subject", priority=50)
    qb = make_question("Q_b", maps_to="main_problem", priority=50)
    qc = make_question("Q_c", maps_to="learning_style", priority=50)

    # Order of the input must not affect the result.
    result_one = select_next_question(
        profile=make_profile(),
        asked_question_ids=[],
        available_questions=[qc, qa, qb],
    )
    result_two = select_next_question(
        profile=make_profile(),
        asked_question_ids=[],
        available_questions=[qb, qa, qc],
    )
    assert result_one is not None
    assert result_two is not None
    assert result_one.question_id == "Q_a"
    assert result_two.question_id == "Q_a"


def test_audience_filter_excludes_irrelevant_questions(
    make_profile: ProfileFactory,
    make_question: QuestionFactory,
) -> None:
    profile = make_profile(class_level=ClassLevel.CLASS_11)
    dropper_only = make_question(
        "Q1",
        maps_to="weak_subject",
        priority=99,
        audience=(ClassLevel.DROPPER,),
    )
    universal = make_question("Q2", maps_to="main_problem", priority=10)
    result = select_next_question(
        profile=profile,
        asked_question_ids=[],
        available_questions=[dropper_only, universal],
    )
    assert result is not None
    assert result.question_id == "Q2"


def test_skips_question_when_target_field_already_filled(
    make_profile: ProfileFactory,
    make_question: QuestionFactory,
) -> None:
    profile = make_profile(learning_style=LearningStyle.STEP_BY_STEP)
    redundant = make_question("Q1", maps_to="learning_style", priority=99)
    fresh = make_question("Q2", maps_to="weak_subject", priority=1)
    result = select_next_question(
        profile=profile,
        asked_question_ids=[],
        available_questions=[redundant, fresh],
    )
    assert result is not None
    assert result.question_id == "Q2"
