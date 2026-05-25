"""Auth provider contract.

Implementations:
    * Clerk (production MVP)
    * Fake (local dev — accepts any token, returns a dev user)

API code calls `verify_token(token)` → `AuthenticatedUser`. It never knows
which provider is wired in. Swapping Clerk → self-hosted is one adapter file.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from neetai_core.ids import StudentId


class AuthenticatedUser(BaseModel):
    student_id: StudentId
    email: str | None = None
    issued_at_unix: int


@runtime_checkable
class AuthProvider(Protocol):
    async def verify_token(self, token: str) -> AuthenticatedUser:
        """Validate the token. Raise `neetai_core.SafetyViolation` if invalid."""
