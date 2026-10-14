"""CORS behavior tests (backlog task 14).

The SPA is served from a different origin than the API, so the browser only
accepts an API response when the server echoes the frontend origin in
``Access-Control-Allow-Origin``. These tests pin that behavior down, plus the
preflight ``OPTIONS`` request the browser sends first.

The origin itself is configured through ``CORS_ALLOW_ORIGINS`` so a deployment
can point at its own frontend instead of hard-coding a localhost default.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

FRONTEND_ORIGIN = "http://localhost:3000"


def test_preflight_request_is_allowed_for_the_configured_origin(api_client: TestClient) -> None:
    response = api_client.options(
        "/auth/token",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
    assert "POST" in response.headers["access-control-allow-methods"]
    assert response.headers["access-control-allow-credentials"] == "true"


def test_actual_request_carries_the_allow_origin_header(api_client: TestClient) -> None:
    response = api_client.get("/healthz", headers={"Origin": FRONTEND_ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


def test_unknown_origin_is_not_echoed_back(api_client: TestClient) -> None:
    response = api_client.get(
        "/healthz", headers={"Origin": "http://evil.example.com"}
    )

    # The request still succeeds; the browser is the component that refuses to
    # hand the body to the page when the header is missing.
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_origins_are_configurable_and_trimmed() -> None:
    settings = Settings(
        _env_file=None,
        cors_allow_origins="https://app.example.com , http://localhost:5173,",
    )

    assert settings.cors_origins == [
        "https://app.example.com",
        "http://localhost:5173",
    ]


def test_default_origins_cover_the_local_frontend() -> None:
    settings = Settings(_env_file=None)

    assert "http://localhost:3000" in settings.cors_origins
    assert "http://127.0.0.1:3000" in settings.cors_origins


def test_empty_configuration_disables_the_middleware() -> None:
    app = create_app(Settings(_env_file=None, cors_allow_origins=""))
    app.state.db.create_all()
    try:
        with TestClient(app) as client:
            response = client.get(
                "/healthz", headers={"Origin": FRONTEND_ORIGIN}
            )
    finally:
        app.state.db.drop_all()
        app.state.db.dispose()

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
