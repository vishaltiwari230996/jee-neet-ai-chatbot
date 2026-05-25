"""Rule-based question selector.

A single pure function. No I/O, no LLM, no clock. Given the current state
of a student's profile and the questions they've already answered, it
returns the next question — or `None` when onboarding is complete.

Selection rules, in order:

1. **Audience filter** — drop questions whose `audience` doesn't include this
   student's class level.
2. **Already-asked filter** — drop questions in `asked_question_ids`.
3. **Missing-field filter** — keep only questions whose `maps_to` field is
   currently `None` on the profile (we never re-ask for data we already have).
4. **Priority sort** — pick the highest-priority remaining question. Ties
   are broken by `question_id` so the selection is fully deterministic
   (critical for reproducible tests and replay debugging).

Returning `None` is the natural signal that the onboarding loop should
transition to "classify archetype + persist + finish".
"""

from __future__ import annotations

from collections.abc import Iterable

from neetai_core.ids import QuestionId
from neetai_core.profile import StudentProfile
from neetai_question_bank.models import Question


def select_next_question(
    *,
    profile: StudentProfile,
    asked_question_ids: Iterable[QuestionId],
    available_questions: Iterable[Question],
) -> Question | None:
    """Return the next diagnostic question, or `None` when onboarding is complete."""
    asked = frozenset(asked_question_ids)

    eligible = [
        q
        for q in available_questions
        if q.applies_to(profile.class_level)
        and q.applies_to_exam(profile.exam_target)
        and q.question_id not in asked
        and _profile_field_is_missing(profile, q.maps_to)
    ]
    if not eligible:
        return None

    # Stable sort: highest priority first, then by id for deterministic ties.
    eligible.sort(key=lambda q: (-q.priority, q.question_id))
    return eligible[0]


def _profile_field_is_missing(profile: StudentProfile, field_name: str) -> bool:
    """`None` counts as missing. Anything else (including empty string,
    which we reject at ingestion time anyway) counts as set."""
    return getattr(profile, field_name, None) is None
