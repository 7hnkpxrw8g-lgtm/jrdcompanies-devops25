"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "jrdbooks-api"
    environment: str = Field(default="local", description="local|staging|production")
    debug: bool = True

    database_url: str = "postgresql+psycopg://jrd:jrd@localhost:5432/jrdbooks"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    sentry_dsn: str | None = None
    otel_endpoint: str | None = None

    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    plaid_client_id: str | None = None
    plaid_secret: str | None = None
    plaid_env: str = "sandbox"

    openai_api_key: str | None = None
    ai_model: str = "claude-sonnet-4-6"

    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
