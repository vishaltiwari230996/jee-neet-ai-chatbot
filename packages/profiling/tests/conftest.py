"""Shared fixtures for profiling tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from neetai_core.ids import StudentId
from neetai_core.profile import StudentProfile
from neetai_core.types import ClassLevel, ExamTarget

ProfileFactory = Callable[..., StudentProfile]


def _make_profile(**overrides: Any) -> StudentProfile:
    now = datetime.now(UTC)
    base: dict[str, Any] = {
        "student_id": StudentId("stu_test"),
        "class_level": ClassLevel.DROPPER,
        "exam_target": ExamTarget.JEE_MAIN_ADVANCED,
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return StudentProfile.model_validate(base)


@pytest.fixture
def make_profile() -> ProfileFactory:
    return _make_profile
