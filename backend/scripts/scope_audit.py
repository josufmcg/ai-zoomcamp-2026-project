"""Scope audit: compare every list endpoint against an independent expectation.

This is a verification script, not part of the test suite. It seeds two
communities, two managers, and two residents, then recomputes the expected
result set for each list endpoint directly from the models and compares it with
the API response. Its purpose is to catch the class of bug where a correlated
``EXISTS`` silently degrades into a cartesian product (which returns too many
rows) or a duplicate join (which raises).

Run with: uv run python scripts/scope_audit.py
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

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
    OwnershipType,
    Tag,
    Unit,
    UnitAssignment,
    UnitType,
    User,
    UserRole,
    Vote,
)
from app.security import hash_password

PASSWORD = "password123"
WIPE_ORDER = (
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


def _login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post("/auth/token", data={"username": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def build_fixtures(app) -> dict:
    """Seed two communities with distinct managers, residents, and records."""
    with app.state.db.session() as session:
        for model in WIPE_ORDER:
            session.execute(delete(model))
        session.commit()

        users = {
            name: User(
                email=f"{name}@audit.test",
                hashed_password=hash_password(PASSWORD),
                role=role,
            )
            for name, role in (
                ("admin", UserRole.ADMINISTRATOR),
                ("managerA", UserRole.MANAGER),
                ("managerB", UserRole.MANAGER),
                ("residentA", UserRole.RESIDENT),
                ("residentB", UserRole.RESIDENT),
            )
        }
        session.add_all(users.values())
        session.commit()
        for user in users.values():
            session.refresh(user)

        fixtures: dict = {"users": users, "units": {}, "communities": {}}
        for label, community_name, manager_name, resident_name, unit_ids in (
            ("A", "Community A", "managerA", "residentA", ["A-1", "A-2", "A-3"]),
            ("B", "Community B", "managerB", "residentB", ["B-1", "B-2"]),
        ):
            community = Community(name=community_name)
            building = Building(name=f"Block {label}", community=community)
            tag = Tag(name=f"tag-{label}")
            session.add(community)
            session.commit()
            session.add(
                ManagerAssignment(manager_id=users[manager_name].id, community_id=community.id)
            )
            units = []
            for index, identifier in enumerate(unit_ids):
                unit = Unit(
                    identifier=identifier,
                    unit_type=UnitType.APARTMENT if index == 0 else UnitType.GARAGE,
                    building=building,
                    tags=[tag] if index == 1 else [],
                )
                session.add(unit)
                units.append(unit)
            session.commit()
            for unit in units:
                session.refresh(unit)
                session.add(
                    UnitAssignment(
                        user_id=users[resident_name].id,
                        unit_id=unit.id,
                        ownership_type=OwnershipType.OWNER,
                    )
                )
            session.commit()

            # One bill and one incidence per unit, all created by that
            # community's manager and owned by that community's resident.
            for unit in units:
                session.add(
                    Bill(
                        unit_id=unit.id,
                        amount="10.00",
                        description=f"bill {unit.identifier}",
                        issue_date=date.today(),
                        due_date=date.today() + timedelta(days=30),
                    )
                )
                session.add(
                    Incidence(
                        unit_id=unit.id,
                        created_by_id=users[resident_name].id,
                        title=f"incidence {unit.identifier}",
                        description="audit",
                    )
                )
            session.commit()
            fixtures["communities"][label] = community
            fixtures["units"][label] = units
            for value in users.values():
                session.refresh(value)

        for user in users.values():
            session.refresh(user)
        for label in ("A", "B"):
            fixtures["communities"][label] = session.get(
                Community, fixtures["communities"][label].id
            )
            fixtures["units"][label] = [
                session.get(Unit, unit.id) for unit in fixtures["units"][label]
            ]
        session.expunge_all()
        return fixtures


def main() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://efinges:efinges@127.0.0.1:5432/efinges",
        secret_key="audit-secret-key-at-least-32-bytes-long",
    )
    app = create_app(settings)
    app.state.db.create_all()
    fixtures = build_fixtures(app)
    db = app.state.db

    with db.session() as session:
        units_a = [unit.id for unit in fixtures["units"]["A"]]
        units_b = [unit.id for unit in fixtures["units"]["B"]]

    checks: list[tuple[str, str, str, set, set]] = []
    with TestClient(app) as client:
        headers = {name: _login(client, user.email) for name, user in fixtures["users"].items()}

        def collect(label, path, who, expected_ids, key="id"):
            """Compare the endpoint's rows with an independent expectation.

            ``key`` is ``"id"`` for the property endpoints and ``"unit_id"``
            for bills and incidences, where the record is keyed by the unit it
            belongs to rather than by its own id.
            """
            response = client.get(path, headers=headers[who])
            assert response.status_code == 200, f"{path} ({who}): {response.text}"
            got = {row[key] for row in response.json()}
            checks.append((label, path, who, got, set(expected_ids)))

        all_units = set(units_a + units_b)
        collect("admin units", "/units", "admin", all_units)
        collect("managerA units", "/units", "managerA", set(units_a))
        collect("managerB units", "/units", "managerB", set(units_b))
        collect("residentA units", "/units", "residentA", set(units_a))
        collect("residentB units", "/units", "residentB", set(units_b))

        community_a = fixtures["communities"]["A"].id
        community_b = fixtures["communities"]["B"].id
        building_a = fixtures["units"]["A"][0].building_id
        collect(
            "managerA units by community",
            f"/units?community_id={community_a}",
            "managerA",
            set(units_a),
        )
        collect(
            "managerA units by other community",
            f"/units?community_id={community_b}",
            "managerA",
            set(),
        )
        collect(
            "managerA units by building",
            f"/units?building_id={building_a}",
            "managerA",
            set(units_a),
        )
        collect(
            "residentA units by other community",
            f"/units?community_id={community_b}",
            "residentA",
            set(),
        )

        collect("admin bills", "/bills", "admin", all_units, key="unit_id")
        collect("managerA bills", "/bills", "managerA", set(units_a), key="unit_id")
        collect("managerB bills", "/bills", "managerB", set(units_b), key="unit_id")
        collect("residentA bills", "/bills", "residentA", set(units_a), key="unit_id")
        collect("residentB bills", "/bills", "residentB", set(units_b), key="unit_id")
        unit_a = fixtures["units"]["A"][0].id
        collect(
            "managerA bills filtered",
            f"/bills?unit_id={unit_a}",
            "managerA",
            {unit_a},
            key="unit_id",
        )

        collect("admin incidences", "/incidences", "admin", all_units, key="unit_id")
        collect("managerA incidences", "/incidences", "managerA", set(units_a), key="unit_id")
        collect("managerB incidences", "/incidences", "managerB", set(units_b), key="unit_id")
        collect("residentA incidences", "/incidences", "residentA", set(units_a), key="unit_id")
        collect(
            "managerB incidences filter",
            "/incidences?status=submitted",
            "managerB",
            set(units_b),
            key="unit_id",
        )

        # Buildings are identified by building id, not unit id.
        with db.session() as session:
            buildings_a = set(
                session.scalars(
                    select(Building.id).where(
                        Building.community_id == fixtures["communities"]["A"].id
                    )
                ).all()
            )
            buildings_b = set(
                session.scalars(
                    select(Building.id).where(
                        Building.community_id == fixtures["communities"]["B"].id
                    )
                ).all()
            )
        collect("admin buildings", "/buildings", "admin", buildings_a | buildings_b)
        collect("managerA buildings", "/buildings", "managerA", buildings_a)
        collect("residentA buildings", "/buildings", "residentA", buildings_a)
        collect(
            "managerA buildings filtered",
            f"/buildings?community_id={community_a}",
            "managerA",
            buildings_a,
        )

        communities_a = {fixtures["communities"]["A"].id}
        communities_b = {fixtures["communities"]["B"].id}
        collect("admin communities", "/communities", "admin", communities_a | communities_b)
        collect("managerA communities", "/communities", "managerA", communities_a)
        collect("residentB communities", "/communities", "residentB", communities_b)

    failures = [
        (label, path, who, got, want) for label, path, who, got, want in checks if got != want
    ]
    for label, path, who, got, want in failures:
        print(f"MISMATCH {label}: {path} as {who}\n  got  {sorted(got)}\n  want {sorted(want)}")
    assert not failures, f"{len(failures)} scope mismatches"
    app.state.db.dispose()
    print(f"SCOPE AUDIT OK: {len(checks)} checks passed")


if __name__ == "__main__":
    main()
