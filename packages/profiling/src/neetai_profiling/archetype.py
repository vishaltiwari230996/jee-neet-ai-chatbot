"""Archetype classification — pure decision tree.

Mirrors blueprint §5 (Student Archetypes). Decisions are explicit; no LLM,
no probability, no ML model. The point is that a teacher reading this file
can audit *exactly* how an archetype is assigned and disagree intelligently.

Order matters: rules fire top-to-bottom. The first match wins. This makes
overrides easy (e.g. a Class-11 student with strong concepts but poor
execution still maps to `STRONG_CONCEPTS_POOR_EXECUTION` because that rule
fires before the foundation-student fallback).

The function is pure: same inputs → same output, no side effects.
"""

from __future__ import annotations

from neetai_core.profile import StudentProfile
from neetai_core.types import Archetype, ClassLevel

# String fragments we look for inside free-text profile fields. Lowercased
# during comparison so authors of the question CSV don't need to worry about
# capitalisation. Keep these short — long phrases create false negatives.

_LOW_SCORE_SIGNS = ("low mock score", "low confidence", "marks not improving")
_SILLY_MISTAKE_SIGNS = ("silly mistake", "calculation", "panic", "time pressure")
_CONCEPTUAL_GAP_SIGNS = ("backlog", "concept", "lectures", "not understanding")


def classify_archetype(profile: StudentProfile) -> Archetype:
    """Map a `StudentProfile` to one of the blueprint's archetypes.

    Returns `Archetype.UNCLASSIFIED` when there isn't enough profile signal
    to assign one — the orchestrator treats this as "ask another diagnostic
    question before answering".
    """
    if not _has_enough_signal(profile):
        return Archetype.UNCLASSIFIED

    # Behavioural signatures override class-based fallbacks.
    if _looks_like_strong_concepts_poor_execution(profile):
        return Archetype.STRONG_CONCEPTS_POOR_EXECUTION

    if _looks_like_weak_concepts_hardworking(profile):
        return Archetype.WEAK_CONCEPTS_HARDWORKING

    # Class-level fallbacks. Dropper is most specific, then 12, then 11.
    match profile.class_level:
        case ClassLevel.DROPPER:
            return Archetype.DROPPER
        case ClassLevel.CLASS_12:
            return Archetype.CLASS_12_BALANCED
        case ClassLevel.CLASS_11:
            return Archetype.CLASS_11_FOUNDATION


# ---------------------------------------------------------------------------
# Rule helpers — small enough to be readable on one screen.
# ---------------------------------------------------------------------------


def _has_enough_signal(profile: StudentProfile) -> bool:
    """We need at least one of the diagnostic signals before classifying."""
    return any(
        getattr(profile, name) is not None
        for name in (
            "weak_subject",
            "main_problem",
            "mistake_pattern",
            "study_hours_per_day",
        )
    )


def _contains_any(haystack: str | None, needles: tuple[str, ...]) -> bool:
    if not haystack:
        return False
    lower = haystack.lower()
    return any(needle in lower for needle in needles)


def _looks_like_strong_concepts_poor_execution(profile: StudentProfile) -> bool:
    """Blueprint §5.2: understands theory, makes silly mistakes, time pressure."""
    studies_hard = (profile.study_hours_per_day or 0) >= 5
    has_silly_mistakes = _contains_any(profile.mistake_pattern, _SILLY_MISTAKE_SIGNS)
    has_score_concern = _contains_any(profile.main_problem, _LOW_SCORE_SIGNS)
    no_concept_gap = not _contains_any(profile.main_problem, _CONCEPTUAL_GAP_SIGNS)

    return studies_hard and has_silly_mistakes and has_score_concern and no_concept_gap


def _looks_like_weak_concepts_hardworking(profile: StudentProfile) -> bool:
    """Blueprint §5.1: studies many hours, conceptual gaps, needs hints."""
    studies_hard = (profile.study_hours_per_day or 0) >= 5
    has_concept_gap = _contains_any(profile.main_problem, _CONCEPTUAL_GAP_SIGNS)
    return studies_hard and has_concept_gap
