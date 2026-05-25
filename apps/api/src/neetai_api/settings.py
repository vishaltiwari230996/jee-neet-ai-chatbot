"""Application settings.

Single typed object that the rest of the app reads. Everything that varies
across environments (local, dev, staging, prod) lands here. Adapters never
reach into `os.environ` themselves — they receive their config via the
container.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class LogFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


class LLMProvider(StrEnum):
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"
    FAKE = "fake"


class DatabaseBackend(StrEnum):
    """Which persistence adapter to wire up at startup.

    `memory` is for tests + ephemeral local dev only — it discards state on
    restart and offers no concurrency across processes. `postgres` is the
    production path.
    """

    POSTGRES = "postgres"
    MEMORY = "memory"


class AuthProviderName(StrEnum):
    CLERK = "clerk"
    FAKE = "fake"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEETAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    env: AppEnv = AppEnv.LOCAL
    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.TEXT

    api_host: str = "0.0.0.0"  # noqa: S104 — binding 0.0.0.0 in a container is intentional
    api_port: int = 8000

    database_backend: DatabaseBackend = DatabaseBackend.POSTGRES
    database_url: str = "postgresql+psycopg://neetai:neetai@localhost:55432/neetai"
    database_echo_sql: bool = False
    database_pool_size: int = 10
    redis_url: str = "redis://localhost:56379/0"

    llm_provider: LLMProvider = LLMProvider.FAKE
    # Model slugs verified against OpenRouter's `/api/v1/models` endpoint on
    # 2026-05-22. Sonnet 4.6 is the latest strong model (1M ctx); Haiku 4.5
    # is the latest cheap model (200K ctx). Both are routed through the
    # `ModelTier` enum in the LLM port, never hard-coded at call sites.
    llm_strong_model: str = "anthropic/claude-sonnet-4.6"
    llm_cheap_model: str = "anthropic/claude-haiku-4.5"
    llm_embedding_model: str = "text-embedding-3-small"
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2

    # Chat orchestrator knobs. Tuned conservatively: 1500 output tokens
    # ≈ ₹2 per message at Sonnet 4.6 prices, which scales fine to free-tier
    # demo usage. Lower these in dev to stretch a $10 OpenRouter cap.
    chat_max_output_tokens: int = 1500
    chat_temperature: float = 0.3
    chat_history_limit: int = 20

    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    sentry_dsn: str | None = None

    langfuse_enabled: bool = False
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    auth_provider: AuthProviderName = AuthProviderName.FAKE

    # Provider-specific secrets — read via the *raw* env names, no NEETAI_ prefix
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="OPENROUTER_BASE_URL",
    )
    openrouter_app_name: str = Field(default="neetai", alias="OPENROUTER_APP_NAME")
    openrouter_app_url: str = Field(
        default="https://neetai.local",
        alias="OPENROUTER_APP_URL",
    )

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    clerk_publishable_key: str | None = Field(default=None, alias="CLERK_PUBLISHABLE_KEY")
    clerk_secret_key: str | None = Field(default=None, alias="CLERK_SECRET_KEY")
    clerk_jwks_url: str | None = Field(default=None, alias="CLERK_JWKS_URL")
    clerk_webhook_signing_secret: str | None = Field(
        default=None,
        alias="CLERK_WEBHOOK_SIGNING_SECRET",
    )

    google_service_account_file: str | None = Field(
        default=None,
        alias="GOOGLE_SERVICE_ACCOUNT_FILE",
    )
    google_service_account_json: str | None = Field(
        default=None,
        alias="GOOGLE_SERVICE_ACCOUNT_JSON",
    )
    signup_sheet_id: str | None = Field(
        default=None,
        alias="SIGNUP_SHEET_ID",
    )
    signup_sheet_tab_name: str = Field(default="Signups", alias="SIGNUP_SHEET_TAB_NAME")

    @property
    def is_production(self) -> bool:
        return self.env is AppEnv.PROD


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. Call once per process."""
    return Settings()
