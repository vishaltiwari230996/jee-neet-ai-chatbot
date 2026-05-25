"""Shared fixtures for orchestrator tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from neetai_core.ids import StudentId
from neetai_core.profile import StudentProfile
from neetai_core.types import Archetype, ClassLevel, ExamTarget


def _make_profile(**overrides: Any) -> StudentProfile:
    now = datetime.now(UTC)
    base: dict[str, Any] = {
        "student_id": StudentId("stu_test"),
        "class_level": ClassLevel.CLASS_12,
        "exam_target": ExamTarget.JEE_MAIN_ADVANCED,
        "archetype": Archetype.STRONG_CONCEPTS_POOR_EXECUTION,
        "profile_confidence": 0.8,
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return StudentProfile.model_validate(base)


@pytest.fixture
def make_profile() -> Callable[..., StudentProfile]:
    return _make_profile
