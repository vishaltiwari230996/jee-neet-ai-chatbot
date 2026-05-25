"""Strongly-typed identifier aliases.

NewType wrappers around `str` so the type checker prevents accidentally
passing a `MessageId` where a `StudentId` was expected. They cost nothing
at runtime but eliminate a whole class of bug.
"""

from typing import NewType

StudentId = NewType("StudentId", str)
SessionId = NewType("SessionId", str)
MessageId = NewType("MessageId", str)
ChunkId = NewType("ChunkId", str)
QuestionId = NewType("QuestionId", str)
