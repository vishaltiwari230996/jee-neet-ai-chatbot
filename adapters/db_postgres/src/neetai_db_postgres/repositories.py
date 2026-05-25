"""Postgres repository implementations.

Design choices worth flagging:

* Repositories take a `SessionFactory` and open a fresh session per call.
  This keeps the public API simple at the cost of one connection acquisition
  per call. When that becomes hot we'll add a session-per-request pattern
  via FastAPI dependency injection. Until then, simplicity wins.

* Upserts use Postgres's native `INSERT ... ON CONFLICT DO UPDATE` via
  SQLAlchemy's `postgresql.insert`. This makes the CSV ingestion CLI
  genuinely idempotent (re-running it produces the same DB state).

* Repositories raise `neetai_core` errors, never SQLAlchemy errors. The
  domain code never knows it's talking to Postgres.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from neetai_core.ids import QuestionId, StudentId
from neetai_core.profile import StudentProfile
from neetai_db_postgres.mappers import (
    profile_from_row,
    profile_to_row,
    question_from_row,
    question_to_row,
    student_from_row,
)
from neetai_db_postgres.models import (
    AskedQuestionRow,
    ProfileRow,
    QuestionRow,
    StudentRow,
)
from neetai_db_postgres.session import SessionFactory
from neetai_ports import (
    AskedQuestion,
    BankQuestion,
    Student,
)

# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------


class PgStudentRepository:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def get(self, student_id: StudentId) -> Student | None:
        async with self._sessions.session() as s:
            row = await s.get(StudentRow, str(student_id))
            return student_from_row(row) if row else None

    async def upsert(self, student: Student) -> Student:
        async with self._sessions.session() as s:
            stmt = pg_insert(StudentRow).values(
                student_id=str(student.student_id),
                email=student.email,
                display_name=student.display_name,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[StudentRow.student_id],
                set_={
                    "email": stmt.excluded.email,
                    "display_name": stmt.excluded.display_name,
                    "last_active_at": datetime.now(UTC),
                },
            )
            await s.execute(stmt)
            # Re-read to capture server-side timestamps.
            row = await s.get(StudentRow, str(student.student_id))
            assert row is not None  # we just inserted
            return student_from_row(row)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


class PgProfileRepository:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def get(self, student_id: StudentId) -> StudentProfile | None:
        async with self._sessions.session() as s:
            row = await s.get(ProfileRow, str(student_id))
            return profile_from_row(row) if row else None

    async def save(self, profile: StudentProfile) -> StudentProfile:
        async with self._sessions.session() as s:
            row = profile_to_row(profile)
            stmt = pg_insert(ProfileRow).values(_row_to_insert_values(row))
            stmt = stmt.on_conflict_do_update(
                index_elements=[ProfileRow.student_id],
                set_={k: v for k, v in _row_to_insert_values(row).items() if k != "student_id"},
            )
            await s.execute(stmt)
            reloaded = await s.get(ProfileRow, str(profile.student_id))
            assert reloaded is not None
            return profile_from_row(reloaded)


def _row_to_insert_values(row: ProfileRow) -> dict[str, object]:
    """Pull insert values off the ORM dataclass-style row.

    We avoid `row.__dict__` because SQLAlchemy adds private attributes that
    don't belong in the INSERT — listing fields explicitly keeps surprises
    out.
    """
    return {
        "student_id": row.student_id,
        "class_level": row.class_level,
        "exam_target": row.exam_target,
        "language": row.language,
        "weak_subject": row.weak_subject,
        "strong_subject": row.strong_subject,
        "mock_score_range": row.mock_score_range,
        "target_rank": row.target_rank,
        "study_hours_per_day": row.study_hours_per_day,
        "revision_habit": row.revision_habit,
        "main_problem": row.main_problem,
        "mistake_pattern": row.mistake_pattern,
        "emotional_state": row.emotional_state,
        "learning_style": row.learning_style,
        "archetype": row.archetype,
        "archetype_version": row.archetype_version,
        "profile_confidence": row.profile_confidence,
    }


# ---------------------------------------------------------------------------
# Question bank
# ---------------------------------------------------------------------------


class PgQuestionBankRepository:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def list_active(self) -> list[BankQuestion]:
        async with self._sessions.session() as s:
            result = await s.scalars(
                select(QuestionRow)
                .where(QuestionRow.is_active.is_(True))
                .order_by(QuestionRow.priority.desc(), QuestionRow.question_id),
            )
            return [question_from_row(row) for row in result.all()]

    async def upsert_many(self, questions: list[BankQuestion]) -> int:
        if not questions:
            return 0
        async with self._sessions.session() as s:
            for q in questions:
                row = question_to_row(q)
                stmt = pg_insert(QuestionRow).values(
                    question_id=row.question_id,
                    text=row.text,
                    category=row.category,
                    exam_targets=row.exam_targets,
                    audience=row.audience,
                    answer_type=row.answer_type,
                    options=row.options,
                    maps_to=row.maps_to,
                    priority=row.priority,
                    is_required=row.is_required,
                    is_active=row.is_active,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=[QuestionRow.question_id],
                    set_={
                        "text": stmt.excluded.text,
                        "category": stmt.excluded.category,
                        "exam_targets": stmt.excluded.exam_targets,
                        "audience": stmt.excluded.audience,
                        "answer_type": stmt.excluded.answer_type,
                        "options": stmt.excluded.options,
                        "maps_to": stmt.excluded.maps_to,
                        "priority": stmt.excluded.priority,
                        "is_required": stmt.excluded.is_required,
                        "is_active": stmt.excluded.is_active,
                    },
                )
                await s.execute(stmt)
            return len(questions)


# ---------------------------------------------------------------------------
# Asked questions
# ---------------------------------------------------------------------------


class PgAskedQuestionRepository:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def list_answered_question_ids(self, student_id: StudentId) -> list[QuestionId]:
        async with self._sessions.session() as s:
            result = await s.scalars(
                select(AskedQuestionRow.question_id).where(
                    AskedQuestionRow.student_id == str(student_id),
                    AskedQuestionRow.answered_at.is_not(None),
                ),
            )
            return [QuestionId(qid) for qid in result.all()]

    async def list_answered(self, student_id: StudentId) -> list[AskedQuestion]:
        async with self._sessions.session() as s:
            result = await s.scalars(
                select(AskedQuestionRow)
                .where(
                    AskedQuestionRow.student_id == str(student_id),
                    AskedQuestionRow.answered_at.is_not(None),
                )
                .order_by(AskedQuestionRow.answered_at, AskedQuestionRow.question_id),
            )
            return [
                AskedQuestion(
                    student_id=StudentId(row.student_id),
                    question_id=QuestionId(row.question_id),
                    raw_answer=row.raw_answer,
                    asked_at=row.asked_at,
                    answered_at=row.answered_at,
                )
                for row in result.all()
            ]

    async def record_asked(self, *, student_id: StudentId, question_id: QuestionId) -> None:
        async with self._sessions.session() as s:
            stmt = pg_insert(AskedQuestionRow).values(
                student_id=str(student_id),
                question_id=str(question_id),
            )
            # If we've already asked it, leave the existing row alone — we
            # never want to clobber a real answer with an empty "asked" row.
            stmt = stmt.on_conflict_do_nothing(
                index_elements=[AskedQuestionRow.student_id, AskedQuestionRow.question_id],
            )
            await s.execute(stmt)

    async def record_answer(
        self,
        *,
        student_id: StudentId,
        question_id: QuestionId,
        raw_answer: str,
    ) -> None:
        async with self._sessions.session() as s:
            # Upsert: works whether or not `record_asked` ran first.
            now = datetime.now(UTC)
            stmt = pg_insert(AskedQuestionRow).values(
                student_id=str(student_id),
                question_id=str(question_id),
                raw_answer=raw_answer,
                answered_at=now,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[
                    AskedQuestionRow.student_id,
                    AskedQuestionRow.question_id,
                ],
                set_={
                    "raw_answer": stmt.excluded.raw_answer,
                    "answered_at": stmt.excluded.answered_at,
                },
            )
            await s.execute(stmt)
