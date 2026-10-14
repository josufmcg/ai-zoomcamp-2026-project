"""Shared pytest fixtures for the backend test suite."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Database
from app.main import create_app
from app.models import User, UserRole
from app.security import hash_password


@pytest.fixture
def settings() -> Settings:
    """Settings with no ``.env`` file, using the in-memory test database."""
    return Settings(_env_file=None)


@pytest.fixture
def database(settings: Settings) -> Iterator[Database]:
    """A fresh database with every table created, dropped after the test."""
    db = Database(settings.test_database_url)
    db.create_all()
    try:
        yield db
    finally:
        db.drop_all()
        db.dispose()


@pytest.fixture
def session(database: Database) -> Iterator[Session]:
    """A session bound to the test database, closed after the test."""
    session = database.session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api_settings() -> Settings:
    """Settings pointing the application at an in-memory database.

    Uses a fixed ``SECRET_KEY`` (at least 32 bytes, as HMAC-SHA256 expects) so
    tests can decode the tokens the app issues.
    """
    return Settings(
        _env_file=None,
        database_url="sqlite:///:memory:",
        secret_key="test-secret-key-at-least-32-bytes-long",
    )


@pytest.fixture
def api_app(api_settings: Settings) -> Iterator[FastAPI]:
    """An application built from :func:`api_settings` with tables created."""
    app = create_app(api_settings)
    app.state.db.create_all()
    try:
        yield app
    finally:
        app.state.db.drop_all()
        app.state.db.dispose()


@pytest.fixture
def api_client(api_app: FastAPI) -> Iterator[TestClient]:
    """A TestClient for :func:`api_app`, running the lifespan on enter/exit."""
    with TestClient(api_app) as client:
        yield client


@pytest.fixture
def create_user(api_app: FastAPI) -> Callable[..., User]:
    """Return a helper that inserts a user directly into the app database.

    There is no user-creation endpoint yet (that arrives in backlog task 9), so
    tests seed accounts by writing rows and hashing the password.
    """

    def _create_user(
        email: str,
        password: str = "correct horse battery staple",
        role: UserRole = UserRole.RESIDENT,
        *,
        is_active: bool = True,
    ) -> User:
        with api_app.state.db.session() as db_session:
            user = User(
                email=email,
                hashed_password=hash_password(password),
                role=role,
                is_active=is_active,
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            db_session.expunge(user)
        return user

    return _create_user
