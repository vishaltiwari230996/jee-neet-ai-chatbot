"""CSV ingestion tests + a sanity check on the shipped starter CSV."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from neetai_core.errors import ValidationError
from neetai_profiling.mapper import supported_fields
from neetai_question_bank.ingest import (
    load_questions_from_csv,
    parse_questions,
    validate_maps_to_fields,
)
from neetai_question_bank.models import AnswerType

_HEADER = (
    "question_id,text,category,exam_targets,audience,answer_type,options,maps_to,"
    "priority,is_required\n"
)


def _csv(rows: str) -> io.StringIO:
    return io.StringIO(_HEADER + rows)


def test_parses_minimal_valid_row() -> None:
    csv = _csv(
        "Q1,Which subject is weakest?,academic_diagnosis,jee_main,dropper,single_choice,"
        "physics|chemistry,weak_subject,80,true\n",
    )
    questions = list(parse_questions(csv))
    assert len(questions) == 1
    q = questions[0]
    assert q.question_id == "Q1"
    assert q.answer_type is AnswerType.SINGLE_CHOICE
    assert q.options == ("physics", "chemistry")


def test_rejects_csv_missing_required_columns() -> None:
    csv = io.StringIO("question_id,text\nQ1,hi\n")
    with pytest.raises(ValidationError, match="missing required columns"):
        list(parse_questions(csv))


def test_rejects_duplicate_question_ids() -> None:
    rows = (
        "Q1,A?,academic_diagnosis,jee_main,dropper,single_choice,a|b,weak_subject,50,true\n"
        "Q1,B?,academic_diagnosis,jee_main,dropper,single_choice,a|b,main_problem,40,true\n"
    )
    with pytest.raises(ValidationError, match="Duplicate question_id"):
        list(parse_questions(_csv(rows)))


def test_rejects_choice_with_no_options() -> None:
    csv = _csv(
        "Q1,Which subject?,academic_diagnosis,jee_main,dropper,single_choice,"
        ",weak_subject,50,true\n",
    )
    with pytest.raises(ValidationError, match="requires at least one option"):
        list(parse_questions(csv))


def test_audience_pipe_split() -> None:
    csv = _csv(
        "Q1,X,academic_diagnosis,jee_main,class_11|class_12|dropper,single_choice,a|b,weak_subject,50,true\n",
    )
    q = next(parse_questions(csv))
    assert len(q.audience) == 3


def test_validate_maps_to_rejects_unknown_field() -> None:
    csv = _csv(
        "Q1,X,academic_diagnosis,jee_main,dropper,single_choice,a|b,not_a_real_field,50,true\n",
    )
    questions = list(parse_questions(csv))
    with pytest.raises(ValidationError, match="unknown profile fields"):
        validate_maps_to_fields(questions, supported_fields=frozenset({"weak_subject"}))


def test_starter_csv_loads_and_maps_to_supported_fields() -> None:
    """The shipped starter CSV must remain valid as the mapper evolves."""
    csv_path = Path(__file__).resolve().parents[3] / "infra" / "data" / "onboarding_questions.csv"
    assert csv_path.is_file(), f"missing starter CSV at {csv_path}"

    questions = load_questions_from_csv(csv_path)
    assert len(questions) >= 10
    validate_maps_to_fields(questions, supported_fields=supported_fields())
