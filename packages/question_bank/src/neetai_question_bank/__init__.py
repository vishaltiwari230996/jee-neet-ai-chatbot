"""Diagnostic question bank.

Three pieces:
    * `models`   — the typed `Question` value object
    * `selector` — pure-function rule-based question selection
    * `ingest`   — CSV → list[Question] parser (used by the CLI in scripts/)

Selection is deliberately rule-based at Phase 1. We add LLM-assisted
re-ranking only when (and if) the rules prove insufficient on real users.
Determinism here is the strongest single defence against AI slop in the
onboarding flow.
"""

from neetai_question_bank.ingest import (
    load_questions_from_csv,
    parse_questions,
    to_bank_question,
    validate_maps_to_fields,
)
from neetai_question_bank.models import (
    AnswerType,
    Question,
    QuestionCategory,
)
from neetai_question_bank.selector import select_next_question

__all__ = [
    "AnswerType",
    "Question",
    "QuestionCategory",
    "load_questions_from_csv",
    "parse_questions",
    "select_next_question",
    "to_bank_question",
    "validate_maps_to_fields",
]
__version__ = "0.1.0"
