"""Generic key/value cache contract.

Used for:
    * semantic answer cache (key = hash(normalized_doubt, archetype))
    * rate-limit token buckets
    * profile snapshot warming

Implementations: Redis (primary), in-memory dict (tests).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Cache(Protocol):
    async def get(self, key: str) -> bytes | None: ...

    async def set(self, key: str, value: bytes, ttl_seconds: int | None = None) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def incr(self, key: str, ttl_seconds: int | None = None) -> int:
        """Atomic increment used by rate limiters."""
