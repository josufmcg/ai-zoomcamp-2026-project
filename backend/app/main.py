"""EFINGES backend application factory.

The application is built by :func:`create_app`, which keeps the app
configurable for tests and for the different deployment environments.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.database import Database
from app.routers import (
    assignments,
    auth,
    bills,
    governance,
    incidences,
    property,
    users,
)
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

    # Allow the browser SPA to call the API (backlog task 14). The SPA runs on
    # a different origin than the API, so without this the browser blocks every
    # cross-origin response even though the request reached the server.
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        """Liveness probe used by Docker health checks and smoke tests."""
        return {"status": "ok"}

    # Authentication and user endpoints (backlog task 6).
    app.include_router(auth.router)

    # Resident and unit assignment endpoints (backlog task 7).
    app.include_router(assignments.router)

    # Property tree, tags, and manager assignments (backlog task 8).
    # Order matters: the fixed /manager-assignments path must be registered
    # before any dynamic /{resource}/{id} route from later routers.
    app.include_router(property.router)

    # Administrator user management (backlog task 9).
    app.include_router(users.router)

    # Manual bills (backlog task 10).
    app.include_router(bills.router)

    # Incidences and comment threads (backlog task 11).
    app.include_router(incidences.router)

    # Initiatives and per-unit voting (backlog task 12).
    app.include_router(governance.router)

    return app


# Module-level instance for `uv run uvicorn app.main:app` and ASGI servers.
app = create_app()
