"""Chat HTTP routes.

Phase-3 MVP surface: a single SSE streaming endpoint. The client POSTs the
student id and the conversation so far; we stream Sonnet's reply back as
`data: {"delta": "..."}` events, terminating with `event: done`.

Why SSE (not WebSockets, not chunked JSON):
- SSE is one-way (server → client), which is exactly what streamed
  completion is. Adding WebSocket lifecycle for a unidirectional stream is
  ceremony we don't need.
- Plays nicely with the Next.js dev proxy.
- The browser EventSource API + the streaming Fetch API both consume it
  without custom protocol code.

Why we pass conversation history in the request (instead of storing
sessions server-side at this stage):
- Persistence is a Phase-4 concern. The orchestrator already accepts a
  history list, and the client trivially keeps it in React state. When we
  add `ChatRepository`, the wire schema stays compatible — we just start
  ignoring the client-supplied history when a session_id is present.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from neetai_api.container import Container
from neetai_api.deps import get_container
from neetai_api.logging import get_logger
from neetai_api.settings import Settings, get_settings
from neetai_core.ids import StudentId
from neetai_core.types import Language
from neetai_orchestrator import ChatService, ChatTurn
from neetai_ports import LLMRole

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
log = get_logger("neetai_api.chat")


# ---------------------------------------------------------------------------
# Wire schemas
# ---------------------------------------------------------------------------

ChatRole = Literal["user", "assistant"]


class ChatMessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: ChatRole
    content: str = Field(min_length=1, max_length=4000)


class ChatStreamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: StudentId = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=4000)
    language: Language | None = None
    history: list[ChatMessageIn] = Field(default_factory=list, max_length=40)


# ---------------------------------------------------------------------------
# Dependency wiring
# ---------------------------------------------------------------------------


def get_chat_service(
    container: Annotated[Container, Depends(get_container)],
) -> ChatService:
    return container.chat


ChatDep = Annotated[ChatService, Depends(get_chat_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream a personalized answer as Server-Sent Events.",
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def stream_chat(
    body: ChatStreamRequest,
    chat: ChatDep,
    settings: SettingsDep,
) -> StreamingResponse:
    # Cap history server-side regardless of what the client sent. Prevents
    # a misbehaving client from running up token bills by replaying a
    # 10,000-turn fake history.
    trimmed = body.history[-settings.chat_history_limit :]
    history = [
        ChatTurn(role=LLMRole(msg.role), content=msg.content) for msg in trimmed
    ]

    async def event_stream() -> AsyncIterator[bytes]:
        try:
            async for chunk in chat.stream_answer(
                student_id=body.student_id,
                history=history,
                question=body.question,
                response_language=body.language,
            ):
                if chunk.done:
                    payload = {
                        "model": chunk.model_id,
                        "usage": chunk.usage.model_dump() if chunk.usage else None,
                        "cost_usd": chunk.cost_usd,
                    }
                    yield _sse("done", payload)
                    return
                if chunk.delta:
                    yield _sse("delta", {"text": chunk.delta})
        except Exception as exc:
            # SSE can't surface a non-200 mid-stream cleanly. Emit a
            # structured error event and close — the client renders it
            # as an inline error message instead of a silent stall.
            log.exception("chat.stream.failed", error=str(exc))
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",  # disable nginx buffering if we ever sit behind it
        },
    )


def _sse(event: str, data: object) -> bytes:
    """Format one Server-Sent Event frame. Always a single `data:` line so
    we don't have to worry about newline escaping in deltas."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()
