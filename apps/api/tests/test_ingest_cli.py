"""Unit tests for the question-ingest CLI orchestration.

We don't shell out to the script — instead we test `run_ingest` directly
with an in-memory question repo. This keeps the test fast, deterministic,
and independent of the Postgres adapter.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from neetai_api.cli.ingest_questions import run_ingest
from neetai_core.errors import ValidationError
from neetai_db_fake import InMemoryQuestionBankRepository

REPO_ROOT = Path(__file__).resolve().parents[3]
STARTER_CSV = REPO_ROOT / "infra" / "data" / "onboarding_questions.csv"


@pytest.mark.asyncio
async def test_ingest_writes_questions(tmp_path: Path) -> None:
    csv = tmp_path / "qs.csv"
    csv.write_text(
        "question_id,text,category,exam_targets,audience,answer_type,options,maps_to,priority,is_required\n"
        "Q001,Which subject feels hardest?,academic_diagnosis,jee_main,dropper|class_12,"
        "single_choice,physics|chemistry|biology|math,weak_subject,90,true\n",
        encoding="utf-8",
    )

    repo = InMemoryQuestionBankRepository()
    result = await run_ingest(csv, repo)

    assert result.written == 1
    listed = await repo.list_active()
    assert [q.question_id for q in listed] == ["Q001"]


@pytest.mark.asyncio
async def test_ingest_is_idempotent(tmp_path: Path) -> None:
    csv = tmp_path / "qs.csv"
    csv.write_text(
        "question_id,text,category,exam_targets,audience,answer_type,options,maps_to,priority,is_required\n"
        "Q001,One,academic_diagnosis,jee_main,dropper,single_choice,a|b,weak_subject,80,true\n",
        encoding="utf-8",
    )
    repo = InMemoryQuestionBankRepository()

    await run_ingest(csv, repo)
    await run_ingest(csv, repo)

    listed = await repo.list_active()
    assert len(listed) == 1, "second run must not create a duplicate row"


@pytest.mark.asyncio
async def test_ingest_rejects_unknown_maps_to(tmp_path: Path) -> None:
    csv = tmp_path / "qs.csv"
    csv.write_text(
        "question_id,text,category,exam_targets,audience,answer_type,options,maps_to,priority,is_required\n"
        "Q001,Hi,academic_diagnosis,jee_main,dropper,short_text,,not_a_real_field,50,true\n",
        encoding="utf-8",
    )
    repo = InMemoryQuestionBankRepository()

    with pytest.raises(ValidationError, match="unknown profile fields"):
        await run_ingest(csv, repo)


@pytest.mark.asyncio
async def test_ingest_raises_on_missing_file(tmp_path: Path) -> None:
    repo = InMemoryQuestionBankRepository()
    with pytest.raises(ValidationError, match="CSV file not found"):
        await run_ingest(tmp_path / "nope.csv", repo)


@pytest.mark.asyncio
async def test_ingest_loads_the_starter_csv() -> None:
    """Locks in the contract: the shipped starter CSV is always valid."""
    assert STARTER_CSV.exists(), f"starter CSV missing at {STARTER_CSV}"
    repo = InMemoryQuestionBankRepository()
    result = await run_ingest(STARTER_CSV, repo)
    assert result.written >= 8, "starter set should have ~10 questions"
