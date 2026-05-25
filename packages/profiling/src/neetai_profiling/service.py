"""OnboardingService — the orchestration layer for student onboarding.

This is *not* the answer pipeline (that's Phase 3). It is the small,
focused workflow that takes a brand-new student through diagnostic
questions until their profile is ready for the chat system.

Single responsibility, deliberately:

    start_onboarding(student_id, class_level, exam_target)
        → ensure student + initial profile exist
        → emit the first diagnostic question

    submit_answer(student_id, question_id, raw_answer)
        → validate + map answer → updated profile
        → re-classify archetype
        → persist
        → emit the next question, or COMPLETE if onboarding is done

The service depends only on repository Protocols and pure functions. It
contains no SQL, no LLM, no HTTP. Tests can wire `InMemory*` adapters and
exercise the whole flow in microseconds.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from neetai_core.errors import NotFoundError, ValidationError
from neetai_core.ids import QuestionId, StudentId
from neetai_core.profile import StudentProfile
from neetai_core.types import ClassLevel, ExamTarget, Language
from neetai_ports import (
    AskedQuestionRepository,
    BankQuestion,
    ProfileRepository,
    QuestionBankRepository,
    Student,
    StudentRepository,
)
from neetai_profiling.archetype import classify_archetype
from neetai_profiling.mapper import apply_answer
from neetai_question_bank import (
    Question,
    QuestionCategory,
    select_next_question,
)
from neetai_question_bank.models import AnswerType

# ---------------------------------------------------------------------------
# Onboarding state value object (what we return to the API)
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class OnboardingState:
    """Snapshot of where the student is in the onboarding flow."""

    student_id: StudentId
    profile: StudentProfile
    next_question: Question | None
    status: Literal["in_progress", "complete"]

    @classmethod
    def from_parts(
        cls,
        *,
        profile: StudentProfile,
        next_question: Question | None,
    ) -> OnboardingState:
        return cls(
            student_id=profile.student_id,
            profile=profile,
            next_question=next_question,
            status="complete" if next_question is None else "in_progress",
        )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class OnboardingService:
    def __init__(
        self,
        *,
        students: StudentRepository,
        profiles: ProfileRepository,
        questions: QuestionBankRepository,
        asked: AskedQuestionRepository,
    ) -> None:
        self._students = students
        self._profiles = profiles
        self._questions = questions
        self._asked = asked

    async def start_onboarding(
        self,
        *,
        student_id: StudentId,
        class_level: ClassLevel,
        exam_target: ExamTarget,
        language: Language = Language.ENGLISH,
        display_name: str | None = None,
        email: str | None = None,
    ) -> OnboardingState:
        """Idempotent: re-calling for the same student resumes where they left off."""
        now = datetime.now(UTC)

        existing_student = await self._students.get(student_id)
        if existing_student is None:
            await self._students.upsert(
                Student(
                    student_id=student_id,
                    email=email,
                    display_name=display_name,
                    created_at=now,
                    last_active_at=now,
                ),
            )

        profile = await self._profiles.get(student_id)
        if profile is None:
            profile = StudentProfile(
                student_id=student_id,
                class_level=class_level,
                exam_target=exam_target,
                language=language,
                created_at=now,
                updated_at=now,
            )
            await self._profiles.save(profile)

        next_question = await self._pick_and_mark_next(profile)
        return OnboardingState.from_parts(profile=profile, next_question=next_question)

    async def submit_answer(
        self,
        *,
        student_id: StudentId,
        question_id: QuestionId,
        raw_answer: str,
    ) -> OnboardingState:
        profile = await self._profiles.get(student_id)
        if profile is None:
            raise NotFoundError(f"No profile for student {student_id}")

        question = await self._fetch_question(question_id)
        _validate_answer_shape(question, raw_answer)

        await self._asked.record_answer(
            student_id=student_id,
            question_id=question_id,
            raw_answer=raw_answer,
        )

        updated = apply_answer(
            profile,
            field_name=question.maps_to,
            raw_answer=raw_answer,
        )
        updated = updated.model_copy(update={"archetype": classify_archetype(updated)})
        updated = await self._profiles.save(updated)

        next_question = await self._pick_and_mark_next(updated)
        return OnboardingState.from_parts(profile=updated, next_question=next_question)

    async def get_state(self, student_id: StudentId) -> OnboardingState:
        profile = await self._profiles.get(student_id)
        if profile is None:
            raise NotFoundError(f"No profile for student {student_id}")
        next_question = await self._pick_and_mark_next(profile, record_asked=False)
        return OnboardingState.from_parts(profile=profile, next_question=next_question)

    # ------------------------------------------------------------------ helpers

    async def _pick_and_mark_next(
        self,
        profile: StudentProfile,
        *,
        record_asked: bool = True,
    ) -> Question | None:
        bank = await self._questions.list_active()
        domain_questions = [_bank_to_domain(q) for q in bank]
        asked = await self._asked.list_answered_question_ids(profile.student_id)

        question = select_next_question(
            profile=profile,
            asked_question_ids=asked,
            available_questions=domain_questions,
        )
        if question is None:
            return None
        if record_asked:
            await self._asked.record_asked(
                student_id=profile.student_id,
                question_id=question.question_id,
            )
        return question

    async def _fetch_question(self, question_id: QuestionId) -> Question:
        bank = await self._questions.list_active()
        for q in bank:
            if q.question_id == question_id:
                return _bank_to_domain(q)
        raise NotFoundError(f"Unknown question_id {question_id}")


# ---------------------------------------------------------------------------
# Bank ↔ domain conversion
#
# The persistence side carries `BankQuestion` (flat strings); the selector
# and mapper expect the typed `Question` from `neetai_question_bank`.
# ---------------------------------------------------------------------------


def _bank_to_domain(q: BankQuestion) -> Question:
    return Question(
        question_id=q.question_id,
        text=q.text,
        category=QuestionCategory(q.category),
        exam_targets=frozenset(ExamTarget(target) for target in q.exam_targets),
        audience=frozenset(ClassLevel(a) for a in q.audience),
        answer_type=AnswerType(q.answer_type),
        options=tuple(q.options),
        maps_to=q.maps_to,
        priority=q.priority,
        is_required=q.is_required,
    )


def _validate_answer_shape(question: Question, raw_answer: str) -> None:
    cleaned = raw_answer.strip()
    if not cleaned:
        raise ValidationError("answer cannot be empty")
    if (
        question.answer_type is AnswerType.SINGLE_CHOICE
        and question.options
        and cleaned not in question.options
    ):
        raise ValidationError(
            f"answer '{cleaned}' not in allowed options for {question.question_id}",
        )
