"""Profile read + bulk-upsert endpoints.

Bulk upsert is the simple onboarding API: the frontend collects answers from
hardcoded questions, packages them as profile fields, POSTs them once, and we
persist the profile + classify archetype in one shot. No question-bank DB
involved.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from neetai_api.container import Container
from neetai_api.deps import get_container
from neetai_api.routers.onboarding import ProfileSummary
from neetai_core.errors import NotFoundError
from neetai_core.ids import StudentId
from neetai_core.profile import StudentProfile
from neetai_core.types import (
    ClassLevel,
    ExamTarget,
    Language,
    LearningStyle,
    Subject,
)
from neetai_ports import ProfileRepository, Student, StudentRepository
from neetai_profiling.archetype import classify_archetype

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


def get_profile_repo(
    container: Annotated[Container, Depends(get_container)],
) -> ProfileRepository:
    return container.profiles


def get_student_repo(
    container: Annotated[Container, Depends(get_container)],
) -> StudentRepository:
    return container.students


ProfileRepoDep = Annotated[ProfileRepository, Depends(get_profile_repo)]
StudentRepoDep = Annotated[StudentRepository, Depends(get_student_repo)]


class ProfileUpsertRequest(BaseModel):
    """Whole-profile patch sent by the frontend onboarding flow.

    Only `student_id`, `class_level`, and `exam_target` are required. The rest
    are optional so the same endpoint handles "I've answered everything" and
    "I've only answered a few questions so far".
    """

    model_config = ConfigDict(extra="forbid")

    student_id: StudentId = Field(min_length=1, max_length=64)
    class_level: ClassLevel
    exam_target: ExamTarget
    language: Language = Language.ENGLISH

    weak_subject: Subject | None = None
    strong_subject: Subject | None = None
    learning_style: LearningStyle | None = None

    mock_score_range: str | None = Field(default=None, max_length=32)
    main_problem: str | None = Field(default=None, max_length=120)
    mistake_pattern: str | None = Field(default=None, max_length=120)
    emotional_state: str | None = Field(default=None, max_length=64)
    revision_habit: str | None = Field(default=None, max_length=64)
    study_hours_per_day: float | None = Field(default=None, ge=0, le=24)

    display_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=254)


@router.get(
    "/{student_id}",
    response_model=ProfileSummary,
    summary="Fetch a student's current profile snapshot.",
)
async def get_profile(
    student_id: StudentId,
    profiles: ProfileRepoDep,
) -> ProfileSummary:
    profile = await profiles.get(student_id)
    if profile is None:
        raise NotFoundError(f"No profile for student {student_id}")
    return ProfileSummary.from_domain(profile)


@router.post(
    "/upsert",
    response_model=ProfileSummary,
    summary="Create or update a student's profile in one call.",
)
async def upsert_profile(
    body: ProfileUpsertRequest,
    profiles: ProfileRepoDep,
    students: StudentRepoDep,
) -> ProfileSummary:
    now = datetime.now(UTC)

    if (await students.get(body.student_id)) is None:
        await students.upsert(
            Student(
                student_id=body.student_id,
                email=body.email,
                display_name=body.display_name,
                created_at=now,
                last_active_at=now,
            ),
        )

    existing = await profiles.get(body.student_id)
    base = existing or StudentProfile(
        student_id=body.student_id,
        class_level=body.class_level,
        exam_target=body.exam_target,
        language=body.language,
        created_at=now,
        updated_at=now,
    )

    updates: dict[str, object] = {
        "class_level": body.class_level,
        "exam_target": body.exam_target,
        "language": body.language,
        "updated_at": now,
    }
    for field in (
        "weak_subject",
        "strong_subject",
        "learning_style",
        "mock_score_range",
        "main_problem",
        "mistake_pattern",
        "emotional_state",
        "revision_habit",
        "study_hours_per_day",
    ):
        value = getattr(body, field)
        if value is not None:
            updates[field] = value

    filled_fields = sum(
        1 for key in updates if key not in {"class_level", "exam_target", "language", "updated_at"}
    )
    if not existing:
        updates["profile_confidence"] = min(1.0, 0.1 * filled_fields)
    else:
        updates["profile_confidence"] = min(
            1.0,
            max(base.profile_confidence, 0.1 * filled_fields),
        )

    updated = base.model_copy(update=updates)
    updated = updated.model_copy(update={"archetype": classify_archetype(updated)})
    saved = await profiles.save(updated)
    return ProfileSummary.from_domain(saved)
