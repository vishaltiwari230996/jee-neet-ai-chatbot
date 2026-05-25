"""Internal event bus.

Used for fire-and-forget side effects: analytics, profile refresh, embedding
jobs, feedback signal extraction. Implementations:
    * Redis Streams (default; small ops surface)
    * In-memory list (tests)

Events are JSON-serialisable dicts. Schemas live with the publisher.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EventBus(Protocol):
    async def publish(self, topic: str, event: dict[str, Any]) -> None: ...
