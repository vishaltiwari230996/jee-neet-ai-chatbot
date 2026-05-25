"""Profile read endpoint.

Read-only view of the student's current profile. Kept separate from the
onboarding router because read patterns and write patterns diverge fast
(caching, projections, denormalizations) — co-locating now causes pain
later.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from neetai_api.container import Container
from neetai_api.deps import get_container
from neetai_api.routers.onboarding import ProfileSummary
from neetai_core.errors import NotFoundError
from neetai_core.ids import StudentId
from neetai_ports import ProfileRepository

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


def get_profile_repo(
    container: Annotated[Container, Depends(get_container)],
) -> ProfileRepository:
    return container.profiles


ProfileRepoDep = Annotated[ProfileRepository, Depends(get_profile_repo)]


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
