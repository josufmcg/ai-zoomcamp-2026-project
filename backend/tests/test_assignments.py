"""Tests for resident and unit assignments (backlog task 7).

Covers the manager-only assignment endpoints, the resident-scoped unit helper,
duplicate prevention, and the ownership flag persisted per assignment.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models import OwnershipType, UnitAssignment, User, UserRole
from app.routers.assignments import units_for_user
from tests.conftest import PropertyTree, auth_header


def _assign(
    client: TestClient,
    token: str,
    *,
    user_id: int,
    unit_id: int,
    ownership_type: OwnershipType = OwnershipType.OWNER,
):
    return client.post(
        "/assignments",
        json={
            "user_id": user_id,
            "unit_id": unit_id,
            "ownership_type": ownership_type.value,
        },
        headers=auth_header(token),
    )


# --- Manager creation -------------------------------------------------------


def test_manager_creates_an_assignment(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    login: Callable[[str], str],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()

    response = _assign(
        api_client,
        login(manager.email),
        user_id=resident.id,
        unit_id=tree.apartment.id,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == resident.id
    assert body["unit_id"] == tree.apartment.id
    assert body["ownership_type"] == "owner"
    # The embedded objects carry enough detail to render a table without a
    # second request, and never the password hash.
    assert body["user"]["email"] == "resident@efinges.test"
    assert body["unit"]["identifier"] == "A-101"
    assert "password" not in response.text


def test_administrator_can_assign_too(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    login: Callable[[str], str],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()

    response = _assign(
        api_client,
        login(admin.email),
        user_id=resident.id,
        unit_id=tree.garage.id,
        ownership_type=OwnershipType.TENANT,
    )

    assert response.status_code == 201
    assert response.json()["ownership_type"] == "tenant"


def test_a_resident_may_hold_several_units(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    login: Callable[[str], str],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    token = login(manager.email)

    for unit, ownership in (
        (tree.apartment, OwnershipType.OWNER),
        (tree.garage, OwnershipType.TENANT),
        (tree.storage, OwnershipType.OWNER),
    ):
        response = _assign(
            api_client,
            token,
            user_id=resident.id,
            unit_id=unit.id,
            ownership_type=ownership,
        )
        assert response.status_code == 201, response.text

    listing = api_client.get(
        f"/assignments?user_id={resident.id}",
        headers=auth_header(token),
    )
    assert listing.status_code == 200
    assert {row["unit"]["identifier"] for row in listing.json()} == {
        "A-101",
        "G-01",
        "S-01",
    }


# --- Duplicate prevention and validation ------------------------------------


def test_assigning_the_same_unit_twice_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    login: Callable[[str], str],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    first = create_user("first@efinges.test")
    second = create_user("second@efinges.test")
    tree = create_property_tree()
    token = login(manager.email)

    assert (
        _assign(
            api_client, token, user_id=first.id, unit_id=tree.apartment.id
        ).status_code
        == 201
    )

    duplicate = _assign(
        api_client, token, user_id=second.id, unit_id=tree.apartment.id
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Unit is already assigned"


def test_assigning_the_same_unit_to_the_same_resident_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    login: Callable[[str], str],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    token = login(manager.email)

    first = _assign(
        api_client, token, user_id=resident.id, unit_id=tree.apartment.id
    )
    second = _assign(
        api_client, token, user_id=resident.id, unit_id=tree.apartment.id
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_assignment_of_a_missing_unit_returns_404(
    api_client: TestClient,
    create_user: Callable[..., User],
    login: Callable[[str], str],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")

    response = _assign(
        api_client, login(manager.email), user_id=resident.id, unit_id=9999
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Unit not found"


def test_assignment_of_a_missing_user_returns_404(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    login: Callable[[str], str],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()

    response = _assign(
        api_client,
        login(manager.email),
        user_id=9999,
        unit_id=tree.apartment.id,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_assigning_a_non_resident_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    login: Callable[[str], str],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    other_manager = create_user("other@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()

    response = _assign(
        api_client,
        login(manager.email),
        user_id=other_manager.id,
        unit_id=tree.apartment.id,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Only residents can be assigned to units"


def test_an_invalid_ownership_type_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    login: Callable[[str], str],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()

    response = api_client.post(
        "/assignments",
        json={
            "user_id": resident.id,
            "unit_id": tree.apartment.id,
            "ownership_type": "landlord",
        },
        headers=auth_header(login(manager.email)),
    )

    assert response.status_code == 422


# --- Role boundaries --------------------------------------------------------


def test_a_resident_cannot_create_an_assignment(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    login: Callable[[str], str],
) -> None:
    resident = create_user("resident@efinges.test")
    other = create_user("other@efinges.test")
    tree = create_property_tree()

    response = _assign(
        api_client,
        login(resident.email),
        user_id=other.id,
        unit_id=tree.apartment.id,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient role"


def test_a_resident_cannot_list_all_assignments(
    api_client: TestClient,
    create_user: Callable[..., User],
    login: Callable[[str], str],
) -> None:
    resident = create_user("resident@efinges.test")

    response = api_client.get(
        "/assignments", headers=auth_header(login(resident.email))
    )

    assert response.status_code == 403


def test_assignments_require_a_token(api_client: TestClient) -> None:
    assert api_client.get("/assignments").status_code == 401
    assert (
        api_client.post(
            "/assignments",
            json={"user_id": 1, "unit_id": 1, "ownership_type": "owner"},
        ).status_code
        == 401
    )


# --- Resident-scoped listing ------------------------------------------------


def test_resident_sees_only_their_own_units(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_unit: Callable[..., UnitAssignment],
    login: Callable[[str], str],
) -> None:
    resident = create_user("resident@efinges.test")
    neighbour = create_user("neighbour@efinges.test")
    tree = create_property_tree()
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    assign_unit(resident, tree.garage, OwnershipType.TENANT)
    assign_unit(neighbour, tree.storage, OwnershipType.OWNER)

    response = api_client.get(
        "/auth/me/units", headers=auth_header(login(resident.email))
    )

    assert response.status_code == 200
    body = response.json()
    assert [(row["identifier"], row["ownership_type"]) for row in body] == [
        ("A-101", "owner"),
        ("G-01", "tenant"),
    ]
    assert body[0]["building_id"] == tree.building.id


def test_resident_without_assignments_sees_an_empty_list(
    api_client: TestClient,
    create_user: Callable[..., User],
    login: Callable[[str], str],
) -> None:
    resident = create_user("resident@efinges.test")

    response = api_client.get(
        "/auth/me/units", headers=auth_header(login(resident.email))
    )

    assert response.status_code == 200
    assert response.json() == []


def test_manager_can_filter_assignments_by_unit(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_unit: Callable[..., UnitAssignment],
    login: Callable[[str], str],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_unit(resident, tree.apartment)
    assign_unit(resident, tree.storage)

    response = api_client.get(
        f"/assignments?unit_id={tree.storage.id}",
        headers=auth_header(login(manager.email)),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["unit"]["identifier"] == "S-01"


# --- Removal ----------------------------------------------------------------


def test_manager_removes_an_assignment(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    login: Callable[[str], str],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    token = login(manager.email)

    created = _assign(
        api_client, token, user_id=resident.id, unit_id=tree.apartment.id
    )
    assignment_id = created.json()["id"]

    deleted = api_client.delete(
        f"/assignments/{assignment_id}", headers=auth_header(token)
    )

    assert deleted.status_code == 204
    assert deleted.content == b""
    assert (
        api_client.get(
            "/auth/me/units", headers=auth_header(login(resident.email))
        ).json()
        == []
    )


def test_removing_a_missing_assignment_returns_404(
    api_client: TestClient,
    create_user: Callable[..., User],
    login: Callable[[str], str],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)

    response = api_client.delete(
        "/assignments/9999", headers=auth_header(login(manager.email))
    )

    assert response.status_code == 404


def test_a_resident_cannot_remove_an_assignment(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_unit: Callable[..., UnitAssignment],
    login: Callable[[str], str],
) -> None:
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assignment = assign_unit(resident, tree.apartment)

    response = api_client.delete(
        f"/assignments/{assignment.id}",
        headers=auth_header(login(resident.email)),
    )

    assert response.status_code == 403


def test_reassigning_a_removed_unit_succeeds(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    login: Callable[[str], str],
) -> None:
    """The unique constraint frees the unit again after removal."""
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    first = create_user("first@efinges.test")
    second = create_user("second@efinges.test")
    tree = create_property_tree()
    token = login(manager.email)

    created = _assign(
        api_client, token, user_id=first.id, unit_id=tree.apartment.id
    )
    api_client.delete(
        f"/assignments/{created.json()['id']}", headers=auth_header(token)
    )

    reassigned = _assign(
        api_client,
        token,
        user_id=second.id,
        unit_id=tree.apartment.id,
        ownership_type=OwnershipType.TENANT,
    )

    assert reassigned.status_code == 201
    assert reassigned.json()["user_id"] == second.id


# --- The helper reused by later tasks ---------------------------------------


def test_units_for_user_helper_returns_units_with_ownership(
    api_app: FastAPI,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_unit: Callable[..., UnitAssignment],
) -> None:
    """`units_for_user` is the resident scope the billing/vote tasks reuse."""
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    assign_unit(resident, tree.garage, OwnershipType.TENANT)

    with api_app.state.db.session() as session:
        units = units_for_user(session, resident.id)

    assert [unit.identifier for unit in units] == ["A-101", "G-01"]
    assert [unit.ownership_type for unit in units] == [
        OwnershipType.OWNER,
        OwnershipType.TENANT,
    ]
