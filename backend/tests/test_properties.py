"""Tests for property, tag, and manager-assignment endpoints (backlog task 8).

Covers the CRUD flows for communities, buildings, units, and tags, plus all
three role boundaries: administrators see everything, managers are limited to
the communities they are assigned to, and residents see only their own units.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    ManagerAssignment,
    OwnershipType,
    Tag,
    Unit,
    UnitAssignment,
    User,
    UserRole,
)
from tests.conftest import PropertyTree

# --- Administrators manage the tree ----------------------------------------


def test_administrator_creates_a_community(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)

    response = api_client.post(
        "/communities", json={"name": "Riverside"}, headers=auth_token(admin)
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Riverside"


def test_a_manager_cannot_create_a_community(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)

    response = api_client.post(
        "/communities", json={"name": "Riverside"}, headers=auth_token(manager)
    )

    assert response.status_code == 403


def test_administrator_renames_and_deletes_a_community(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    headers = auth_token(admin)
    created = api_client.post("/communities", json={"name": "Riverside"}, headers=headers).json()

    renamed = api_client.patch(
        f"/communities/{created['id']}", json={"name": "Riverside North"}, headers=headers
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Riverside North"

    deleted = api_client.delete(f"/communities/{created['id']}", headers=headers)
    assert deleted.status_code == 204
    missing = api_client.get(f"/communities/{created['id']}", headers=headers)
    assert missing.status_code == 404


def test_deleting_a_community_cascades_to_its_units(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    auth_token: Callable[[User], dict[str, str]],
    db_session: Session,
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    tree = create_property_tree()

    response = api_client.delete(f"/communities/{tree.community.id}", headers=auth_token(admin))

    assert response.status_code == 204
    assert db_session.get(Unit, tree.apartment.id) is None


# --- Managers maintain buildings and units in their scope -------------------


def test_manager_creates_a_building_in_an_assigned_community(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)

    response = api_client.post(
        "/buildings",
        json={"community_id": tree.community.id, "name": "Block B"},
        headers=auth_token(manager),
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Block B"


def test_manager_cannot_touch_a_building_outside_their_scope(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()

    # The manager is assigned to no community at all.
    created = api_client.post(
        "/buildings",
        json={"community_id": tree.community.id, "name": "Block B"},
        headers=auth_token(manager),
    )
    assert created.status_code == 403

    renamed = api_client.patch(
        f"/buildings/{tree.building.id}",
        json={"name": "Block Z"},
        headers=auth_token(manager),
    )
    assert renamed.status_code == 403


def test_manager_creates_a_unit_and_attaches_tags(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    create_tag: Callable[..., Tag],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    downtown = create_tag("Downtown")

    response = api_client.post(
        "/units",
        json={
            "building_id": tree.building.id,
            "identifier": "A-102",
            "unit_type": "apartment",
            "tag_ids": [downtown.id],
        },
        headers=auth_token(manager),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["identifier"] == "A-102"
    assert [tag["name"] for tag in body["tags"]] == ["Downtown"]


def test_a_duplicate_building_name_in_the_same_community_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)

    response = api_client.post(
        "/buildings",
        json={"community_id": tree.community.id, "name": tree.building.name},
        headers=auth_token(manager),
    )

    assert response.status_code == 409


def test_creating_a_unit_in_a_missing_building_returns_404(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)

    response = api_client.post(
        "/units",
        json={"building_id": 9999, "identifier": "A-1", "unit_type": "garage"},
        headers=auth_token(manager),
    )

    assert response.status_code == 404


def test_an_invalid_unit_type_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)

    response = api_client.post(
        "/units",
        json={
            "building_id": tree.building.id,
            "identifier": "X-1",
            "unit_type": "penthouse",
        },
        headers=auth_token(manager),
    )

    assert response.status_code == 422


def test_manager_updates_a_unit(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)

    response = api_client.patch(
        f"/units/{tree.garage.id}",
        json={"identifier": "G-02", "unit_type": "storage"},
        headers=auth_token(manager),
    )

    assert response.status_code == 200
    assert response.json()["identifier"] == "G-02"
    assert response.json()["unit_type"] == "storage"


def test_manager_deletes_a_unit(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
    db_session: Session,
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)

    response = api_client.delete(f"/units/{tree.storage.id}", headers=auth_token(manager))

    assert response.status_code == 204
    assert db_session.get(Unit, tree.storage.id) is None


# --- Reading the tree --------------------------------------------------------


def test_manager_lists_only_buildings_in_their_communities(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    mine = create_property_tree("Riverside")
    other = create_property_tree("Hilltop")
    assign_manager(manager, mine.community)

    response = api_client.get("/buildings", headers=auth_token(manager))

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [mine.building.id]
    assert other.building.id not in [row["id"] for row in response.json()]


def test_administrator_lists_every_community(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    create_property_tree("Riverside")
    create_property_tree("Hilltop")

    response = api_client.get("/communities", headers=auth_token(admin))

    assert response.status_code == 200
    assert {row["name"] for row in response.json()} == {"Riverside", "Hilltop"}


def test_manager_reading_an_out_of_scope_building_gets_404(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()

    response = api_client.get(f"/buildings/{tree.building.id}", headers=auth_token(manager))

    assert response.status_code == 404


def test_resident_lists_only_their_own_units(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)

    response = api_client.get("/units", headers=auth_token(resident))

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [tree.apartment.id]


def test_resident_reading_another_residents_unit_gets_404(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    resident = create_user("resident@efinges.test")
    neighbour = create_user("neighbour@efinges.test")
    tree = create_property_tree()
    assign_unit(neighbour, tree.apartment, OwnershipType.OWNER)

    response = api_client.get(f"/units/{tree.apartment.id}", headers=auth_token(resident))

    assert response.status_code == 404


def test_manager_filters_units_by_tag(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    create_tag: Callable[..., Tag],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    headers = auth_token(manager)

    garage_tag = api_client.post("/tags", json={"name": "Garages"}, headers=headers).json()
    api_client.patch(
        f"/units/{tree.garage.id}",
        json={"tag_ids": [garage_tag["id"]]},
        headers=headers,
    )

    response = api_client.get(f"/units?tag_id={garage_tag['id']}", headers=headers)

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [tree.garage.id]


def test_every_unit_filter_works_alongside_a_managers_scope(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    create_tag: Callable[..., Tag],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    """Regression: a filter must not join ``buildings`` a second time.

    Scoping a manager to their communities already reaches ``buildings``, so
    ``?community_id=`` used to produce a duplicate join and a 500. Every filter
    is now a correlated ``EXISTS``, and this test exercises each one.
    """
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    tag = create_tag("Downtown")
    headers = auth_token(manager)

    every_unit = api_client.get("/units", headers=headers)
    by_community = api_client.get(f"/units?community_id={tree.community.id}", headers=headers)
    by_building = api_client.get(f"/units?building_id={tree.building.id}", headers=headers)
    by_tag = api_client.get(f"/units?tag_id={tag.id}", headers=headers)

    assert every_unit.status_code == 200
    assert by_community.status_code == 200
    assert by_building.status_code == 200
    assert by_tag.status_code == 200
    assert len(every_unit.json()) == 3
    assert len(by_community.json()) == 3
    assert len(by_building.json()) == 3
    assert by_tag.json() == []


def test_a_resident_can_combine_ownership_with_unit_filters(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    """The resident scope combined with ``?community_id=`` must not double-join."""
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    headers = auth_token(resident)

    response = api_client.get(f"/units?community_id={tree.community.id}", headers=headers)

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [tree.apartment.id]


def test_property_endpoints_require_a_token(api_client: TestClient) -> None:
    assert api_client.get("/communities").status_code == 401
    assert api_client.get("/buildings").status_code == 401
    assert api_client.get("/units").status_code == 401


# --- Tags -------------------------------------------------------------------


def test_tags_are_unique(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    headers = auth_token(manager)

    first = api_client.post("/tags", json={"name": "Downtown"}, headers=headers)
    second = api_client.post("/tags", json={"name": "Downtown"}, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409


def test_a_resident_cannot_create_a_tag(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    resident = create_user("resident@efinges.test")

    response = api_client.post("/tags", json={"name": "Downtown"}, headers=auth_token(resident))

    assert response.status_code == 403


def test_deleting_a_tag_detaches_it_from_units(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    create_tag: Callable[..., Tag],
    auth_token: Callable[[User], dict[str, str]],
    db_session: Session,
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    tag = create_tag("Downtown")
    headers = auth_token(manager)
    api_client.patch(
        f"/units/{tree.apartment.id}",
        json={"tag_ids": [tag.id]},
        headers=headers,
    )

    deleted = api_client.delete(f"/tags/{tag.id}", headers=headers)

    assert deleted.status_code == 204
    db_session.expire_all()
    assert db_session.get(Unit, tree.apartment.id).tags == []


# --- Manager-to-community assignments ---------------------------------------


def test_administrator_assigns_a_manager_to_a_community(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()

    response = api_client.post(
        "/manager-assignments",
        json={"manager_id": manager.id, "community_id": tree.community.id},
        headers=auth_token(admin),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["manager"]["email"] == "manager@efinges.test"
    assert body["community"]["name"] == "Riverside"


def test_the_assignment_is_what_grants_write_access(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    admin_headers = auth_token(admin)
    manager_headers = auth_token(manager)

    denied = api_client.post(
        "/buildings",
        json={"community_id": tree.community.id, "name": "Block B"},
        headers=manager_headers,
    )
    assert denied.status_code == 403

    api_client.post(
        "/manager-assignments",
        json={"manager_id": manager.id, "community_id": tree.community.id},
        headers=admin_headers,
    )

    allowed = api_client.post(
        "/buildings",
        json={"community_id": tree.community.id, "name": "Block B"},
        headers=manager_headers,
    )
    assert allowed.status_code == 201


def test_assigning_the_same_pair_twice_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    headers = auth_token(admin)
    payload = {"manager_id": manager.id, "community_id": tree.community.id}

    assert api_client.post("/manager-assignments", json=payload, headers=headers).status_code == 201
    duplicate = api_client.post("/manager-assignments", json=payload, headers=headers)

    assert duplicate.status_code == 409


def test_assigning_a_non_manager_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()

    response = api_client.post(
        "/manager-assignments",
        json={"manager_id": resident.id, "community_id": tree.community.id},
        headers=auth_token(admin),
    )

    assert response.status_code == 422


def test_a_manager_cannot_assign_themselves_to_a_community(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()

    response = api_client.post(
        "/manager-assignments",
        json={"manager_id": manager.id, "community_id": tree.community.id},
        headers=auth_token(manager),
    )

    assert response.status_code == 403


def test_removing_a_manager_assignment_revokes_access(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assignment = assign_manager(manager, tree.community)
    manager_headers = auth_token(manager)

    assert api_client.get("/buildings", headers=manager_headers).json() != []

    removed = api_client.delete(f"/manager-assignments/{assignment.id}", headers=auth_token(admin))

    assert removed.status_code == 204
    assert api_client.get("/buildings", headers=manager_headers).json() == []


def test_manager_assignment_listing_is_administrator_only(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)

    assert api_client.get("/manager-assignments", headers=auth_token(manager)).status_code == 403


def test_an_unknown_community_or_manager_returns_404(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    headers = auth_token(admin)

    missing_community = api_client.post(
        "/manager-assignments",
        json={"manager_id": manager.id, "community_id": 9999},
        headers=headers,
    )
    missing_manager = api_client.post(
        "/manager-assignments",
        json={"manager_id": 9999, "community_id": tree.community.id},
        headers=headers,
    )

    assert missing_community.status_code == 404
    assert missing_manager.status_code == 404


def test_communities_are_not_unique_by_name(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    """A community name may repeat; uniqueness lives on buildings instead.

    This pins the intended database shape: ``communities.name`` carries no
    unique constraint, while ``buildings`` is unique on
    ``(community_id, name)`` (covered by the duplicate test above).
    """
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    headers = auth_token(admin)

    first = api_client.post("/communities", json={"name": "Riverside"}, headers=headers)
    second = api_client.post("/communities", json={"name": "Riverside"}, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_building_and_unit_reads_include_tags(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    create_tag: Callable[..., Tag],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    tag = create_tag("Downtown")

    api_client.patch(
        f"/buildings/{tree.building.id}",
        json={"tag_ids": [tag.id]},
        headers=auth_token(manager),
    )

    response = api_client.get(f"/buildings/{tree.building.id}", headers=auth_token(manager))

    assert response.status_code == 200
    assert [row["name"] for row in response.json()["tags"]] == ["Downtown"]
