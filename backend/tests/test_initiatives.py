"""Tests for initiatives and per-unit voting (backlog task 12).

Covers creation with an eligible scope, multi-unit voting, scope exclusion,
double-vote prevention on the same unit, closed initiatives, and aggregation.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Initiative,
    InitiativeOption,
    ManagerAssignment,
    OwnershipType,
    Tag,
    UnitAssignment,
    User,
    UserRole,
)
from tests.conftest import PropertyTree

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)


def _create_initiative(
    client: TestClient,
    headers: dict[str, str],
    *,
    title: str = "Repaint the facade",
    options: list[str] | None = None,
    opens_at: date = YESTERDAY,
    closes_at: date = TOMORROW,
    scope: dict[str, object] | None = None,
):
    return client.post(
        "/initiatives",
        json={
            "title": title,
            "description": "Should we repaint the facade this year?",
            "opens_at": opens_at.isoformat(),
            "closes_at": closes_at.isoformat(),
            "options": [{"label": label} for label in (options or ["Yes", "No"])],
            "scope": scope or {},
        },
        headers=headers,
    )


def _vote(
    client: TestClient,
    headers: dict[str, str],
    initiative_id: int,
    *,
    unit_id: int,
    option_id: int,
):
    return client.post(
        f"/initiatives/{initiative_id}/votes",
        json={"unit_id": unit_id, "option_id": option_id},
        headers=headers,
    )


# --- Creation ---------------------------------------------------------------


def test_manager_creates_an_initiative_with_scope_and_options(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)

    response = _create_initiative(
        api_client,
        auth_token(manager),
        scope={"community_ids": [tree.community.id], "unit_types": ["garage"]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["is_open"] is True
    assert [option["label"] for option in body["options"]] == ["Yes", "No"]
    assert [option["votes"] for option in body["options"]] == [0, 0]
    # The response always carries all four filters so the frontend has a
    # stable shape; only the keys the manager set are stored.
    assert body["scope"] == {
        "community_ids": [tree.community.id],
        "building_ids": [],
        "unit_types": ["garage"],
        "tag_ids": [],
    }


def test_an_initiative_needs_at_least_two_options(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)

    response = _create_initiative(api_client, auth_token(manager), options=["Only one"])

    assert response.status_code == 422


def test_duplicate_option_labels_are_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)

    response = _create_initiative(api_client, auth_token(manager), options=["Yes", "yes"])

    assert response.status_code == 422


def test_a_close_date_before_the_open_date_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)

    response = _create_initiative(
        api_client, auth_token(manager), opens_at=TODAY, closes_at=YESTERDAY
    )

    assert response.status_code == 422


def test_a_resident_cannot_create_an_initiative(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    resident = create_user("resident@efinges.test")

    response = _create_initiative(api_client, auth_token(resident))

    assert response.status_code == 403


def test_initiative_endpoints_require_a_token(api_client: TestClient) -> None:
    assert api_client.get("/initiatives").status_code == 401
    assert api_client.get("/initiatives/1/results").status_code == 401


# --- Multi-unit voting ------------------------------------------------------


def test_a_resident_casts_one_ballot_per_eligible_unit(
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
    # The resident holds all three units, and the scope is the whole community.
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    assign_unit(resident, tree.garage, OwnershipType.OWNER)
    assign_unit(resident, tree.storage, OwnershipType.TENANT)
    initiative = _create_initiative(
        api_client,
        auth_token(manager),
        scope={"community_ids": [tree.community.id]},
    ).json()
    yes, no = (option["id"] for option in initiative["options"])
    resident_headers = auth_token(resident)

    first = _vote(
        api_client,
        resident_headers,
        initiative["id"],
        unit_id=tree.apartment.id,
        option_id=yes,
    )
    second = _vote(
        api_client,
        resident_headers,
        initiative["id"],
        unit_id=tree.garage.id,
        option_id=no,
    )
    third = _vote(
        api_client,
        resident_headers,
        initiative["id"],
        unit_id=tree.storage.id,
        option_id=yes,
    )

    assert [first.status_code, second.status_code, third.status_code] == [201, 201, 201]
    results = api_client.get(
        f"/initiatives/{initiative['id']}/results", headers=resident_headers
    ).json()
    assert results["total_votes"] == 3
    assert {row["label"]: row["votes"] for row in results["tallies"]} == {
        "Yes": 2,
        "No": 1,
    }


def test_a_second_ballot_for_the_same_unit_is_rejected(
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
    initiative = _create_initiative(api_client, auth_token(manager)).json()
    yes, no = (option["id"] for option in initiative["options"])
    resident_headers = auth_token(resident)

    first = _vote(
        api_client,
        resident_headers,
        initiative["id"],
        unit_id=tree.apartment.id,
        option_id=yes,
    )
    second = _vote(
        api_client,
        resident_headers,
        initiative["id"],
        unit_id=tree.apartment.id,
        option_id=no,
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Unit has already voted in this initiative"


def test_the_unique_constraint_prevents_a_duplicate_ballot(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
    db_session: Session,
) -> None:
    """The database rejects a duplicate even if the endpoint checks are bypassed."""
    from sqlalchemy.exc import IntegrityError

    from app.models import Vote

    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    initiative = _create_initiative(api_client, auth_token(manager)).json()
    yes, no = (option["id"] for option in initiative["options"])
    _vote(
        api_client,
        auth_token(resident),
        initiative["id"],
        unit_id=tree.apartment.id,
        option_id=yes,
    )

    db_session.add(
        Vote(
            initiative_id=initiative["id"],
            option_id=no,
            unit_id=tree.apartment.id,
            voter_id=resident.id,
        )
    )
    try:
        db_session.commit()
    except IntegrityError:
        db_session.rollback()
    else:  # pragma: no cover - the constraint must fire
        raise AssertionError("a duplicate ballot was accepted by the database")


def test_a_unit_outside_the_scope_cannot_vote(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    """The scope selects garages only, so the apartment's owner cannot vote it."""
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    assign_unit(resident, tree.garage, OwnershipType.OWNER)
    initiative = _create_initiative(
        api_client,
        auth_token(manager),
        scope={"unit_types": ["garage"]},
    ).json()
    option_id = initiative["options"][0]["id"]
    resident_headers = auth_token(resident)

    excluded = _vote(
        api_client,
        resident_headers,
        initiative["id"],
        unit_id=tree.apartment.id,
        option_id=option_id,
    )
    included = _vote(
        api_client,
        resident_headers,
        initiative["id"],
        unit_id=tree.garage.id,
        option_id=option_id,
    )

    assert excluded.status_code == 409
    assert included.status_code == 201


def test_a_unit_the_resident_does_not_hold_cannot_vote(
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
    # The resident holds only the apartment; the garage belongs to nobody.
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    initiative = _create_initiative(api_client, auth_token(manager)).json()

    response = _vote(
        api_client,
        auth_token(resident),
        initiative["id"],
        unit_id=tree.garage.id,
        option_id=initiative["options"][0]["id"],
    )

    assert response.status_code == 409


def test_tag_scoping_selects_only_tagged_units(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    create_tag: Callable[..., Tag],
    assign_unit: Callable[..., UnitAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    assign_unit(resident, tree.apartment, OwnershipType.OWNER)
    assign_unit(resident, tree.garage, OwnershipType.OWNER)
    tag = create_tag("Voting units")
    manager_headers = auth_token(manager)
    api_client.patch(
        f"/units/{tree.garage.id}",
        json={"tag_ids": [tag.id]},
        headers=manager_headers,
    )
    initiative = _create_initiative(api_client, manager_headers, scope={"tag_ids": [tag.id]}).json()
    option_id = initiative["options"][0]["id"]
    resident_headers = auth_token(resident)

    excluded = _vote(
        api_client,
        resident_headers,
        initiative["id"],
        unit_id=tree.apartment.id,
        option_id=option_id,
    )
    included = _vote(
        api_client,
        resident_headers,
        initiative["id"],
        unit_id=tree.garage.id,
        option_id=option_id,
    )

    assert excluded.status_code == 409
    assert included.status_code == 201


def test_an_empty_scope_makes_every_unit_eligible(
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
    assign_unit(resident, tree.storage, OwnershipType.TENANT)
    initiative = _create_initiative(api_client, auth_token(manager), scope={}).json()

    response = _vote(
        api_client,
        auth_token(resident),
        initiative["id"],
        unit_id=tree.storage.id,
        option_id=initiative["options"][0]["id"],
    )

    assert response.status_code == 201


# --- Closed initiatives -----------------------------------------------------


def test_voting_on_a_closed_initiative_is_rejected(
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
    initiative = _create_initiative(
        api_client,
        auth_token(manager),
        opens_at=TODAY - timedelta(days=10),
        closes_at=YESTERDAY,
    ).json()

    response = _vote(
        api_client,
        auth_token(resident),
        initiative["id"],
        unit_id=tree.apartment.id,
        option_id=initiative["options"][0]["id"],
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Initiative is not open for voting"


def test_voting_before_an_initiative_opens_is_rejected(
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
    initiative = _create_initiative(
        api_client,
        auth_token(manager),
        opens_at=TOMORROW,
        closes_at=TOMORROW + timedelta(days=7),
    ).json()

    response = _vote(
        api_client,
        auth_token(resident),
        initiative["id"],
        unit_id=tree.apartment.id,
        option_id=initiative["options"][0]["id"],
    )

    assert response.status_code == 409


def test_closed_initiatives_are_reported_as_not_open(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    headers = auth_token(manager)
    initiative = _create_initiative(
        api_client, headers, opens_at=TODAY - timedelta(days=10), closes_at=YESTERDAY
    ).json()

    response = api_client.get(f"/initiatives/{initiative['id']}", headers=headers)

    assert response.json()["is_open"] is False


def test_filtering_open_and_closed_initiatives(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    headers = auth_token(manager)
    open_one = _create_initiative(api_client, headers, title="Open").json()
    closed = _create_initiative(
        api_client,
        headers,
        title="Closed",
        opens_at=TODAY - timedelta(days=10),
        closes_at=YESTERDAY,
    ).json()

    open_listing = api_client.get("/initiatives?is_open=true", headers=headers)
    closed_listing = api_client.get("/initiatives?is_open=false", headers=headers)

    assert [row["id"] for row in open_listing.json()] == [open_one["id"]]
    assert [row["id"] for row in closed_listing.json()] == [closed["id"]]


# --- Ballot bookkeeping -----------------------------------------------------


def test_eligible_units_endpoint_lists_owned_units_and_existing_votes(
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
    assign_unit(resident, tree.garage, OwnershipType.OWNER)
    initiative = _create_initiative(api_client, auth_token(manager)).json()
    yes = initiative["options"][0]["id"]
    resident_headers = auth_token(resident)
    _vote(
        api_client,
        resident_headers,
        initiative["id"],
        unit_id=tree.apartment.id,
        option_id=yes,
    )

    response = api_client.get(
        f"/initiatives/{initiative['id']}/eligible-units", headers=resident_headers
    )

    assert response.status_code == 200
    by_unit = {row["unit_id"]: row for row in response.json()}
    assert set(by_unit) == {tree.apartment.id, tree.garage.id}
    assert by_unit[tree.apartment.id]["option_id"] == yes
    assert by_unit[tree.apartment.id]["vote_id"] is not None
    assert by_unit[tree.garage.id]["option_id"] is None


def test_an_option_from_another_initiative_is_rejected(
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
    manager_headers = auth_token(manager)
    first = _create_initiative(api_client, manager_headers, title="First").json()
    second = _create_initiative(api_client, manager_headers, title="Second").json()

    response = _vote(
        api_client,
        auth_token(resident),
        first["id"],
        unit_id=tree.apartment.id,
        option_id=second["options"][0]["id"],
    )

    assert response.status_code == 404


def test_a_manager_cannot_cast_a_ballot(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    manager_headers = auth_token(manager)
    initiative = _create_initiative(api_client, manager_headers).json()

    response = _vote(
        api_client,
        manager_headers,
        initiative["id"],
        unit_id=tree.apartment.id,
        option_id=initiative["options"][0]["id"],
    )

    assert response.status_code == 403


def test_results_for_an_initiative_with_no_ballots(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    headers = auth_token(manager)
    initiative = _create_initiative(api_client, headers).json()

    response = api_client.get(f"/initiatives/{initiative['id']}/results", headers=headers)

    assert response.status_code == 200
    assert response.json()["total_votes"] == 0
    assert [row["votes"] for row in response.json()["tallies"]] == [0, 0]


def test_a_missing_initiative_returns_404(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    resident = create_user("resident@efinges.test")

    response = api_client.get("/initiatives/9999", headers=auth_token(resident))

    assert response.status_code == 404


def test_the_scope_filter_helper_is_the_single_source_of_eligibility(
    api_client: TestClient,
    db_session: Session,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    """``eligible_unit_ids`` returns exactly the units the filters select."""
    from app.models import Unit
    from app.routers.governance import eligible_unit_ids

    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    initiative = _create_initiative(
        api_client,
        auth_token(manager),
        scope={"unit_types": ["storage"]},
    ).json()

    stored = db_session.get(Initiative, initiative["id"])
    assert stored is not None
    assert eligible_unit_ids(db_session, stored.scope) == {tree.storage.id}
    # And the scope really is stored as JSON strings, not enum objects.
    assert stored.scope == {"unit_types": ["storage"]}
    assert db_session.get(Unit, tree.storage.id) is not None


def test_option_positions_follow_the_request_order(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
    db_session: Session,
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    initiative = _create_initiative(
        api_client, auth_token(manager), options=["First", "Second", "Third"]
    ).json()

    stored = db_session.get(Initiative, initiative["id"])
    assert stored is not None
    ordered = sorted(stored.options, key=lambda option: option.position)
    assert [option.label for option in ordered] == ["First", "Second", "Third"]
    assert [option.position for option in ordered] == [0, 1, 2]
    assert all(isinstance(option, InitiativeOption) for option in ordered)
