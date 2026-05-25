"""Chat orchestration service.

Phase-3 MVP shape: a single `ChatService.stream()` method that takes a
student's id, their conversation so far, and the new question; returns an
async iterator of `StreamChunk`s (incremental text deltas + a terminal
chunk with usage + cost).

What's deliberately omitted at MVP:
    * Doubt classification as a separate LLM call. Folded into the system
      prompt — Sonnet 4.6 handles intent recognition reliably enough that
      a Haiku pre-call would add latency for marginal benefit. Will split
      out when we see real failure modes worth routing on.
    * Retrieval. Stays disconnected until Phase 4 builds the corpus.
      The system prompt explicitly forbids fabricating citations, so the
      model defaults to grounded explanation rather than hallucinated
      sources.
    * Critique-revise loop. Adds ~half the latency cost again. Will turn
      on once the eval harness can quantify when it helps.
    * Persistence. Conversation history is passed in by the caller. When
      we want resumable chats, we add a `ChatRepository` Protocol.

What is here:
    * Profile gating — refuses gracefully if the student's profile is missing.
    * Profile-personalised system prompt (see `prompts.py`).
    * Streaming via the LLMClient.stream port — adapter handles cancellation.
    * Hard cap on output tokens to bound per-message cost.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from neetai_core.errors import NotFoundError
from neetai_core.ids import StudentId
from neetai_core.types import Language
from neetai_orchestrator.prompts import build_system_prompt
from neetai_ports import (
    AskedQuestionRepository,
    CompletionRequest,
    LLMClient,
    LLMMessage,
    LLMRole,
    ModelTier,
    ProfileRepository,
    QuestionBankRepository,
    StreamChunk,
)


@dataclass(slots=True, frozen=True)
class ChatTurn:
    """One side of the conversation as the orchestrator sees it.

    Kept distinct from `LLMMessage` so the HTTP layer can't accidentally
    forward a `system`-role message from a client (which would let them
    overwrite our policy).
    """

    role: LLMRole
    content: str

    def to_llm_message(self) -> LLMMessage:
        return LLMMessage(role=self.role, content=self.content)


class ChatService:
    def __init__(
        self,
        *,
        llm: LLMClient,
        profiles: ProfileRepository,
        questions: QuestionBankRepository,
        asked: AskedQuestionRepository,
        max_output_tokens: int = 1500,
        temperature: float = 0.3,
    ) -> None:
        self._llm = llm
        self._profiles = profiles
        self._questions = questions
        self._asked = asked
        self._max_output_tokens = max_output_tokens
        self._temperature = temperature

    async def stream_answer(
        self,
        *,
        student_id: StudentId,
        history: list[ChatTurn],
        question: str,
        response_language: Language | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream Sonnet's response. Raises if the student has no profile."""
        profile = await self._profiles.get(student_id)
        if profile is None:
            raise NotFoundError(
                f"No profile for student {student_id}. Complete onboarding first.",
            )

        for turn in history:
            if turn.role is LLMRole.SYSTEM:
                # Defensive: refuse client-supplied system messages. Our
                # system prompt is built fresh from the profile on every
                # call so the policy can't be poisoned via chat history.
                raise NotFoundError(
                    "Chat history must contain only user/assistant turns.",
                )

        onboarding_qa = await self._load_onboarding_qa(student_id)
        messages: list[LLMMessage] = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=build_system_prompt(
                    profile,
                    onboarding_qa=onboarding_qa,
                    response_language=response_language,
                ),
            ),
            *(turn.to_llm_message() for turn in history),
            LLMMessage(role=LLMRole.USER, content=question),
        ]

        request = CompletionRequest(
            tier=ModelTier.STRONG,
            messages=messages,
            temperature=self._temperature,
            max_output_tokens=self._max_output_tokens,
            metadata={"student_id": str(student_id)},
        )

        async for chunk in self._llm.stream(request):
            yield chunk

    async def _load_onboarding_qa(self, student_id: StudentId) -> list[tuple[str, str]]:
        answered = await self._asked.list_answered(student_id)
        if not answered:
            return []

        bank = await self._questions.list_active()
        question_text_by_id = {q.question_id: q.text for q in bank}
        return [
            (question_text_by_id.get(row.question_id, str(row.question_id)), row.raw_answer or "")
            for row in answered
            if row.raw_answer
        ]
