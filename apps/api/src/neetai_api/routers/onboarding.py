"""Onboarding HTTP routes.

These map HTTP <-> `OnboardingService` calls and nothing else. All flow
logic lives in `neetai_profiling.service`; routers only translate.

Request/response models are local to the router (the API's *wire schema* is
versioned independently of the domain). The mapping is intentionally
explicit — when the domain `StudentProfile` gains a field, we get a typed
mypy error here forcing us to decide whether to expose it. Silent leakage
of internal fields into the public API is exactly the kind of accident
this layer is supposed to prevent.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from neetai_api.container import Container
from neetai_api.deps import get_container
from neetai_core.ids import QuestionId, StudentId
from neetai_core.profile import StudentProfile
from neetai_core.types import ClassLevel, ExamTarget, Language
from neetai_profiling.service import OnboardingService, OnboardingState
from neetai_question_bank.models import Question

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


# ---------------------------------------------------------------------------
# Wire schemas
# ---------------------------------------------------------------------------


class StartOnboardingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: StudentId = Field(min_length=1, max_length=64)
    class_level: ClassLevel
    exam_target: ExamTarget
    language: Language = Language.ENGLISH
    display_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=254)


class SubmitAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: StudentId = Field(min_length=1, max_length=64)
    question_id: QuestionId = Field(min_length=1, max_length=32)
    raw_answer: str = Field(min_length=1, max_length=500)


class QuestionPayload(BaseModel):
    question_id: QuestionId
    text: str
    category: str
    answer_type: str
    options: tuple[str, ...]

    @classmethod
    def from_domain(cls, q: Question) -> QuestionPayload:
        return cls(
            question_id=q.question_id,
            text=q.text,
            category=q.category.value,
            answer_type=q.answer_type.value,
            options=q.options,
        )


class ProfileSummary(BaseModel):
    """Public view of a profile.

    Deliberately a subset of `StudentProfile` — we don't reflect raw rows
    over the wire. New domain fields don't become public by accident.
    """

    student_id: StudentId
    class_level: str
    exam_target: str
    language: str
    weak_subject: str | None
    strong_subject: str | None
    main_problem: str | None
    learning_style: str | None
    archetype: str
    profile_confidence: float
    missing_critical_fields: list[str]

    @classmethod
    def from_domain(cls, p: StudentProfile) -> ProfileSummary:
        return cls(
            student_id=p.student_id,
            class_level=p.class_level.value,
            exam_target=p.exam_target.value,
            language=p.language.value,
            weak_subject=p.weak_subject.value if p.weak_subject else None,
            strong_subject=p.strong_subject.value if p.strong_subject else None,
            main_problem=p.main_problem,
            learning_style=p.learning_style.value if p.learning_style else None,
            archetype=p.archetype.value,
            profile_confidence=p.profile_confidence,
            missing_critical_fields=p.missing_critical_fields(),
        )


class OnboardingStateResponse(BaseModel):
    status: Literal["in_progress", "complete"]
    profile: ProfileSummary
    next_question: QuestionPayload | None

    @classmethod
    def from_state(cls, state: OnboardingState) -> OnboardingStateResponse:
        return cls(
            status=state.status,
            profile=ProfileSummary.from_domain(state.profile),
            next_question=(
                QuestionPayload.from_domain(state.next_question)
                if state.next_question is not None
                else None
            ),
        )


# ---------------------------------------------------------------------------
# Dependency wiring
# ---------------------------------------------------------------------------


def get_onboarding_service(
    container: Annotated[Container, Depends(get_container)],
) -> OnboardingService:
    return container.onboarding


OnboardingDep = Annotated[OnboardingService, Depends(get_onboarding_service)]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/start",
    response_model=OnboardingStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Start (or resume) the onboarding flow for a student.",
)
async def start_onboarding(
    body: StartOnboardingRequest,
    onboarding: OnboardingDep,
) -> OnboardingStateResponse:
    state = await onboarding.start_onboarding(
        student_id=body.student_id,
        class_level=body.class_level,
        exam_target=body.exam_target,
        language=body.language,
        display_name=body.display_name,
        email=body.email,
    )
    return OnboardingStateResponse.from_state(state)


@router.post(
    "/answer",
    response_model=OnboardingStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a student's answer to the current diagnostic question.",
)
async def submit_answer(
    body: SubmitAnswerRequest,
    onboarding: OnboardingDep,
) -> OnboardingStateResponse:
    state = await onboarding.submit_answer(
        student_id=body.student_id,
        question_id=body.question_id,
        raw_answer=body.raw_answer,
    )
    return OnboardingStateResponse.from_state(state)


@router.get(
    "/state/{student_id}",
    response_model=OnboardingStateResponse,
    summary="Return current onboarding state without mutating anything.",
)
async def get_state(
    student_id: StudentId,
    onboarding: OnboardingDep,
) -> OnboardingStateResponse:
    state = await onboarding.get_state(student_id)
    return OnboardingStateResponse.from_state(state)
