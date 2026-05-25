"""Persistence Protocols.

The domain layer talks to persistence exclusively through these. A repository
*reads* and *writes* aggregate-level domain objects (StudentProfile, Question,
…). It does not expose SQL, ORM rows, or transactions.

Implementations:
    * `adapters/db_postgres` — SQLAlchemy 2.0 + psycopg async (production)
    * `adapters/db_fake`     — in-memory dict-based (tests, local dev)

Why repositories and not a unit-of-work pattern at MVP: a single `UnitOfWork`
would be premature ceremony for our current handlers. When we need
cross-aggregate transactions (e.g. "save profile AND append asked question
atomically"), we add a `UnitOfWork` Protocol then. Until then, each repo
method is its own transaction.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from neetai_core.ids import QuestionId, StudentId
from neetai_core.profile import StudentProfile

# ---------------------------------------------------------------------------
# Persistence-facing value objects that cross the boundary
# ---------------------------------------------------------------------------


class Student(BaseModel):
    """Minimal student identity record.

    Richer behavioural data lives on `StudentProfile` (a separate aggregate).
    The split makes auth changes cheap: rotating an email is a student-row
    update; archetype recomputes are profile-row updates.
    """

    model_config = ConfigDict(frozen=True)

    student_id: StudentId
    email: str | None = None
    display_name: str | None = None
    created_at: datetime
    last_active_at: datetime


class BankQuestion(BaseModel):
    """Persistence-facing question row.

    Flat, JSON-compatible: easy to read from a DB row, easy to send over the
    wire. The domain-side `Question` (in `neetai_question_bank`) enriches
    this with typed enums; repositories convert between the two at the
    boundary.
    """

    model_config = ConfigDict(frozen=True)

    question_id: QuestionId
    text: str
    category: str
    exam_targets: list[str]
    audience: list[str]
    answer_type: str
    options: list[str] = Field(default_factory=list)
    maps_to: str
    priority: int = 50
    is_required: bool = True
    is_active: bool = True


class AskedQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    student_id: StudentId
    question_id: QuestionId
    raw_answer: str | None
    asked_at: datetime
    answered_at: datetime | None


# ---------------------------------------------------------------------------
# Repository Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class StudentRepository(Protocol):
    async def get(self, student_id: StudentId) -> Student | None: ...
    async def upsert(self, student: Student) -> Student: ...


@runtime_checkable
class ProfileRepository(Protocol):
    async def get(self, student_id: StudentId) -> StudentProfile | None: ...
    async def save(self, profile: StudentProfile) -> StudentProfile: ...


@runtime_checkable
class QuestionBankRepository(Protocol):
    """The question bank is *append-mostly*. We never delete in place — to
    deprecate, mark `is_active=False`. The CSV ingestion CLI handles upserts.
    """

    async def list_active(self) -> list[BankQuestion]: ...

    async def upsert_many(self, questions: list[BankQuestion]) -> int:
        """Insert or update each question by id. Returns the count written."""


@runtime_checkable
class AskedQuestionRepository(Protocol):
    async def list_answered_question_ids(self, student_id: StudentId) -> list[QuestionId]:
        """Question ids the student has actually *answered*.

        The selector uses this to decide what to ask next. Crucially: a
        question that was *shown but not answered* (e.g. user closed the
        browser mid-question) is NOT in this list — they will see it again
        on resume, which is the correct UX.
        """

    async def list_answered(self, student_id: StudentId) -> list[AskedQuestion]:
        """Answered onboarding rows, ordered by answer time.

        The chat orchestrator uses this to send the raw onboarding Q/A context
        to the model, not just the normalized profile fields. This preserves
        nuance from free-text answers like weak chapters and current worries.
        """

    async def record_asked(self, *, student_id: StudentId, question_id: QuestionId) -> None:
        """Audit: record that we presented this question to the student.

        Idempotent — re-asking the same question (e.g. on resume) does not
        clobber the existing row or its `answered_at` if already set.
        """

    async def record_answer(
        self,
        *,
        student_id: StudentId,
        question_id: QuestionId,
        raw_answer: str,
    ) -> None:
        """Store the student's answer + stamp `answered_at`."""
