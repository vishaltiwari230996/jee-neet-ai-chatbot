"""Shared domain vocabulary for the NeetAI system.

Every package in the workspace may depend on `neetai_core`. `neetai_core`
depends on nothing outside the standard library + pydantic.
"""

from neetai_core.errors import (
    DomainError,
    NotFoundError,
    SafetyViolation,
    UpstreamError,
    ValidationError,
)
from neetai_core.ids import ChunkId, MessageId, SessionId, StudentId
from neetai_core.types import (
    Archetype,
    ClassLevel,
    DoubtType,
    ExamTarget,
    Language,
    LearningStyle,
    Subject,
)

__all__ = [
    "Archetype",
    "ChunkId",
    "ClassLevel",
    "DomainError",
    "DoubtType",
    "ExamTarget",
    "Language",
    "LearningStyle",
    "MessageId",
    "NotFoundError",
    "SafetyViolation",
    "SessionId",
    "StudentId",
    "Subject",
    "UpstreamError",
    "ValidationError",
]
