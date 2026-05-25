import pytest
from pydantic import ValidationError as PydanticValidationError

from neetai_core.answer import AnswerSection, Citation, StructuredAnswer
from neetai_core.ids import ChunkId


def _section(text: str = "x") -> AnswerSection:
    return AnswerSection(text=text)


def _full_answer(**overrides: object) -> StructuredAnswer:
    base: dict[str, object] = {
        "diagnosis": _section("Your score plateau is execution, not concept."),
        "explanation": _section("Here is why."),
        "concept_breakdown": _section("Step 1, step 2, step 3."),
        "example": _section("Sample question."),
        "common_mistake": _section("Skipping mock analysis."),
        "today_task": _section("Re-analyse last mock."),
    }
    base.update(overrides)
    return StructuredAnswer.model_validate(base)


def test_structured_answer_round_trips() -> None:
    answer = _full_answer()
    payload = answer.model_dump()
    assert StructuredAnswer.model_validate(payload) == answer


def test_section_text_required() -> None:
    with pytest.raises(PydanticValidationError):
        AnswerSection(text="")


def test_all_citations_flattens_across_sections() -> None:
    cite_a = Citation(chunk_id=ChunkId("chunk_1"), quote="a")
    cite_b = Citation(chunk_id=ChunkId("chunk_2"), quote="b")
    answer = _full_answer(
        diagnosis=AnswerSection(text="d", citations=[cite_a]),
        example=AnswerSection(text="e", citations=[cite_b]),
    )
    assert answer.all_citations() == [cite_a, cite_b]


def test_follow_up_question_optional() -> None:
    answer = _full_answer(follow_up_question=None)
    assert answer.follow_up_question is None


def test_confidence_bounded() -> None:
    with pytest.raises(PydanticValidationError):
        _full_answer(confidence=1.2)
