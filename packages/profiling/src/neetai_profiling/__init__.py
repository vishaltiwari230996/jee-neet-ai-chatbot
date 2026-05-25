"""Student profile construction + archetype classification.

Public surface:
    * `apply_answer`          — deterministic answer → profile update
    * `classify_archetype`    — pure-function archetype assignment
    * `OnboardingService`     — orchestrates selector + mapper + archetype +
                                repositories. Lives in `service.py` (Phase 1+).

All three are pure functions wherever possible. The service layer is the
only place that touches I/O — and it does so exclusively through repository
Protocols, never through a database driver directly.
"""

from neetai_profiling.archetype import classify_archetype
from neetai_profiling.mapper import (
    InvalidAnswer,
    apply_answer,
)
from neetai_profiling.service import OnboardingService, OnboardingState

__all__ = [
    "InvalidAnswer",
    "OnboardingService",
    "OnboardingState",
    "apply_answer",
    "classify_archetype",
]
__version__ = "0.1.0"
