"""CSV → Question loader.

Used by:
    * `scripts/ingest_questions.py` to seed the database from a CSV file
    * unit tests that need a deterministic question set
    * the API in tests, where the in-memory question repo is hydrated from
      this same CSV (single source of truth for what "the question bank" is)

CSV format is documented in `infra/data/onboarding_questions.csv`. Audience
and options are pipe-delimited inside a single CSV cell — keeps the file
trivially editable in any spreadsheet tool.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import IO

from neetai_core.errors import ValidationError
from neetai_core.ids import QuestionId
from neetai_core.types import ClassLevel, ExamTarget
from neetai_ports import BankQuestion
from neetai_question_bank.models import (
    AnswerType,
    Question,
    QuestionCategory,
)

_REQUIRED_COLUMNS = frozenset(
    {
        "question_id",
        "text",
        "category",
        "exam_targets",
        "audience",
        "answer_type",
        "options",
        "maps_to",
        "priority",
        "is_required",
    },
)


def load_questions_from_csv(path: Path) -> list[Question]:
    """Read and validate a CSV file end-to-end. Returns a list ordered by row."""
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(parse_questions(handle))


def parse_questions(stream: IO[str]) -> Iterator[Question]:
    reader = csv.DictReader(stream)
    if reader.fieldnames is None:
        raise ValidationError("CSV has no header row")

    missing = _REQUIRED_COLUMNS - set(reader.fieldnames)
    if missing:
        raise ValidationError(f"CSV missing required columns: {sorted(missing)}")

    seen_ids: set[str] = set()
    for line_no, row in enumerate(reader, start=2):
        try:
            question = _row_to_question(row)
        except (ValueError, KeyError) as exc:
            raise ValidationError(
                f"CSV row {line_no} ({row.get('question_id', '?')}): {exc}",
            ) from exc

        if question.question_id in seen_ids:
            raise ValidationError(
                f"Duplicate question_id '{question.question_id}' at row {line_no}",
            )
        seen_ids.add(question.question_id)
        yield question


def to_bank_question(q: Question) -> BankQuestion:
    """Domain → persistence shape.

    The persistence layer carries flat strings; we don't want the database
    code to depend on `neetai_question_bank` for the enum types.
    """
    return BankQuestion(
        question_id=q.question_id,
        text=q.text,
        category=q.category.value,
        exam_targets=[target.value for target in q.exam_targets],
        audience=[a.value for a in q.audience],
        answer_type=q.answer_type.value,
        options=list(q.options),
        maps_to=q.maps_to,
        priority=q.priority,
        is_required=q.is_required,
    )


def validate_maps_to_fields(
    questions: Iterable[Question],
    *,
    supported_fields: frozenset[str],
) -> None:
    """Fail fast if a question references a profile field the mapper can't fill.

    Called by the ingestion CLI before any database write — the import is
    all-or-nothing.
    """
    unknown = {q.question_id: q.maps_to for q in questions if q.maps_to not in supported_fields}
    if unknown:
        raise ValidationError(
            "Questions reference unknown profile fields: "
            + ", ".join(f"{qid}→{field}" for qid, field in sorted(unknown.items())),
        )


def _row_to_question(row: dict[str, str]) -> Question:
    exam_targets_raw = row["exam_targets"].strip()
    exam_targets = frozenset(ExamTarget(part) for part in _split_pipe(exam_targets_raw))
    if not exam_targets:
        raise ValueError("exam_targets cannot be empty")

    audience_raw = row["audience"].strip()
    audience = frozenset(ClassLevel(part) for part in _split_pipe(audience_raw))
    if not audience:
        raise ValueError("audience cannot be empty")

    answer_type = AnswerType(row["answer_type"].strip())
    options_raw = row.get("options", "").strip()
    options: tuple[str, ...] = tuple(_split_pipe(options_raw)) if options_raw else ()

    if answer_type in {AnswerType.SINGLE_CHOICE, AnswerType.MULTI_CHOICE} and not options:
        raise ValueError(f"answer_type={answer_type.value} requires at least one option")

    return Question(
        question_id=QuestionId(row["question_id"].strip()),
        text=row["text"].strip(),
        category=QuestionCategory(row["category"].strip()),
        exam_targets=exam_targets,
        audience=audience,
        answer_type=answer_type,
        options=options,
        maps_to=row["maps_to"].strip(),
        priority=int(row["priority"].strip()),
        is_required=_to_bool(row["is_required"]),
    )


def _split_pipe(raw: str) -> list[str]:
    return [part.strip() for part in raw.split("|") if part.strip()]


def _to_bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in {"true", "1", "yes", "y"}:
        return True
    if value in {"false", "0", "no", "n", ""}:
        return False
    raise ValueError(f"cannot parse bool from {raw!r}")
