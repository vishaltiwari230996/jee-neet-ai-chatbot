"""Domain enums.

These reflect the categories defined in the project blueprint (sections 3, 5,
and 7). Keeping them as enums (not free-form strings) keeps the data model
honest and the LLM outputs validatable.
"""

from enum import StrEnum


class ClassLevel(StrEnum):
    CLASS_11 = "class_11"
    CLASS_12 = "class_12"
    DROPPER = "dropper"


class ExamTarget(StrEnum):
    JEE_MAIN = "jee_main"
    JEE_ADVANCED = "jee_advanced"
    NEET = "neet"
    JEE_MAIN_ADVANCED = "jee_main_advanced"


class Subject(StrEnum):
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    MATHEMATICS = "mathematics"
    BIOLOGY = "biology"


class Language(StrEnum):
    ENGLISH = "en"
    HINDI = "hi"
    HINGLISH = "hi-en"


class LearningStyle(StrEnum):
    BASIC_EXPLANATION = "basic_explanation"
    EXAMPLES = "examples"
    TRICKS = "tricks"
    STEP_BY_STEP = "step_by_step"
    VISUAL = "visual"


class DoubtType(StrEnum):
    """Mirrors §3.3 of the blueprint."""

    CONCEPT = "concept"
    PROBLEM_SOLVING = "problem_solving"
    STRATEGY = "strategy"
    REVISION = "revision"
    PERFORMANCE = "performance"
    EMOTIONAL = "emotional"
    PLANNING = "planning"
    OUT_OF_SCOPE = "out_of_scope"


class Archetype(StrEnum):
    """Mirrors §5 of the blueprint. Classification logic lives in
    `neetai_profiling.archetype`; this is just the value type."""

    WEAK_CONCEPTS_HARDWORKING = "weak_concepts_hardworking"
    STRONG_CONCEPTS_POOR_EXECUTION = "strong_concepts_poor_execution"
    CLASS_11_FOUNDATION = "class_11_foundation"
    CLASS_12_BALANCED = "class_12_balanced"
    DROPPER = "dropper"
    UNCLASSIFIED = "unclassified"
