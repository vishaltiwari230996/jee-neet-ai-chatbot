"""Shared fixtures for question-bank tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from neetai_core.ids import QuestionId, StudentId
from neetai_core.profile import StudentProfile
from neetai_core.types import ClassLevel, ExamTarget
from neetai_question_bank.models import (
    AnswerType,
    Question,
    QuestionCategory,
)

ProfileFactory = Callable[..., StudentProfile]
QuestionFactory = Callable[..., Question]


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


def _make_question(
    qid: str,
    *,
    maps_to: str,
    priority: int = 50,
    audience: tuple[ClassLevel, ...] = (
        ClassLevel.CLASS_11,
        ClassLevel.CLASS_12,
        ClassLevel.DROPPER,
    ),
) -> Question:
    return Question(
        question_id=QuestionId(qid),
        text=f"placeholder for {qid}",
        category=QuestionCategory.ACADEMIC_DIAGNOSIS,
        exam_targets=frozenset(ExamTarget),
        audience=frozenset(audience),
        answer_type=AnswerType.SINGLE_CHOICE,
        options=("A", "B"),
        maps_to=maps_to,
        priority=priority,
    )


@pytest.fixture
def make_profile() -> ProfileFactory:
    return _make_profile


@pytest.fixture
def make_question() -> QuestionFactory:
    return _make_question
