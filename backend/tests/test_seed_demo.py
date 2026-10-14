"""Tests for the demo seed script (backlog task 23).

These tests run the seed against a real (in-memory) database rather than
mocking it, because the whole point of the script is that the rows it creates
are coherent: the counts, the three bill statuses, the incidence lifecycle, and
the per-unit ballots all have to line up. A second run must create nothing, and
``--reset`` must remove only what the seed owns.
"""

from __future__ import annotations

from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import Database
from app.models import (
    Bill,
    Building,
    Comment,
    Community,
    Incidence,
    IncidenceStatus,
    Initiative,
    ManagerAssignment,
    Tag,
    Unit,
    UnitAssignment,
    UnitType,
    User,
    UserRole,
    Vote,
)
from scripts.seed_demo import (
    ADMIN_EMAIL,
    DEMO_PASSWORD,
    MANAGER_EMAIL,
    RESIDENT_EMAILS,
    run,
)


def _count(database: Database, model) -> int:
    """Return the number of rows of ``model`` in ``database``."""
    with database.session() as session:
        return session.scalar(select(func.count()).select_from(model)) or 0


def _login(client: TestClient, email: str) -> dict[str, str]:
    """Sign in through ``POST /auth/token`` and return request headers."""
    response = client.post(
        "/auth/token",
        data={"username": email, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_seed_creates_the_full_demo_scenario(database: Database) -> None:
    run(database)

    assert _count(database, User) == 5
    assert _count(database, Community) == 1
    assert _count(database, Building) == 2
    assert _count(database, Unit) == 8
    assert _count(database, Tag) == 4
    assert _count(database, ManagerAssignment) == 1
    assert _count(database, UnitAssignment) == 7
    assert _count(database, Bill) == 4
    assert _count(database, Incidence) == 4
    assert _count(database, Comment) == 7
    assert _count(database, Initiative) == 1
    assert _count(database, Vote) == 2

    with database.session() as session:
        roles = session.execute(select(User.role, func.count()).group_by(User.role)).all()
        assert dict(roles) == {
            UserRole.ADMINISTRATOR: 1,
            UserRole.MANAGER: 1,
            UserRole.RESIDENT: 3,
        }

        unit_types = session.execute(
            select(Unit.unit_type, func.count()).group_by(Unit.unit_type)
        ).all()
        assert dict(unit_types) == {
            UnitType.APARTMENT: 4,
            UnitType.GARAGE: 2,
            UnitType.STORAGE: 2,
        }

        emails = set(session.scalars(select(User.email)).all())
        assert emails == {ADMIN_EMAIL, MANAGER_EMAIL, *RESIDENT_EMAILS}


def test_seed_is_idempotent(database: Database) -> None:
    first = run(database)
    assert first.total_created() > 0
    user_count = _count(database, User)

    second = run(database)

    assert second.total_created() == 0
    assert all(created == 0 for created in second.created.values())
    assert _count(database, User) == user_count
    assert _count(database, UnitAssignment) == 7
    assert _count(database, Vote) == 2


def test_seed_bills_cover_pending_paid_and_overdue(database: Database) -> None:
    run(database)
    today = date.today()

    with database.session() as session:
        bills = session.scalars(select(Bill)).all()
        statuses = {bill.display_status(today).value for bill in bills}

    # ``overdue`` is never stored; it is computed from the past due date of a
    # pending bill, so all three display statuses appear in one seed.
    assert statuses == {"pending", "paid", "overdue"}
    assert all(bill.status.value in {"pending", "paid"} for bill in bills)


def test_seed_covers_every_incidence_stage_with_comments(database: Database) -> None:
    run(database)

    with database.session() as session:
        incidences = session.scalars(select(Incidence)).all()
        stages = {incidence.status for incidence in incidences}
        # Every incidence has a thread, and each starts with the reporter.
        assert all(incidence.comments for incidence in incidences)

    assert stages == {
        IncidenceStatus.SUBMITTED,
        IncidenceStatus.IN_PROGRESS,
        IncidenceStatus.RESOLVED,
        IncidenceStatus.CLOSED,
    }


def test_seed_initiative_is_open_and_scoped_to_garages(database: Database) -> None:
    run(database)

    with database.session() as session:
        initiative = session.scalars(select(Initiative)).one()
        assert initiative.is_open_on(date.today())
        assert initiative.scope == {"unit_types": ["garage"]}
        assert len(initiative.options) == 3
        votes = session.scalars(select(Vote).where(Vote.initiative_id == initiative.id)).all()

    assert len(votes) == 2
    assert {vote.option_id for vote in votes} == {initiative.options[0].id}


def test_seeded_accounts_can_sign_in_and_see_their_own_data(
    api_app: FastAPI,
    api_client: TestClient,
) -> None:
    # Seed the demo into the application's own database so the HTTP API sees it.
    run(api_app.state.db)

    resident_headers = _login(api_client, RESIDENT_EMAILS[0])
    units = api_client.get("/auth/me/units", headers=resident_headers).json()
    bills = api_client.get("/bills", headers=resident_headers).json()

    # Alice holds two units and one bill each (one pending, one paid).
    assert {unit["identifier"] for unit in units} == {"A-101", "G-01"}
    assert {bill["unit_identifier"] for bill in bills} == {"A-101", "G-01"}

    manager_headers = _login(api_client, MANAGER_EMAIL)
    assignments = api_client.get("/assignments", headers=manager_headers).json()
    assert len(assignments) == 7


def test_seeded_administrator_sees_the_global_overview(
    api_app: FastAPI,
    api_client: TestClient,
) -> None:
    run(api_app.state.db)
    admin_headers = _login(api_client, ADMIN_EMAIL)

    communities = api_client.get("/communities", headers=admin_headers).json()
    buildings = api_client.get("/buildings", headers=admin_headers).json()
    units = api_client.get("/units", headers=admin_headers).json()
    users = api_client.get("/users", headers=admin_headers).json()

    assert len(communities) == 1
    assert len(buildings) == 2
    assert len(units) == 8
    assert len(users) == 5


def test_reset_removes_only_demo_rows(database: Database) -> None:
    run(database)

    # A hand-made community and account must survive a reset.
    with database.session() as session:
        session.add(Community(name="Handmade Community"))
        session.add(
            User(
                email="outsider@example.test",
                hashed_password="not-a-real-hash",
                role=UserRole.RESIDENT,
            )
        )
        session.commit()

    run(database, reset=True)

    with database.session() as session:
        community_names = set(session.scalars(select(Community.name)).all())
        emails = set(session.scalars(select(User.email)).all())

    assert community_names == {"Handmade Community", "Demo Riverside"}
    assert emails == {"outsider@example.test", *{ADMIN_EMAIL, MANAGER_EMAIL, *RESIDENT_EMAILS}}
