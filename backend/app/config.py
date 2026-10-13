"""Application settings loaded from environment variables.

Every value can be overridden with an environment variable (for example
``DATABASE_URL``, ``SECRET_KEY``, ``OTEL_EXPORTER_OTLP_ENDPOINT``). The
defaults below are safe for local development only and must never be used
in production.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the EFINGES backend."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLAlchemy database URL. Defaults to a local SQLite file for
    # development; production and Docker use PostgreSQL.
    database_url: str = "sqlite:///./efinges.db"

    # Secret used to sign JWTs. The default is a development-only value;
    # production must set a strong random SECRET_KEY.
    secret_key: str = "dev-only-secret-key-change-me"

    # OpenTelemetry OTLP endpoint. When unset, telemetry is disabled.
    otel_exporter_otlp_endpoint: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
