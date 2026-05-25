"""ORM ↔ domain translation.

Two-way mapping. Domain objects never carry SQLAlchemy state; ORM rows
never carry pydantic validators. This file is the only place either gets
to see the other.
"""

from __future__ import annotations

from neetai_core.ids import QuestionId, StudentId
from neetai_core.profile import StudentProfile
from neetai_core.types import (
    Archetype,
    ClassLevel,
    ExamTarget,
    Language,
    LearningStyle,
    Subject,
)
from neetai_db_postgres.models import (
    ProfileRow,
    QuestionRow,
    StudentRow,
)
from neetai_ports import BankQuestion, Student

# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------


def student_to_row(student: Student) -> StudentRow:
    return StudentRow(
        student_id=str(student.student_id),
        email=student.email,
        display_name=student.display_name,
    )


def student_from_row(row: StudentRow) -> Student:
    return Student(
        student_id=StudentId(row.student_id),
        email=row.email,
        display_name=row.display_name,
        created_at=row.created_at,
        last_active_at=row.last_active_at,
    )


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


def profile_to_row(profile: StudentProfile) -> ProfileRow:
    return ProfileRow(
        student_id=str(profile.student_id),
        class_level=str(profile.class_level),
        exam_target=str(profile.exam_target),
        language=str(profile.language),
        weak_subject=str(profile.weak_subject) if profile.weak_subject else None,
        strong_subject=str(profile.strong_subject) if profile.strong_subject else None,
        mock_score_range=profile.mock_score_range,
        target_rank=profile.target_rank,
        study_hours_per_day=profile.study_hours_per_day,
        revision_habit=profile.revision_habit,
        main_problem=profile.main_problem,
        mistake_pattern=profile.mistake_pattern,
        emotional_state=profile.emotional_state,
        learning_style=str(profile.learning_style) if profile.learning_style else None,
        archetype=str(profile.archetype),
        archetype_version=profile.archetype_version,
        profile_confidence=profile.profile_confidence,
    )


def profile_from_row(row: ProfileRow) -> StudentProfile:
    return StudentProfile(
        student_id=StudentId(row.student_id),
        class_level=ClassLevel(row.class_level),
        exam_target=ExamTarget(row.exam_target),
        language=Language(row.language),
        weak_subject=Subject(row.weak_subject) if row.weak_subject else None,
        strong_subject=Subject(row.strong_subject) if row.strong_subject else None,
        mock_score_range=row.mock_score_range,
        target_rank=row.target_rank,
        study_hours_per_day=row.study_hours_per_day,
        revision_habit=row.revision_habit,
        main_problem=row.main_problem,
        mistake_pattern=row.mistake_pattern,
        emotional_state=row.emotional_state,
        learning_style=LearningStyle(row.learning_style) if row.learning_style else None,
        archetype=Archetype(row.archetype),
        archetype_version=row.archetype_version,
        profile_confidence=row.profile_confidence,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------


def question_to_row(q: BankQuestion) -> QuestionRow:
    return QuestionRow(
        question_id=str(q.question_id),
        text=q.text,
        category=q.category,
        exam_targets=list(q.exam_targets),
        audience=list(q.audience),
        answer_type=q.answer_type,
        options=list(q.options),
        maps_to=q.maps_to,
        priority=q.priority,
        is_required=q.is_required,
        is_active=q.is_active,
    )


def question_from_row(row: QuestionRow) -> BankQuestion:
    return BankQuestion(
        question_id=QuestionId(row.question_id),
        text=row.text,
        category=row.category,
        exam_targets=list(row.exam_targets),
        audience=list(row.audience),
        answer_type=row.answer_type,
        options=list(row.options),
        maps_to=row.maps_to,
        priority=row.priority,
        is_required=row.is_required,
        is_active=row.is_active,
    )
