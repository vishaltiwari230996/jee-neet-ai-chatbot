"""In-memory repository adapters.

Why this exists:

* Unit tests should never depend on a docker stack. The fake repos let us
  exercise *real* domain services against *real* repository interfaces in a
  millisecond, with no setup.
* Local dev without docker is occasionally useful — the API can boot against
  these and serve a smoke-test onboarding flow.

These are NOT for production. The container in `apps/api` selects them only
when `NEETAI_DB_PROVIDER=fake`.
"""

from neetai_db_fake.repositories import (
    InMemoryAskedQuestionRepository,
    InMemoryProfileRepository,
    InMemoryQuestionBankRepository,
    InMemoryStudentRepository,
)

__all__ = [
    "InMemoryAskedQuestionRepository",
    "InMemoryProfileRepository",
    "InMemoryQuestionBankRepository",
    "InMemoryStudentRepository",
]
