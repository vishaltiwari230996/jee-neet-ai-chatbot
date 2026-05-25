"""End-to-end onboarding flow against the in-memory adapters.

This test is the closest Phase-1 gets to a real user journey. It proves
that selector + mapper + archetype + repositories cohere correctly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from neetai_core.errors import NotFoundError, ValidationError
from neetai_core.ids import QuestionId, StudentId
from neetai_core.types import Archetype, ClassLevel, ExamTarget
from neetai_db_fake import (
    InMemoryAskedQuestionRepository,
    InMemoryProfileRepository,
    InMemoryQuestionBankRepository,
    InMemoryStudentRepository,
)
from neetai_ports import BankQuestion
from neetai_profiling import OnboardingService
from neetai_question_bank import load_questions_from_csv


def _csv_path() -> Path:
    return Path(__file__).resolve().parents[3] / "infra" / "data" / "onboarding_questions.csv"


def _domain_to_bank(q: object) -> BankQuestion:
    # Convert the typed Question (from CSV) into the persistence-facing shape
    # the repositories expect. This is the same translation the production
    # CSV ingestion CLI will perform.
    return BankQuestion(
        question_id=QuestionId(str(q.question_id)),  # type: ignore[attr-defined]
        text=q.text,  # type: ignore[attr-defined]
        category=str(q.category),  # type: ignore[attr-defined]
        exam_targets=[str(target) for target in q.exam_targets],  # type: ignore[attr-defined]
        audience=[str(a) for a in q.audience],  # type: ignore[attr-defined]
        answer_type=str(q.answer_type),  # type: ignore[attr-defined]
        options=list(q.options),  # type: ignore[attr-defined]
        maps_to=q.maps_to,  # type: ignore[attr-defined]
        priority=q.priority,  # type: ignore[attr-defined]
        is_required=q.is_required,  # type: ignore[attr-defined]
        is_active=True,
    )


@pytest.fixture
async def service() -> OnboardingService:
    bank_repo = InMemoryQuestionBankRepository()
    questions = load_questions_from_csv(_csv_path())
    await bank_repo.upsert_many([_domain_to_bank(q) for q in questions])
    return OnboardingService(
        students=InMemoryStudentRepository(),
        profiles=InMemoryProfileRepository(),
        questions=bank_repo,
        asked=InMemoryAskedQuestionRepository(),
    )


async def test_start_emits_first_diagnostic_question(service: OnboardingService) -> None:
    state = await service.start_onboarding(
        student_id=StudentId("stu_1"),
        class_level=ClassLevel.DROPPER,
        exam_target=ExamTarget.JEE_MAIN_ADVANCED,
        display_name="Anaya",
    )
    assert state.status == "in_progress"
    assert state.next_question is not None
    # Highest-priority JEE diagnostic from the shipped CSV.
    assert state.next_question.question_id == "JEE_MOCK_SCORE"


async def test_resuming_returns_same_first_question(service: OnboardingService) -> None:
    first = await service.start_onboarding(
        student_id=StudentId("stu_2"),
        class_level=ClassLevel.CLASS_12,
        exam_target=ExamTarget.JEE_MAIN,
    )
    second = await service.start_onboarding(
        student_id=StudentId("stu_2"),
        class_level=ClassLevel.CLASS_12,
        exam_target=ExamTarget.JEE_MAIN,
    )
    assert first.next_question is not None
    assert second.next_question is not None
    assert first.next_question.question_id == second.next_question.question_id


async def test_submit_answer_advances_to_next_question(
    service: OnboardingService,
) -> None:
    sid = StudentId("stu_3")
    state = await service.start_onboarding(
        student_id=sid,
        class_level=ClassLevel.DROPPER,
        exam_target=ExamTarget.JEE_MAIN_ADVANCED,
    )
    assert state.next_question is not None
    assert state.next_question.maps_to == "mock_score_range"

    advanced = await service.submit_answer(
        student_id=sid,
        question_id=state.next_question.question_id,
        raw_answer="120-160",
    )
    assert advanced.profile.mock_score_range == "120-160"
    assert advanced.profile.profile_confidence == pytest.approx(0.1)
    assert advanced.next_question is not None
    assert advanced.next_question.question_id != state.next_question.question_id


async def test_full_walkthrough_yields_complete_state(
    service: OnboardingService,
) -> None:
    """Drive the flow to completion answering every question with a valid
    option until the selector returns None."""
    sid = StudentId("stu_walk")
    state = await service.start_onboarding(
        student_id=sid,
        class_level=ClassLevel.DROPPER,
        exam_target=ExamTarget.JEE_MAIN_ADVANCED,
    )

    while state.next_question is not None:
        answer = _plausible_answer_for(state.next_question)
        state = await service.submit_answer(
            student_id=sid,
            question_id=state.next_question.question_id,
            raw_answer=answer,
        )

    assert state.status == "complete"
    assert state.profile.weak_subject is not None
    assert state.profile.main_problem is not None
    assert state.profile.learning_style is not None
    # Archetype gets re-classified each step; final value should not be UNCLASSIFIED.
    assert state.profile.archetype is not Archetype.UNCLASSIFIED


async def test_submit_answer_for_unknown_student_raises(
    service: OnboardingService,
) -> None:
    with pytest.raises(NotFoundError):
        await service.submit_answer(
            student_id=StudentId("stu_does_not_exist"),
            question_id=QuestionId("Q001"),
            raw_answer="physics",
        )


async def test_submit_answer_rejects_option_outside_choices(
    service: OnboardingService,
) -> None:
    sid = StudentId("stu_bad_choice")
    state = await service.start_onboarding(
        student_id=sid,
        class_level=ClassLevel.DROPPER,
        exam_target=ExamTarget.JEE_MAIN_ADVANCED,
    )
    assert state.next_question is not None
    # First question is short-text; answer it to reach a choice question.
    state = await service.submit_answer(
        student_id=sid,
        question_id=state.next_question.question_id,
        raw_answer="120-160",
    )
    assert state.next_question is not None
    with pytest.raises(ValidationError):
        await service.submit_answer(
            student_id=sid,
            question_id=state.next_question.question_id,
            raw_answer="not a valid option",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _plausible_answer_for(question: object) -> str:
    """Pick a deterministic-but-valid answer for any question shape."""
    answer_type = str(question.answer_type)  # type: ignore[attr-defined]
    options = list(question.options)  # type: ignore[attr-defined]
    maps_to = question.maps_to  # type: ignore[attr-defined]

    if answer_type in {"single_choice", "multi_choice"} and options:
        return options[0]
    if answer_type == "number":
        if maps_to == "study_hours_per_day":
            return "6"
        if maps_to == "target_rank":
            return "5000"
        return "1"
    return "placeholder"
