"""EFINGES backend application factory.

The application is built by :func:`create_app`, which keeps the app
configurable for tests and for the different deployment environments.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.database import Database
from app.telemetry import RequestMetricsMiddleware, Telemetry


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return a configured FastAPI application."""
    settings = settings or get_settings()
    telemetry = Telemetry(settings)
    database = Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        # Emit a startup log record, then flush and stop the providers on
        # shutdown.
        telemetry.log_startup()
        yield
        telemetry.shutdown()
        database.dispose()

    app = FastAPI(title="EFINGES API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.telemetry = telemetry
    app.state.db = database

    # Count every request by matched route and response status code.
    app.add_middleware(RequestMetricsMiddleware, telemetry=telemetry)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        """Liveness probe used by Docker health checks and smoke tests."""
        return {"status": "ok"}

    return app


# Module-level instance for `uv run uvicorn app.main:app` and ASGI servers.
app = create_app()
