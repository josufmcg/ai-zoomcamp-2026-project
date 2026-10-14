"""Smoke tests for the backend application factory and health endpoint."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_healthz_returns_ok() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_read_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test-env.db")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    settings = Settings()

    assert settings.database_url == "sqlite:///./test-env.db"
    assert settings.secret_key == "test-secret"
    assert settings.otel_exporter_otlp_endpoint == "http://localhost:4317"


def test_settings_have_safe_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///./efinges.db"
    assert settings.secret_key == "dev-only-secret-key-change-me-in-production"
    assert settings.otel_exporter_otlp_endpoint is None
