"""Fixtures shared by the integration workflows (backlog task 18).

The unit suite runs against an in-memory SQLite database that is created and
dropped for every test. The integration suite instead runs against a *dedicated*
database named by ``TEST_DATABASE_URL`` (PostgreSQL when the Docker stack is
up), so the workflows exercise the real server: native enums, JSON columns,
``NUMERIC`` money, and unique constraints behave exactly as they do in
production.

Isolation without dropping the database
---------------------------------------
The database is assumed to be dedicated to the tests, so the tables are wiped
before every test instead of dropping and recreating the schema. The wipe order
matters: child rows go before their parents because both PostgreSQL and SQLite
enforce the foreign keys, and the tag association tables go first because they
reference buildings and units.

One application for the whole session
-------------------------------------
The application is built once and shared by every workflow. That matters for
the default in-memory SQLite database, where each engine gets its own private
database: a fresh application per test would see an empty schema. Sharing one
application keeps the default ``TEST_DATABASE_URL`` working while PostgreSQL
users simply point the variable at their dedicated server.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import Settings
from app.main import create_app
from app.models import (
    Bill,
    Building,
    Comment,
    Community,
    Incidence,
    Initiative,
    InitiativeOption,
    ManagerAssignment,
    Tag,
    Unit,
    UnitAssignment,
    User,
    UserRole,
    Vote,
    building_tags,
    unit_tags,
)
from app.security import hash_password
from tests.integration.helpers import PASSWORD, Account

# Children before parents; the tag association tables reference buildings and
# units, so they are cleared first.
WIPE_ORDER = (
    building_tags,
    unit_tags,
    Vote,
    InitiativeOption,
    Initiative,
    Comment,
    Incidence,
    Bill,
    UnitAssignment,
    ManagerAssignment,
    Unit,
    Building,
    Community,
    User,
    Tag,
)


@pytest.fixture(scope="session")
def integration_settings() -> Settings:
    """Settings for the integration database, with a fixed signing secret.

    ``DATABASE_URL`` is overridden with ``TEST_DATABASE_URL`` so the application
    targets the dedicated integration database rather than the development one.
    Point ``TEST_DATABASE_URL`` at the Docker PostgreSQL to run the workflows
    against the real server.
    """
    settings = Settings(_env_file=None)
    settings.database_url = settings.test_database_url
    settings.secret_key = "integration-secret-key-at-least-32-bytes"
    return settings


@pytest.fixture(scope="session")
def integration_app(integration_settings: Settings) -> Iterator[FastAPI]:
    """The application on the integration database, built once per session."""
    app = create_app(integration_settings)
    app.state.db.create_all()
    try:
        yield app
    finally:
        app.state.db.drop_all()
        app.state.db.dispose()


@pytest.fixture
def client(integration_app: FastAPI) -> Iterator[TestClient]:
    """A TestClient on a clean database.

    The client is *not* used as a context manager, so the application lifespan
    does not run per test. The lifespan disposes the engine on shutdown, which
    would destroy the session-scoped in-memory SQLite database after the first
    test; the workflows do not depend on lifespan side effects (telemetry), so
    skipping it keeps the default ``TEST_DATABASE_URL`` working while a real
    PostgreSQL server is unaffected.
    """
    with integration_app.state.db.session() as session:
        for model in WIPE_ORDER:
            session.execute(delete(model))
        session.commit()
    yield TestClient(integration_app)


@pytest.fixture
def db_session(integration_app: FastAPI) -> Iterator[Session]:
    """A session on the integration database, for asserting stored rows.

    Workflows use this to prove what was *persisted* (a bill's stored status, a
    hashed password) rather than trusting the HTTP response.
    """
    session = integration_app.state.db.session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def bootstrap_admin(integration_app: FastAPI, db_session: Session) -> Account:
    """Seed the first administrator directly, then use the public API.

    ``POST /users`` is administrator-only, so the very first account cannot be
    created over HTTP. A workflow seeds that one row directly (the way a firm
    provisions its first administrator) and creates every other account through
    ``POST /users``.
    """
    admin = User(
        email="admin@integration.test",
        hashed_password=hash_password(PASSWORD),
        role=UserRole.ADMINISTRATOR,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return Account(id=admin.id, email=admin.email, role=admin.role)
