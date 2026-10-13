"""EFINGES backend application factory.

The application is built by :func:`create_app`, which keeps the app
configurable for tests and for the different deployment environments.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return a configured FastAPI application."""
    settings = settings or get_settings()

    app = FastAPI(title="EFINGES API", version="0.1.0")
    app.state.settings = settings

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        """Liveness probe used by Docker health checks and smoke tests."""
        return {"status": "ok"}

    return app


# Module-level instance for `uv run uvicorn app.main:app` and ASGI servers.
app = create_app()
