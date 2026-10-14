"""Tests for incidence and comment endpoints (backlog task 11).

Covers the full lifecycle (submitted -> in progress -> resolved -> closed), an
illegal transition, the comment thread, and a resident's inability to touch
another resident's incidence.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    INCIDENCE_TRANSITIONS,
    Incidence,
    IncidenceStatus,
    ManagerAssignment,
    OwnershipType,
    UnitAssignment,
    User,
    UserRole,
)
from tests.conftest import PropertyTree

LIFECYCLE = ["in progress", "resolved", "closed"]


def _submit(
    client: TestClient,
    headers: dict[str, str],
    *,
    unit_id: int,
    title: str = "Leaking tap",
    description: str = "The kitchen tap drips all night.",
):
    return client.post(
        "/incidences",
        json={"unit_id": unit_id, "title": title, "description": description},
        headers=headers,
    )


def _set_status(
    client: TestClient, headers: dict[str, str], incidence_id: int, new_status: str
):
    return client.patch(
        f"/incidences/{incidence_id}/status",
        json={"status": new_status},
        headers=headers,
    )


def _comment(
    client: TestClient,
    headers: dict[str, str],
    incidence_id: int,
    body: str,
):
    return client.post(
        f"/incidences/{incidence_id}/comments",
        json={"body": body},
        headers=headers,
    )


# --- Resident submission ----------------------------------------------------


def test_a_resident_submits_an_incidence_for_their_own_unit(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)

    response = _submit(api_client, auth_token(resident), unit_id=tree.apartment.id)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "submitted"
    assert body["unit_identifier"] == "A-101"
    assert body["created_by_email"] == "resident@efinges.test"
    assert body["comments"] == []


def test_a_resident_cannot_submit_for_another_units(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()

    response = _submit(api_client, auth_token(resident), unit_id=tree.apartment.id)

    assert response.status_code == 404


def test_submitting_for_a_missing_unit_returns_404(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    resident = create_user("resident@efinges.test")

    response = _submit(api_client, auth_token(resident), unit_id=9999)

    assert response.status_code == 404


def test_incidences_require_a_token(api_client: TestClient) -> None:
    assert api_client.get("/incidences").status_code == 401
    assert api_client.post(
        "/incidences", json={"unit_id": 1, "title": "x", "description": "y"}
    ).status_code == 401


# --- The lifecycle ----------------------------------------------------------


def test_a_manager_walks_an_incidence_through_the_whole_lifecycle(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    incidence = _submit(
        api_client, auth_token(resident), unit_id=tree.apartment.id
    ).json()
    manager_headers = auth_token(manager)

    for stage in LIFECYCLE:
        response = _set_status(
            api_client, manager_headers, incidence["id"], stage
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == stage


def test_skipping_a_lifecycle_stage_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    incidence = _submit(
        api_client, auth_token(resident), unit_id=tree.apartment.id
    ).json()

    # submitted -> resolved skips "in progress".
    response = _set_status(
        api_client, auth_token(manager), incidence["id"], "resolved"
    )

    assert response.status_code == 409
    assert "in progress" in response.json()["detail"]


def test_moving_an_incidence_backwards_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    incidence = _submit(
        api_client, auth_token(resident), unit_id=tree.apartment.id
    ).json()
    manager_headers = auth_token(manager)
    _set_status(api_client, manager_headers, incidence["id"], "in progress")

    response = _set_status(
        api_client, manager_headers, incidence["id"], "submitted"
    )

    assert response.status_code == 409


def test_a_closed_incidence_is_terminal(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
    db_session: Session,
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    incidence = _submit(
        api_client, auth_token(resident), unit_id=tree.apartment.id
    ).json()
    manager_headers = auth_token(manager)
    for stage in LIFECYCLE:
        _set_status(api_client, manager_headers, incidence["id"], stage)

    response = _set_status(
        api_client, manager_headers, incidence["id"], "closed"
    )

    assert response.status_code == 409
    assert "closed" in response.json()["detail"]
    db_session.expire_all()
    assert (
        db_session.get(Incidence, incidence["id"]).status
        is IncidenceStatus.CLOSED
    )


def test_the_transition_table_matches_the_specification() -> None:
    """The declared lifecycle is exactly the one in the specification."""
    assert INCIDENCE_TRANSITIONS[IncidenceStatus.SUBMITTED] == {
        IncidenceStatus.IN_PROGRESS
    }
    assert INCIDENCE_TRANSITIONS[IncidenceStatus.IN_PROGRESS] == {
        IncidenceStatus.RESOLVED
    }
    assert INCIDENCE_TRANSITIONS[IncidenceStatus.RESOLVED] == {
        IncidenceStatus.CLOSED
    }
    assert INCIDENCE_TRANSITIONS[IncidenceStatus.CLOSED] == frozenset()


def test_a_resident_cannot_change_a_status(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    headers = auth_token(resident)
    incidence = _submit(api_client, headers, unit_id=tree.apartment.id).json()

    response = _set_status(api_client, headers, incidence["id"], "in progress")

    assert response.status_code == 403


def test_a_manager_cannot_change_a_status_outside_their_scope(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    incidence = _submit(
        api_client, auth_token(resident), unit_id=tree.apartment.id
    ).json()

    response = _set_status(
        api_client, auth_token(manager), incidence["id"], "in progress"
    )

    assert response.status_code == 403


# --- Comment threads --------------------------------------------------------


def test_a_resident_and_a_manager_exchange_comments(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    incidence = _submit(
        api_client, auth_token(resident), unit_id=tree.apartment.id
    ).json()

    first = _comment(
        api_client, auth_token(resident), incidence["id"], "Any update?"
    )
    second = _comment(
        api_client, auth_token(manager), incidence["id"], "A plumber is coming."
    )

    assert first.status_code == 201
    assert first.json()["author_email"] == "resident@efinges.test"
    assert second.status_code == 201
    assert second.json()["author_email"] == "manager@efinges.test"

    thread = api_client.get(
        f"/incidences/{incidence['id']}/comments", headers=auth_token(resident)
    )
    assert [row["body"] for row in thread.json()] == [
        "Any update?",
        "A plumber is coming.",
    ]


def test_the_incidence_response_carries_the_thread(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    headers = auth_token(resident)
    incidence = _submit(api_client, headers, unit_id=tree.apartment.id).json()
    _comment(api_client, headers, incidence["id"], "Extra context.")

    response = api_client.get(f"/incidences/{incidence['id']}", headers=headers)

    assert [row["body"] for row in response.json()["comments"]] == [
        "Extra context."
    ]


def test_an_empty_comment_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    headers = auth_token(resident)
    incidence = _submit(api_client, headers, unit_id=tree.apartment.id).json()

    response = _comment(api_client, headers, incidence["id"], "")

    assert response.status_code == 422


def test_a_resident_cannot_comment_on_another_residents_incidence(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    owner = create_user("owner@efinges.test")
    neighbour = create_user("neighbour@efinges.test")
    tree = create_property_tree()
    assign_unit(owner, tree.apartment, OwnershipType.OWNER)
    incidence = _submit(
        api_client, auth_token(owner), unit_id=tree.apartment.id
    ).json()

    response = _comment(
        api_client, auth_token(neighbour), incidence["id"], "Not my business"
    )

    assert response.status_code == 404


def test_a_resident_cannot_read_another_residents_incidence(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    owner = create_user("owner@efinges.test")
    neighbour = create_user("neighbour@efinges.test")
    tree = create_property_tree()
    assign_unit(owner, tree.apartment, OwnershipType.OWNER)
    incidence = _submit(
        api_client, auth_token(owner), unit_id=tree.apartment.id
    ).json()

    response = api_client.get(
        f"/incidences/{incidence['id']}", headers=auth_token(neighbour)
    )

    assert response.status_code == 404


def test_a_resident_lists_only_their_own_incidences(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    mine = create_user("mine@efinges.test")
    neighbour = create_user("neighbour@efinges.test")
    tree = create_property_tree()
    assign_unit(mine, tree.apartment, OwnershipType.OWNER)
    assign_unit(neighbour, tree.garage, OwnershipType.OWNER)
    _submit(api_client, auth_token(neighbour), unit_id=tree.garage.id)
    expected = _submit(
        api_client, auth_token(mine), unit_id=tree.apartment.id
    ).json()

    response = api_client.get("/incidences", headers=auth_token(mine))

    assert [row["id"] for row in response.json()] == [expected["id"]]


def test_a_manager_lists_only_incidences_in_their_communities(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    mine = create_property_tree("Riverside")
    other = create_property_tree("Hilltop")
    resident = create_user("resident@efinges.test")
    assign_manager(manager, mine.community)
    assign_unit(resident, mine.apartment, OwnershipType.OWNER)
    assign_unit(resident, other.apartment, OwnershipType.OWNER)
    resident_headers = auth_token(resident)
    expected = _submit(
        api_client, resident_headers, unit_id=mine.apartment.id
    ).json()
    _submit(api_client, resident_headers, unit_id=other.apartment.id)

    response = api_client.get("/incidences", headers=auth_token(manager))

    assert [row["id"] for row in response.json()] == [expected["id"]]


def test_filtering_incidences_by_status(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    resident_headers = auth_token(resident)
    submitted = _submit(
        api_client, resident_headers, unit_id=tree.apartment.id
    ).json()
    moving = _submit(
        api_client,
        resident_headers,
        unit_id=tree.apartment.id,
        title="Broken lift",
    ).json()
    _set_status(api_client, auth_token(manager), moving["id"], "in progress")

    response = api_client.get("/incidences?status=in progress", headers=resident_headers)

    assert [row["id"] for row in response.json()] == [moving["id"]]
    assert submitted["id"] != moving["id"]


def test_an_unknown_unit_returns_404_on_the_thread(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    resident = create_user("resident@efinges.test")

    response = api_client.get(
        "/incidences/9999/comments", headers=auth_token(resident)
    )

    assert response.status_code == 404


def test_a_manager_can_combine_their_scope_with_the_unit_and_status_filters(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    """Regression: the manager scope plus ``?unit_id=``/``?status=`` must not double-join."""
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    assign_unit(resident, tree.garage, OwnershipType.OWNER)
    resident_headers = auth_token(resident)
    apartment_incidence = _submit(
        api_client, resident_headers, unit_id=tree.apartment.id
    ).json()
    _submit(
        api_client,
        resident_headers,
        unit_id=tree.garage.id,
        title="Broken door",
    )
    headers = auth_token(manager)

    unfiltered = api_client.get("/incidences", headers=headers)
    by_unit = api_client.get(
        f"/incidences?unit_id={tree.apartment.id}", headers=headers
    )
    by_status = api_client.get("/incidences?status=submitted", headers=headers)

    assert unfiltered.status_code == 200
    assert len(unfiltered.json()) == 2
    assert [row["id"] for row in by_unit.json()] == [apartment_incidence["id"]]
    assert len(by_status.json()) == 2
