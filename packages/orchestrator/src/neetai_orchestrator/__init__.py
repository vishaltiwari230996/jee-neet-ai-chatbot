"""Answer pipeline orchestrator.

Phase-3 MVP: profile-gated, profile-personalised single-shot chat via
`ChatService.stream_answer`. Critique-revise loop and retrieval slot in
later behind the same public surface.

LangGraph stays reserved for the critique-revise sub-loop, not the linear
streaming path.
"""

from neetai_orchestrator.prompts import build_system_prompt
from neetai_orchestrator.service import ChatService, ChatTurn

__all__ = ["ChatService", "ChatTurn", "build_system_prompt"]
__version__ = "0.1.0"
