"""Shared pytest fixtures for the backend test suite."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Database


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
