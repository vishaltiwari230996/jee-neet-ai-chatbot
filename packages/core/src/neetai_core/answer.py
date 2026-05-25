"""The structured answer schema.

Every LLM-generated answer must conform to this. The blueprint (§6) specifies
seven required sections; the schema is enforced via JSON-schema-constrained
LLM output AND validated again on receipt — belt and suspenders.

Anti-slop guarantees enforced here:
    * Answers carry citations referencing real chunks; the orchestrator
      verifies every citation exists in the retrieved set.
    * Personalization is auditable: `profile_signals_used` lists which
      profile fields the LLM was instructed to use.
    * Length bounds prevent rambling output.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from neetai_core.ids import ChunkId


class Citation(BaseModel):
    """One reference back to a retrieved knowledge-base chunk."""

    chunk_id: ChunkId
    quote: str = Field(min_length=1, max_length=400)


class AnswerSection(BaseModel):
    """A single section of the seven-part answer."""

    text: str = Field(min_length=1, max_length=1200)
    citations: list[Citation] = Field(default_factory=list)


class StructuredAnswer(BaseModel):
    """The full personalized answer payload.

    Field names map 1-to-1 to blueprint §6 so a teacher reviewing the UI sees
    exactly the structure the product promised.
    """

    diagnosis: AnswerSection
    explanation: AnswerSection
    concept_breakdown: AnswerSection
    example: AnswerSection
    common_mistake: AnswerSection
    today_task: AnswerSection
    follow_up_question: str | None = Field(default=None, max_length=240)

    profile_signals_used: list[str] = Field(
        default_factory=list,
        description="Profile field names the answer was personalized against.",
    )
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)

    def all_citations(self) -> list[Citation]:
        """Flatten citations across sections — used by the citation verifier."""
        result: list[Citation] = []
        for section in (
            self.diagnosis,
            self.explanation,
            self.concept_breakdown,
            self.example,
            self.common_mistake,
            self.today_task,
        ):
            result.extend(section.citations)
        return result
