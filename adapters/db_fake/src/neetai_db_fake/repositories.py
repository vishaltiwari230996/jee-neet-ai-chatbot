"""Concurrency-safe in-memory repositories.

`asyncio.Lock`s wrap mutations so concurrent test scenarios don't see torn
state. We deep-copy aggregates on the way in and out — repositories return
*independent* objects so the caller cannot mutate persisted state by
accident (matching real-DB semantics).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from neetai_core.ids import QuestionId, StudentId
from neetai_core.profile import StudentProfile
from neetai_ports import (
    AskedQuestion,
    BankQuestion,
    Student,
)


class InMemoryStudentRepository:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._rows: dict[StudentId, Student] = {}

    async def get(self, student_id: StudentId) -> Student | None:
        return self._rows.get(student_id)

    async def upsert(self, student: Student) -> Student:
        async with self._lock:
            self._rows[student.student_id] = student
            return student


class InMemoryProfileRepository:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._rows: dict[StudentId, StudentProfile] = {}

    async def get(self, student_id: StudentId) -> StudentProfile | None:
        return self._rows.get(student_id)

    async def save(self, profile: StudentProfile) -> StudentProfile:
        async with self._lock:
            self._rows[profile.student_id] = profile
            return profile


class InMemoryQuestionBankRepository:
    def __init__(self, seed: list[BankQuestion] | None = None) -> None:
        self._lock = asyncio.Lock()
        self._rows: dict[QuestionId, BankQuestion] = {q.question_id: q for q in (seed or [])}

    async def list_active(self) -> list[BankQuestion]:
        return [q for q in self._rows.values() if q.is_active]

    async def upsert_many(self, questions: list[BankQuestion]) -> int:
        async with self._lock:
            for q in questions:
                self._rows[q.question_id] = q
            return len(questions)


class InMemoryAskedQuestionRepository:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._rows: list[AskedQuestion] = []

    async def list_answered_question_ids(self, student_id: StudentId) -> list[QuestionId]:
        return [
            row.question_id
            for row in self._rows
            if row.student_id == student_id and row.answered_at is not None
        ]

    async def list_answered(self, student_id: StudentId) -> list[AskedQuestion]:
        return sorted(
            [
                row
                for row in self._rows
                if row.student_id == student_id and row.answered_at is not None
            ],
            key=lambda row: row.answered_at or row.asked_at,
        )

    def _find_index(self, student_id: StudentId, question_id: QuestionId) -> int | None:
        for index, row in enumerate(self._rows):
            if row.student_id == student_id and row.question_id == question_id:
                return index
        return None

    async def record_asked(self, *, student_id: StudentId, question_id: QuestionId) -> None:
        async with self._lock:
            # Idempotent: never clobber an existing row (esp. its answer).
            if self._find_index(student_id, question_id) is not None:
                return
            self._rows.append(
                AskedQuestion(
                    student_id=student_id,
                    question_id=question_id,
                    raw_answer=None,
                    asked_at=datetime.now(UTC),
                    answered_at=None,
                ),
            )

    async def record_answer(
        self,
        *,
        student_id: StudentId,
        question_id: QuestionId,
        raw_answer: str,
    ) -> None:
        async with self._lock:
            index = self._find_index(student_id, question_id)
            now = datetime.now(UTC)
            if index is None:
                # Allow recording an answer even if `record_asked` was skipped
                # — mirrors the upsert behaviour of the SQL adapter.
                self._rows.append(
                    AskedQuestion(
                        student_id=student_id,
                        question_id=question_id,
                        raw_answer=raw_answer,
                        asked_at=now,
                        answered_at=now,
                    ),
                )
                return
            row = self._rows[index]
            self._rows[index] = row.model_copy(
                update={"raw_answer": raw_answer, "answered_at": now},
            )
