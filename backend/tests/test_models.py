"""Tests for the property hierarchy and tag models (backlog task 5)."""

from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Database
from app.models import Building, Community, Tag, Unit, UnitType, User, UserRole
from app.security import hash_password, verify_password


def _make_hierarchy(session: Session) -> tuple[Community, Building, Unit]:
    """Create a community with one building and one apartment unit."""
    community = Community(name="Riverside")
    building = Building(name="Block A", community=community)
    unit = Unit(identifier="A-101", unit_type=UnitType.APARTMENT, building=building)
    session.add(community)
    session.commit()
    return community, building, unit


def test_hierarchy_creation_persists_relationships(session: Session) -> None:
    community, building, unit = _make_hierarchy(session)

    assert community.id is not None
    assert building.id is not None
    assert unit.id is not None

    # Relationships are navigable in both directions.
    assert building.community is community
    assert unit.building is building
    assert community.buildings == [building]
    assert building.units == [unit]
    assert unit.unit_type is UnitType.APARTMENT


def test_all_unit_types_are_accepted(session: Session) -> None:
    community = Community(name="Riverside")
    building = Building(name="Block A", community=community)
    for identifier, unit_type in (
        ("A-101", UnitType.APARTMENT),
        ("G-01", UnitType.GARAGE),
        ("S-01", UnitType.STORAGE),
    ):
        Unit(identifier=identifier, unit_type=unit_type, building=building)
    session.add(community)
    session.commit()

    stored = session.scalars(select(Unit.unit_type).order_by(Unit.identifier)).all()
    assert stored == [UnitType.APARTMENT, UnitType.GARAGE, UnitType.STORAGE]


def test_invalid_unit_type_is_rejected_by_the_orm(session: Session) -> None:
    community = Community(name="Riverside")
    building = Building(name="Block A", community=community)
    session.add(community)
    session.commit()

    # SQLAlchemy validates the enum value when the row is flushed.
    session.add(Unit(identifier="X-1", unit_type="penthouse", building=building))
    with pytest.raises(StatementError):
        session.commit()
    session.rollback()


def test_invalid_unit_type_is_rejected_by_the_database(session: Session) -> None:
    """A direct SQL insert bypassing the ORM is still rejected by the CHECK."""
    _, building, _ = _make_hierarchy(session)

    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO units (building_id, identifier, unit_type) "
                "VALUES (:building_id, :identifier, :unit_type)"
            ),
            {"building_id": building.id, "identifier": "X-1", "unit_type": "penthouse"},
        )
        session.commit()
    session.rollback()


def test_tags_attach_to_buildings_and_units(session: Session) -> None:
    _, building, unit = _make_hierarchy(session)
    downtown = Tag(name="Downtown")
    phase_one = Tag(name="Phase 1")
    building.tags.append(downtown)
    unit.tags.extend([downtown, phase_one])
    session.commit()

    session.expire_all()
    stored_building = session.get(Building, building.id)
    stored_unit = session.get(Unit, unit.id)
    assert [tag.name for tag in stored_building.tags] == ["Downtown"]
    assert [tag.name for tag in stored_unit.tags] == ["Downtown", "Phase 1"]
    # The same tag row is shared across buildings and units.
    assert downtown.buildings == [stored_building]
    assert downtown.units == [stored_unit]


def test_tag_names_are_unique(session: Session) -> None:
    session.add(Tag(name="Downtown"))
    session.commit()

    session.add(Tag(name="Downtown"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_building_names_are_unique_within_a_community(session: Session) -> None:
    community = Community(name="Riverside")
    session.add_all(
        [
            Building(name="Block A", community=community),
            Building(name="Block A", community=community),
        ]
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_unit_identifiers_are_unique_within_a_building(session: Session) -> None:
    community = Community(name="Riverside")
    building = Building(name="Block A", community=community)
    session.add_all(
        [
            Unit(identifier="A-101", unit_type=UnitType.APARTMENT, building=building),
            Unit(identifier="A-101", unit_type=UnitType.GARAGE, building=building),
        ]
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_deleting_a_community_cascades_to_buildings_and_units(session: Session) -> None:
    community, building, unit = _make_hierarchy(session)

    session.delete(community)
    session.commit()

    assert session.get(Building, building.id) is None
    assert session.get(Unit, unit.id) is None


def test_development_and_test_database_urls_are_separate() -> None:
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///./efinges.db"
    assert settings.test_database_url == "sqlite:///:memory:"
    assert settings.database_url != settings.test_database_url


def test_test_database_url_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv(
        "TEST_DATABASE_URL", "postgresql+psycopg://efinges:efinges@localhost/efinges_test"
    )
    settings = Settings(_env_file=None)
    assert (
        settings.test_database_url == "postgresql+psycopg://efinges:efinges@localhost/efinges_test"
    )


def test_in_memory_database_is_shared_across_sessions(database: Database) -> None:
    """The StaticPool keeps the in-memory database alive between sessions."""
    with database.session() as first:
        first.add(Community(name="Riverside"))
        first.commit()

    with database.session() as second:
        assert second.scalars(select(Community.name)).all() == ["Riverside"]


# --- Users and roles (backlog task 6) ---------------------------------------


def test_user_creation_persists_a_hashed_password(session: Session) -> None:
    password = "correct horse battery staple"
    user = User(
        email="manager@efinges.test",
        hashed_password=hash_password(password),
        role=UserRole.MANAGER,
    )
    session.add(user)
    session.commit()

    assert user.id is not None
    assert user.role is UserRole.MANAGER
    assert user.is_active is True
    assert password not in user.hashed_password
    assert verify_password(password, user.hashed_password)


def test_all_user_roles_are_accepted(session: Session) -> None:
    for email, role in (
        ("admin@efinges.test", UserRole.ADMINISTRATOR),
        ("manager@efinges.test", UserRole.MANAGER),
        ("resident@efinges.test", UserRole.RESIDENT),
    ):
        session.add(User(email=email, hashed_password="hash", role=role))
    session.commit()

    stored = session.scalars(select(User.role).order_by(User.email)).all()
    assert stored == [UserRole.ADMINISTRATOR, UserRole.MANAGER, UserRole.RESIDENT]


def test_invalid_role_is_rejected_by_the_orm(session: Session) -> None:
    session.add(User(email="x@efinges.test", hashed_password="hash", role="owner"))
    with pytest.raises(StatementError):
        session.commit()
    session.rollback()


def test_invalid_role_is_rejected_by_the_database(session: Session) -> None:
    """A direct SQL insert bypassing the ORM is still rejected by the CHECK."""
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO users (email, hashed_password, role, is_active) "
                "VALUES (:email, :hashed_password, :role, :is_active)"
            ),
            {
                "email": "x@efinges.test",
                "hashed_password": "hash",
                "role": "owner",
                "is_active": True,
            },
        )
        session.commit()
    session.rollback()


def test_user_emails_are_unique(session: Session) -> None:
    session.add(User(email="dup@efinges.test", hashed_password="h", role=UserRole.RESIDENT))
    session.commit()

    session.add(User(email="dup@efinges.test", hashed_password="h", role=UserRole.MANAGER))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
