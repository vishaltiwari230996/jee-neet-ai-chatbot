"""Domain error hierarchy.

Every error raised by domain code derives from `DomainError`. Adapters
translate their own exceptions into one of these so callers see a stable
surface regardless of which provider/database/etc. backed the call.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base for all expected, non-bug error conditions."""

    code: str = "domain_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class ValidationError(DomainError):
    code = "validation_error"


class NotFoundError(DomainError):
    code = "not_found"


class SafetyViolation(DomainError):
    """Raised when an input or output trips a safety rule.

    Carrying the rule id lets the API layer translate this into a structured
    refusal payload without leaking internals.
    """

    code = "safety_violation"

    def __init__(self, message: str, *, rule_id: str) -> None:
        super().__init__(message)
        self.rule_id = rule_id


class UpstreamError(DomainError):
    """Raised by adapters when a third-party dependency fails.

    Carries the provider name and whether a retry is sensible so the caller
    can decide between retry, fallback, and surfacing.
    """

    code = "upstream_error"

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable
