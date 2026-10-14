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

    # SQLAlchemy database URL used by the test suite. Kept separate from
    # ``database_url`` so tests never touch the development database. The
    # default is an in-memory SQLite database; integration tests can point
    # this at a dedicated PostgreSQL database.
    test_database_url: str = "sqlite:///:memory:"

    # Secret used to sign JWTs. The default is a development-only placeholder
    # that is long enough for HMAC-SHA256 (which needs at least 32 bytes);
    # production must still replace SECRET_KEY with a strong random value.
    secret_key: str = "dev-only-secret-key-change-me-in-production"

    # Signing algorithm and token lifetime for the access tokens issued by
    # ``POST /auth/token`` (backlog task 6).
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Browser origins allowed to call the API (backlog task 14).
    #
    # The SPA is served from a different origin than the API (port 3000 versus
    # port 8000), so the browser sends every call as a cross-origin request and
    # refuses the response without an `Access-Control-Allow-Origin` header. The
    # list is explicit rather than `*` so credentials and the Authorization
    # header stay scoped to known frontends.
    #
    # Comma-separated in the environment, for example:
    # ``CORS_ALLOW_ORIGINS=http://localhost:3000,https://app.example.com``.
    cors_allow_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    @property
    def cors_origins(self) -> list[str]:
        """The allowed origins as a list, ignoring empty entries."""
        return [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip()
        ]

    # OpenTelemetry OTLP endpoint. When unset, telemetry is disabled.
    otel_exporter_otlp_endpoint: str | None = None

    # Service name reported to the observability pipeline.
    otel_service_name: str = "efinges-backend"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
