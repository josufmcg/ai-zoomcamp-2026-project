"""Shared pytest fixtures for the backend test suite."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Database
from app.main import create_app
from app.models import (
    Building,
    Community,
    ManagerAssignment,
    OwnershipType,
    Tag,
    Unit,
    UnitAssignment,
    UnitType,
    User,
    UserRole,
)
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


@dataclass(frozen=True)
class PropertyTree:
    """A community with one building and three units of different types."""

    community: Community
    building: Building
    apartment: Unit
    garage: Unit
    storage: Unit

    @property
    def units(self) -> tuple[Unit, Unit, Unit]:
        """Every unit in the tree, in a stable order."""
        return (self.apartment, self.garage, self.storage)


@pytest.fixture
def create_property_tree(api_app: FastAPI) -> Callable[..., PropertyTree]:
    """Return a helper that inserts a small property hierarchy.

    Backlog task 8 adds the property CRUD endpoints; until then tests seed the
    hierarchy directly against the app database, mirroring ``create_user``.
    """

    def _create_property_tree(name: str = "Riverside") -> PropertyTree:
        with api_app.state.db.session() as db_session:
            community = Community(name=name)
            building = Building(name="Block A", community=community)
            apartment = Unit(
                identifier="A-101",
                unit_type=UnitType.APARTMENT,
                building=building,
            )
            garage = Unit(
                identifier="G-01",
                unit_type=UnitType.GARAGE,
                building=building,
            )
            storage = Unit(
                identifier="S-01",
                unit_type=UnitType.STORAGE,
                building=building,
            )
            db_session.add(community)
            db_session.commit()
            for row in (community, building, apartment, garage, storage):
                db_session.refresh(row)
                db_session.expunge(row)
        return PropertyTree(
            community=community,
            building=building,
            apartment=apartment,
            garage=garage,
            storage=storage,
        )

    return _create_property_tree


@pytest.fixture
def assign_unit(api_app: FastAPI) -> Callable[..., UnitAssignment]:
    """Return a helper that assigns a resident to a unit directly."""

    def _assign_unit(
        user: User,
        unit: Unit,
        ownership_type: OwnershipType = OwnershipType.OWNER,
    ) -> UnitAssignment:
        with api_app.state.db.session() as db_session:
            assignment = UnitAssignment(
                user_id=user.id,
                unit_id=unit.id,
                ownership_type=ownership_type,
            )
            db_session.add(assignment)
            db_session.commit()
            db_session.refresh(assignment)
            db_session.expunge(assignment)
        return assignment

    return _assign_unit


@pytest.fixture
def assign_manager(api_app: FastAPI) -> Callable[..., ManagerAssignment]:
    """Return a helper that gives a manager access to a community directly.

    The public endpoint is ``POST /manager-assignments`` (administrator only),
    but most property tests need a manager with a scope without also exercising
    user management, so the row is seeded directly like ``create_user``.
    """

    def _assign_manager(
        manager: User, community: Community
    ) -> ManagerAssignment:
        with api_app.state.db.session() as db_session:
            assignment = ManagerAssignment(
                manager_id=manager.id, community_id=community.id
            )
            db_session.add(assignment)
            db_session.commit()
            db_session.refresh(assignment)
            db_session.expunge(assignment)
        return assignment

    return _assign_manager


@pytest.fixture
def create_tag(api_app: FastAPI) -> Callable[..., Tag]:
    """Return a helper that inserts a tag directly into the app database."""

    def _create_tag(name: str) -> Tag:
        with api_app.state.db.session() as db_session:
            tag = Tag(name=name)
            db_session.add(tag)
            db_session.commit()
            db_session.refresh(tag)
            db_session.expunge(tag)
        return tag

    return _create_tag


@pytest.fixture
def db_session(api_app: FastAPI) -> Iterator[Session]:
    """A session on the application's database, for asserting stored rows.

    Tests that check what was *persisted* (a bill's stored status, a hashed
    password) use this instead of the HTTP response, so they can prove the
    response is not just hiding the truth.
    """
    session = api_app.state.db.session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def login(api_client: TestClient) -> Callable[..., str]:
    """Return a helper that logs a user in and returns the access token."""

    def _login(email: str, password: str = "correct horse battery staple") -> str:
        response = api_client.post(
            "/auth/token",
            data={"username": email, "password": password},
        )
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    return _login


@pytest.fixture
def auth_token(
    login: Callable[..., str],
) -> Callable[[User], dict[str, str]]:
    """Return a helper that logs a user in and returns the request headers."""

    def _auth_token(user: User) -> dict[str, str]:
        return auth_header(login(user.email))

    return _auth_token


def auth_header(token: str) -> dict[str, str]:
    """Return the ``Authorization`` header for a bearer token."""
    return {"Authorization": f"Bearer {token}"}
