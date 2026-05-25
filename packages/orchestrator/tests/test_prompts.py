"""Snapshot-style tests for the system prompt builder.

The point of these tests is not to fix the wording — it's to make sure
profile fields can't *silently* drop out of the prompt. Anti-slop guardrail:
if a key field stops appearing here, the LLM stops being personalised, and
we want CI to scream about it.
"""

from __future__ import annotations

from collections.abc import Callable

from neetai_core.profile import StudentProfile
from neetai_core.types import Archetype, Language, LearningStyle, Subject
from neetai_orchestrator import build_system_prompt


def test_prompt_includes_all_known_profile_fields(
    make_profile: Callable[..., StudentProfile],
) -> None:
    profile = make_profile(
        weak_subject=Subject.PHYSICS,
        strong_subject=Subject.CHEMISTRY,
        main_problem="Backlog",
        mistake_pattern="Skips reading the question carefully",
        emotional_state="anxious",
        learning_style=LearningStyle.TRICKS,
        mock_score_range="60-80",
        study_hours_per_day=4.0,
        language=Language.HINGLISH,
        archetype=Archetype.STRONG_CONCEPTS_POOR_EXECUTION,
        profile_confidence=0.82,
    )

    prompt = build_system_prompt(profile)

    expected_fragments = [
        "physics",
        "chemistry",
        "Backlog",
        "Skips reading the question carefully",
        "anxious",
        "tricks",
        "60-80",
        "4 hours",
        "hi-en",
        "strong_concepts_poor_execution",
        "82%",
    ]
    for fragment in expected_fragments:
        assert fragment in prompt, f"profile fragment missing from prompt: {fragment}"


def test_prompt_includes_archetype_policy(
    make_profile: Callable[..., StudentProfile],
) -> None:
    profile = make_profile(archetype=Archetype.WEAK_CONCEPTS_HARDWORKING)
    prompt = build_system_prompt(profile)
    assert "revision loops" in prompt


def test_prompt_sets_strategy_partner_boundary(
    make_profile: Callable[..., StudentProfile],
) -> None:
    prompt = build_system_prompt(make_profile())
    assert "EduGuide AI" in prompt
    assert "STRATEGY PARTNER" in prompt
    assert "You do NOT solve questions" in prompt
    assert "Never solve, attempt, or walk through any MCQ" in prompt


def test_prompt_handles_unknown_fields_gracefully(
    make_profile: Callable[..., StudentProfile],
) -> None:
    profile = make_profile()  # all optional fields default to None
    prompt = build_system_prompt(profile)
    assert "(unknown)" in prompt
    assert "Profile confidence" in prompt
