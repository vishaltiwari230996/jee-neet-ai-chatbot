"""Pure interfaces (Protocols) for every external dependency.

If you find yourself importing a third-party SDK inside a domain package,
stop. Define the interface here, implement it in an adapter, and inject it.

The contracts here are the only stable agreement between the domain layer
and the outside world.
"""

from neetai_ports.auth import AuthenticatedUser, AuthProvider
from neetai_ports.cache import Cache
from neetai_ports.clock import Clock
from neetai_ports.event_bus import EventBus
from neetai_ports.llm import (
    CompletionRequest,
    CompletionResponse,
    LLMClient,
    LLMMessage,
    LLMRole,
    LLMUsage,
    ModelTier,
    StreamChunk,
)
from neetai_ports.repositories import (
    AskedQuestion,
    AskedQuestionRepository,
    BankQuestion,
    ProfileRepository,
    QuestionBankRepository,
    Student,
    StudentRepository,
)
from neetai_ports.vector_store import VectorChunk, VectorSearchResult, VectorStore

__all__ = [
    "AskedQuestion",
    "AskedQuestionRepository",
    "AuthProvider",
    "AuthenticatedUser",
    "BankQuestion",
    "Cache",
    "Clock",
    "CompletionRequest",
    "CompletionResponse",
    "EventBus",
    "LLMClient",
    "LLMMessage",
    "LLMRole",
    "LLMUsage",
    "ModelTier",
    "ProfileRepository",
    "QuestionBankRepository",
    "StreamChunk",
    "Student",
    "StudentRepository",
    "VectorChunk",
    "VectorSearchResult",
    "VectorStore",
]
