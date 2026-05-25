"""Dependency-injection container.

The *only* place in the codebase that knows which concrete adapter sits
behind each port. Routers and services depend on Protocols (`LLMClient`,
`StudentRepository`, ...), never on the concrete classes.

To swap implementations in production: change the relevant env var and
restart. No code changes anywhere else.
"""

from __future__ import annotations

from dataclasses import dataclass

from neetai_api.settings import DatabaseBackend, LLMProvider, Settings
from neetai_db_fake import (
    InMemoryAskedQuestionRepository,
    InMemoryProfileRepository,
    InMemoryQuestionBankRepository,
    InMemoryStudentRepository,
)
from neetai_db_postgres import (
    DatabaseConfig,
    PgAskedQuestionRepository,
    PgProfileRepository,
    PgQuestionBankRepository,
    PgStudentRepository,
    SessionFactory,
    create_session_factory,
)
from neetai_llm_anthropic import AnthropicClient, AnthropicConfig
from neetai_llm_fake import FakeLLMClient
from neetai_llm_openrouter import OpenRouterClient, OpenRouterConfig
from neetai_orchestrator import ChatService
from neetai_ports import (
    AskedQuestionRepository,
    LLMClient,
    ProfileRepository,
    QuestionBankRepository,
    StudentRepository,
)
from neetai_profiling.service import OnboardingService


@dataclass(slots=True)
class Container:
    """Holds the assembled adapters. Built once on startup, torn down on shutdown."""

    settings: Settings

    # LLM
    llm: LLMClient

    # Repositories — accessed through their Protocol type so routers never
    # import the concrete adapter.
    students: StudentRepository
    profiles: ProfileRepository
    questions: QuestionBankRepository
    asked: AskedQuestionRepository

    # Domain services composed over the repositories.
    onboarding: OnboardingService
    chat: ChatService

    # Owned resources we must explicitly tear down. Kept private so callers
    # don't accidentally couple to them.
    _openrouter: OpenRouterClient | None = None
    _session_factory: SessionFactory | None = None

    async def aclose(self) -> None:
        if self._openrouter is not None:
            await self._openrouter.aclose()
        if self._session_factory is not None:
            await self._session_factory.aclose()

    async def healthcheck_db(self) -> bool:
        """Lightweight DB probe for the readiness endpoint.

        Returns True for the in-memory backend (always available).
        """
        if self._session_factory is None:
            return True
        return await self._session_factory.healthcheck()


def build_container(settings: Settings) -> Container:
    """Assemble adapters according to settings.

    Fails fast at startup (not at first request) if required secrets are missing —
    a misconfigured production deploy should refuse to come up.
    """
    llm, openrouter = _build_llm(settings)
    students, profiles, questions, asked, session_factory = _build_repositories(settings)

    onboarding = OnboardingService(
        students=students,
        profiles=profiles,
        questions=questions,
        asked=asked,
    )
    chat = ChatService(
        llm=llm,
        profiles=profiles,
        questions=questions,
        asked=asked,
        max_output_tokens=settings.chat_max_output_tokens,
        temperature=settings.chat_temperature,
    )

    return Container(
        settings=settings,
        llm=llm,
        students=students,
        profiles=profiles,
        questions=questions,
        asked=asked,
        onboarding=onboarding,
        chat=chat,
        _openrouter=openrouter,
        _session_factory=session_factory,
    )


# ---------------------------------------------------------------------------
# Helpers — kept narrow so `build_container` reads as one screen.
# ---------------------------------------------------------------------------


def _build_llm(settings: Settings) -> tuple[LLMClient, OpenRouterClient | None]:
    match settings.llm_provider:
        case LLMProvider.OPENROUTER:
            if not settings.openrouter_api_key:
                raise RuntimeError(
                    "NEETAI_LLM_PROVIDER=openrouter requires OPENROUTER_API_KEY",
                )
            client = OpenRouterClient(
                OpenRouterConfig(
                    api_key=settings.openrouter_api_key,
                    base_url=settings.openrouter_base_url,
                    app_name=settings.openrouter_app_name,
                    app_url=settings.openrouter_app_url,
                    timeout_seconds=settings.llm_timeout_seconds,
                    max_retries=settings.llm_max_retries,
                    strong_model=settings.llm_strong_model,
                    cheap_model=settings.llm_cheap_model,
                    embedding_model=settings.llm_embedding_model,
                ),
            )
            return client, client

        case LLMProvider.ANTHROPIC:
            if not settings.anthropic_api_key:
                raise RuntimeError(
                    "NEETAI_LLM_PROVIDER=anthropic requires ANTHROPIC_API_KEY",
                )
            return (
                AnthropicClient(
                    AnthropicConfig(
                        api_key=settings.anthropic_api_key,
                        timeout_seconds=settings.llm_timeout_seconds,
                    ),
                ),
                None,
            )

        case LLMProvider.FAKE:
            return FakeLLMClient(), None


def _build_repositories(
    settings: Settings,
) -> tuple[
    StudentRepository,
    ProfileRepository,
    QuestionBankRepository,
    AskedQuestionRepository,
    SessionFactory | None,
]:
    match settings.database_backend:
        case DatabaseBackend.MEMORY:
            return (
                InMemoryStudentRepository(),
                InMemoryProfileRepository(),
                InMemoryQuestionBankRepository(),
                InMemoryAskedQuestionRepository(),
                None,
            )

        case DatabaseBackend.POSTGRES:
            factory = create_session_factory(
                DatabaseConfig(
                    url=settings.database_url,
                    echo=settings.database_echo_sql,
                    pool_size=settings.database_pool_size,
                ),
            )
            return (
                PgStudentRepository(factory),
                PgProfileRepository(factory),
                PgQuestionBankRepository(factory),
                PgAskedQuestionRepository(factory),
                factory,
            )
