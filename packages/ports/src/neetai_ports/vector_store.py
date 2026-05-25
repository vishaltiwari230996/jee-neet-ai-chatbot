"""Vector store contract.

Implementations: pgvector (primary), Qdrant (only if we outgrow pgvector).

Hybrid search lives behind this same interface: dense-only callers pass an
empty `query_text`; hybrid callers pass both. The adapter decides whether to
run BM25 in Postgres tsvector, in OpenSearch, or skip it.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from neetai_core.ids import ChunkId
from neetai_core.types import Subject


class VectorChunk(BaseModel):
    chunk_id: ChunkId
    content: str
    subject: Subject | None = None
    chapter: str | None = None
    topic: str | None = None
    difficulty: str | None = None
    source_type: str | None = None
    embedding: list[float]


class VectorSearchResult(BaseModel):
    chunk: VectorChunk
    score: float = Field(ge=0.0)


@runtime_checkable
class VectorStore(Protocol):
    async def upsert(self, chunks: list[VectorChunk]) -> None:
        """Insert or replace by chunk_id. Idempotent."""

    async def search(
        self,
        *,
        query_vector: list[float],
        query_text: str = "",
        k: int = 10,
        subject: Subject | None = None,
    ) -> list[VectorSearchResult]:
        """Hybrid (dense + lexical) when `query_text` is non-empty; dense-only otherwise."""

    async def delete(self, chunk_ids: list[ChunkId]) -> None: ...
