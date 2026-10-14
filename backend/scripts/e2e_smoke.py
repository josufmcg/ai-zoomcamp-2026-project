"""End-to-end smoke check for backlog tasks 8-13 against a real PostgreSQL.

This is a throwaway verification script (not part of the test suite): the
pytest suite runs against in-memory SQLite, so this proves the created
migrations and endpoints also work on the PostgreSQL server the Docker stack
uses. Run it with the compose postgres up:

    uv run python scripts/e2e_smoke.py
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import delete

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
)
from app.security import hash_password

DATABASE_URL = "postgresql+psycopg://efinges:efinges@127.0.0.1:5432/efinges"
PASSWORD = "password123"

# Wipe order matters: children before parents (SQLite/PostgreSQL both enforce
# the foreign keys, and this script runs against a development database).
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


def _seed_users(app) -> tuple[User, User, User]:
    """Reset the dev database and create one account per role."""
    with app.state.db.session() as session:
        for model in WIPE_ORDER:
            session.execute(delete(model))
        session.commit()
        users = [
            User(
                email=f"{role.value}@e2e.test",
                hashed_password=hash_password(PASSWORD),
                role=role,
            )
            for role in (UserRole.ADMINISTRATOR, UserRole.MANAGER, UserRole.RESIDENT)
        ]
        session.add_all(users)
        session.commit()
        for user in users:
            session.refresh(user)
            session.expunge(user)
        return users[0], users[1], users[2]


def _login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/token", data={"username": email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def main() -> None:
    settings = Settings(
        _env_file=None,
        database_url=DATABASE_URL,
        secret_key="e2e-secret-key-at-least-32-bytes-long",
    )
    app = create_app(settings)
    app.state.db.create_all()
    admin, manager, resident = _seed_users(app)

    with TestClient(app) as client:
        admin_h = _login(client, admin.email)
        manager_h = _login(client, manager.email)
        resident_h = _login(client, resident.email)

        # --- task 8: property CRUD and manager scope -------------------------
        community = client.post(
            "/communities", json={"name": "E2E Riverside"}, headers=admin_h
        ).json()
        denied = client.post(
            "/buildings",
            json={"community_id": community["id"], "name": "Block A"},
            headers=manager_h,
        )
        assert denied.status_code == 403, denied.text

        client.post(
            "/manager-assignments",
            json={"manager_id": manager.id, "community_id": community["id"]},
            headers=admin_h,
        ).raise_for_status()
        building = client.post(
            "/buildings",
            json={"community_id": community["id"], "name": "Block A"},
            headers=manager_h,
        ).json()
        tag = client.post(
            "/tags", json={"name": "E2E Downtown"}, headers=manager_h
        ).json()
        apartment = client.post(
            "/units",
            json={
                "building_id": building["id"],
                "identifier": "A-101",
                "unit_type": "apartment",
                "tag_ids": [tag["id"]],
            },
            headers=manager_h,
        ).json()
        garage = client.post(
            "/units",
            json={
                "building_id": building["id"],
                "identifier": "G-01",
                "unit_type": "garage",
            },
            headers=manager_h,
        ).json()
        assert apartment["tags"][0]["name"] == "E2E Downtown"

        for unit in (apartment, garage):
            response = client.post(
                "/assignments",
                json={
                    "user_id": resident.id,
                    "unit_id": unit["id"],
                    "ownership_type": "owner",
                },
                headers=manager_h,
            )
            assert response.status_code == 201, response.text
        mine = client.get("/auth/me/units", headers=resident_h).json()
        assert {row["identifier"] for row in mine} == {"A-101", "G-01"}, mine

        # --- task 10: bills, computed overdue, paid transition ---------------
        bill = client.post(
            "/bills",
            json={
                "unit_id": apartment["id"],
                "amount": "0.30",
                "description": "Rent",
                "issue_date": (date.today() - timedelta(days=5)).isoformat(),
                "due_date": (date.today() - timedelta(days=1)).isoformat(),
            },
            headers=manager_h,
        ).json()
        assert bill["status"] == "overdue", bill
        filtered = client.get(
            f"/bills?unit_id={apartment['id']}&status=overdue", headers=resident_h
        ).json()
        assert [row["id"] for row in filtered] == [bill["id"]], filtered
        paid = client.post(f"/bills/{bill['id']}/pay", headers=manager_h).json()
        assert paid["status"] == "paid", paid
        assert (
            client.get(f"/bills/{bill['id']}", headers=resident_h).json()["status"]
            == "paid"
        )

        # --- task 11: incidence lifecycle and comment thread -----------------
        incidence = client.post(
            "/incidences",
            json={
                "unit_id": apartment["id"],
                "title": "Leak",
                "description": "Dripping tap.",
            },
            headers=resident_h,
        ).json()
        assert incidence["status"] == "submitted"
        illegal = client.patch(
            f"/incidences/{incidence['id']}/status",
            json={"status": "resolved"},
            headers=manager_h,
        )
        assert illegal.status_code == 409, illegal.text
        for stage in ("in progress", "resolved", "closed"):
            response = client.patch(
                f"/incidences/{incidence['id']}/status",
                json={"status": stage},
                headers=manager_h,
            )
            assert response.status_code == 200, response.text
        for body, headers in (
            ("Any update?", resident_h),
            ("Fixed today.", manager_h),
        ):
            client.post(
                f"/incidences/{incidence['id']}/comments",
                json={"body": body},
                headers=headers,
            ).raise_for_status()
        thread = client.get(
            f"/incidences/{incidence['id']}/comments", headers=resident_h
        ).json()
        assert [row["body"] for row in thread] == [
            "Any update?",
            "Fixed today.",
        ], thread

        # --- task 12: initiative with scope and multi-unit voting ------------
        initiative = client.post(
            "/initiatives",
            json={
                "title": "Repaint?",
                "description": "Repaint the facade.",
                "opens_at": (date.today() - timedelta(days=1)).isoformat(),
                "closes_at": (date.today() + timedelta(days=7)).isoformat(),
                "options": [{"label": "Yes"}, {"label": "No"}],
                "scope": {"community_ids": [community["id"]]},
            },
            headers=manager_h,
        ).json()
        yes, no = (option["id"] for option in initiative["options"])
        for unit, option in ((apartment, yes), (garage, no)):
            response = client.post(
                f"/initiatives/{initiative['id']}/votes",
                json={"unit_id": unit["id"], "option_id": option},
                headers=resident_h,
            )
            assert response.status_code == 201, response.text
        duplicate = client.post(
            f"/initiatives/{initiative['id']}/votes",
            json={"unit_id": apartment["id"], "option_id": no},
            headers=resident_h,
        )
        assert duplicate.status_code == 409, duplicate.text
        results = client.get(
            f"/initiatives/{initiative['id']}/results", headers=resident_h
        ).json()
        assert results["total_votes"] == 2, results
        assert {row["label"]: row["votes"] for row in results["tallies"]} == {
            "Yes": 1,
            "No": 1,
        }, results

    app.state.db.dispose()
    print("E2E OK: backlog tasks 8-13 verified against PostgreSQL")


if __name__ == "__main__":
    main()
