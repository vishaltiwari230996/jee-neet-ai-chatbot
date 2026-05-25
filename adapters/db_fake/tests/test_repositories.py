"""Verify the in-memory adapters satisfy the repository Protocols + behave."""

from __future__ import annotations

from datetime import UTC, datetime

from neetai_core.ids import QuestionId, StudentId
from neetai_core.profile import StudentProfile
from neetai_core.types import ClassLevel, ExamTarget
from neetai_db_fake import (
    InMemoryAskedQuestionRepository,
    InMemoryProfileRepository,
    InMemoryQuestionBankRepository,
    InMemoryStudentRepository,
)
from neetai_ports import (
    AskedQuestionRepository,
    BankQuestion,
    ProfileRepository,
    QuestionBankRepository,
    Student,
    StudentRepository,
)


def test_satisfies_protocols() -> None:
    assert isinstance(InMemoryStudentRepository(), StudentRepository)
    assert isinstance(InMemoryProfileRepository(), ProfileRepository)
    assert isinstance(InMemoryQuestionBankRepository(), QuestionBankRepository)
    assert isinstance(InMemoryAskedQuestionRepository(), AskedQuestionRepository)


async def test_student_upsert_and_get() -> None:
    repo = InMemoryStudentRepository()
    now = datetime.now(UTC)
    student = Student(
        student_id=StudentId("stu_1"),
        email="a@b.com",
        display_name="A",
        created_at=now,
        last_active_at=now,
    )
    await repo.upsert(student)
    assert (await repo.get(StudentId("stu_1"))) == student
    assert (await repo.get(StudentId("stu_missing"))) is None


async def test_profile_save_returns_persisted() -> None:
    repo = InMemoryProfileRepository()
    now = datetime.now(UTC)
    profile = StudentProfile(
        student_id=StudentId("stu_1"),
        class_level=ClassLevel.DROPPER,
        exam_target=ExamTarget.JEE_MAIN,
        created_at=now,
        updated_at=now,
    )
    saved = await repo.save(profile)
    assert saved == profile
    assert (await repo.get(StudentId("stu_1"))) == profile


async def test_question_bank_filters_inactive() -> None:
    active = BankQuestion(
        question_id=QuestionId("Q1"),
        text="active?",
        category="academic_diagnosis",
        exam_targets=["jee_main"],
        audience=["dropper"],
        answer_type="single_choice",
        options=["a"],
        maps_to="weak_subject",
        is_active=True,
    )
    inactive = active.model_copy(update={"question_id": QuestionId("Q2"), "is_active": False})
    repo = InMemoryQuestionBankRepository(seed=[active, inactive])
    listed = await repo.list_active()
    assert [q.question_id for q in listed] == ["Q1"]


async def test_question_bank_upsert_is_idempotent() -> None:
    repo = InMemoryQuestionBankRepository()
    q = BankQuestion(
        question_id=QuestionId("Q1"),
        text="t",
        category="academic_diagnosis",
        exam_targets=["jee_main"],
        audience=["dropper"],
        answer_type="single_choice",
        options=["a"],
        maps_to="weak_subject",
    )
    assert await repo.upsert_many([q]) == 1
    assert await repo.upsert_many([q]) == 1
    listed = await repo.list_active()
    assert len(listed) == 1


async def test_answered_questions_only_appear_after_answer() -> None:
    repo = InMemoryAskedQuestionRepository()
    sid = StudentId("stu_1")
    qid = QuestionId("Q1")

    await repo.record_asked(student_id=sid, question_id=qid)
    # Still in flight — selector should re-offer it.
    assert await repo.list_answered_question_ids(sid) == []

    await repo.record_answer(student_id=sid, question_id=qid, raw_answer="physics")
    assert await repo.list_answered_question_ids(sid) == [qid]


async def test_record_asked_is_idempotent() -> None:
    repo = InMemoryAskedQuestionRepository()
    sid = StudentId("stu_1")
    qid = QuestionId("Q1")

    await repo.record_asked(student_id=sid, question_id=qid)
    await repo.record_answer(student_id=sid, question_id=qid, raw_answer="physics")
    # Re-asking after answer must not wipe the answer (would lose data).
    await repo.record_asked(student_id=sid, question_id=qid)
    assert await repo.list_answered_question_ids(sid) == [qid]


async def test_record_answer_without_record_asked_upserts() -> None:
    """The pg adapter does upsert; the in-memory adapter must match."""
    repo = InMemoryAskedQuestionRepository()
    sid = StudentId("stu_1")
    qid = QuestionId("Q1")

    await repo.record_answer(student_id=sid, question_id=qid, raw_answer="x")
    assert await repo.list_answered_question_ids(sid) == [qid]
