"""Small shared helpers for the integration workflows (backlog task 18).

The workflows create every account and every property through the public HTTP
API, so these helpers only wrap the two things that repeat in all three:
signing in and asserting that a role boundary or a scope boundary was
enforced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

from app.models import UserRole

# Shared password for the accounts the workflows create. The length only has
# to satisfy ``UserCreate`` (at least eight characters).
PASSWORD = "integration-password-123"


@dataclass(frozen=True)
class Account:
    """One account created through ``POST /users`` by a workflow."""

    id: int
    email: str
    role: UserRole
    password: str = PASSWORD

    def sign_in(self, client: TestClient) -> dict[str, str]:
        """Log in through ``POST /auth/token`` and return request headers."""
        response = client.post(
            "/auth/token",
            data={"username": self.email, "password": self.password},
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}


@dataclass(frozen=True)
class Workflow:
    """A fully provisioned three-role scenario used by every workflow.

    It holds the accounts, the property tree, and the ready-to-use request
    headers, so a workflow test only contains the behavior it is responsible
    for instead of repeating the setup.
    """

    admin: Account
    manager: Account
    resident: Account
    community: dict[str, Any]
    building: dict[str, Any]
    apartment: dict[str, Any]
    garage: dict[str, Any]
    admin_headers: dict[str, str]
    manager_headers: dict[str, str]
    resident_headers: dict[str, str]

    @property
    def resident_unit_ids(self) -> list[int]:
        """The ids of the units assigned to the resident, in a stable order."""
        return [self.apartment["id"], self.garage["id"]]



def assert_denied(response: Any) -> None:
    """Assert a role boundary answered 401 (no token) or 403 (wrong role)."""
    assert response.status_code in (401, 403), (
        "expected 401/403 at a role boundary, got "
        f"{response.status_code}: {response.text}"
    )


def assert_hidden(response: Any) -> None:
    """Assert an out-of-scope resource is hidden behind a 404.

    The API answers 404 rather than 403 for a property, bill, or incidence
    outside the caller's scope, so an id cannot be probed for existence.
    """
    assert response.status_code == 404, (
        "expected 404 for an out-of-scope resource, got "
        f"{response.status_code}: {response.text}"
    )


def created(
    client: TestClient,
    method: str,
    path: str,
    *,
    headers: dict[str, str],
    json: dict[str, Any] | None = None,
    expected: int = 201,
) -> Any:
    """Call ``client`` and assert the request succeeded, returning the body."""
    response = client.request(method, path, json=json, headers=headers)
    assert response.status_code == expected, response.text
    return response.json()


def build_structure(
    client: TestClient,
    admin_headers: dict[str, str],
    *,
    name: str,
    identifier: str = "A-101",
    unit_type: str = "apartment",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Create a community, a building, and one unit through the public API.

    Returns the three response bodies, so the caller can read their ids.
    """
    community = created(
        client,
        "POST",
        "/communities",
        headers=admin_headers,
        json={"name": name},
    )
    building = created(
        client,
        "POST",
        "/buildings",
        headers=admin_headers,
        json={"community_id": community["id"], "name": f"{name} Block A"},
    )
    unit = created(
        client,
        "POST",
        "/units",
        headers=admin_headers,
        json={
            "building_id": building["id"],
            "identifier": identifier,
            "unit_type": unit_type,
        },
    )
    return community, building, unit


def create_account(
    client: TestClient,
    admin_headers: dict[str, str],
    *,
    email: str,
    role: UserRole,
) -> Account:
    """Create an account through ``POST /users`` and return a login handle."""
    body = created(
        client,
        "POST",
        "/users",
        headers=admin_headers,
        json={"email": email, "password": PASSWORD, "role": role.value},
    )
    return Account(id=body["id"], email=body["email"], role=UserRole(body["role"]))


def assign_manager(
    client: TestClient,
    admin_headers: dict[str, str],
    manager: Account,
    community_id: int,
) -> dict[str, Any]:
    """Give a manager write scope over one community (administrator action)."""
    return created(
        client,
        "POST",
        "/manager-assignments",
        headers=admin_headers,
        json={"manager_id": manager.id, "community_id": community_id},
    )


def assign_resident(
    client: TestClient,
    manager_headers: dict[str, str],
    resident: Account,
    unit_id: int,
    *,
    ownership_type: str = "owner",
) -> dict[str, Any]:
    """Assign a resident to a unit (manager action for an in-scope unit)."""
    return created(
        client,
        "POST",
        "/assignments",
        headers=manager_headers,
        json={
            "user_id": resident.id,
            "unit_id": unit_id,
            "ownership_type": ownership_type,
        },
    )


def provision_workflow(
    client: TestClient, bootstrap_admin: Account
) -> Workflow:
    """Provision the accounts, property tree, and scope every workflow needs.

    Everything below the bootstrap administrator is created through the public
    API: an administrator (seeded directly) creates the manager and the
    resident with ``POST /users``, grants the manager scope over one community,
    builds a community with an apartment and a garage, and assigns both units
    to the resident.
    """
    admin_headers = bootstrap_admin.sign_in(client)
    manager = create_account(
        client,
        admin_headers,
        email="manager@integration.test",
        role=UserRole.MANAGER,
    )
    resident = create_account(
        client,
        admin_headers,
        email="resident@integration.test",
        role=UserRole.RESIDENT,
    )
    manager_headers = manager.sign_in(client)
    resident_headers = resident.sign_in(client)

    community, building, apartment = build_structure(
        client, admin_headers, name="Integration Riverside"
    )
    # Grant the manager scope first, then let the manager create the second
    # unit: that proves manager write access is scoped, not global.
    assign_manager(client, admin_headers, manager, community["id"])
    garage = created(
        client,
        "POST",
        "/units",
        headers=manager_headers,
        json={
            "building_id": building["id"],
            "identifier": "G-01",
            "unit_type": "garage",
        },
    )
    for unit in (apartment, garage):
        assign_resident(client, manager_headers, resident, unit["id"])

    return Workflow(
        admin=bootstrap_admin,
        manager=manager,
        resident=resident,
        community=community,
        building=building,
        apartment=apartment,
        garage=garage,
        admin_headers=admin_headers,
        manager_headers=manager_headers,
        resident_headers=resident_headers,
    )

