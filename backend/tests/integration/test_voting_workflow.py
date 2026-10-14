"""Integration workflow 2: initiative creation and per-unit voting.

From the architecture document: *manager creates an initiative → resident casts
a property-weighted vote → vote aggregation*. "Property-weighted" means one
ballot per eligible unit a resident holds, so a resident owning an apartment and
a garage inside the scope casts two independent ballots.

This test drives initiative creation, the eligible-units endpoint, multi-unit
voting, scope filtering (community and tag), double-vote prevention, and the
aggregation endpoint through the HTTP API against a real database.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.models import UserRole, Vote
from tests.integration.helpers import (
    assert_denied,
    created,
    create_account,
    provision_workflow,
)

YESTERDAY = date.today() - timedelta(days=1)
TOMORROW = date.today() + timedelta(days=1)


def _create_initiative_response(client, headers, *, scope, title="Repaint the facade"):
    """Create an initiative and return the raw response (for denials)."""
    return client.post(
        "/initiatives",
        json={
            "title": title,
            "description": "Should we repaint the facade this year?",
            "opens_at": YESTERDAY.isoformat(),
            "closes_at": TOMORROW.isoformat(),
            "options": [{"label": "Yes"}, {"label": "No"}],
            "scope": scope,
        },
        headers=headers,
    )


def _create_initiative(client, headers, *, scope, title="Repaint the facade"):
    """A manager creates an initiative with two options and a scope."""
    response = _create_initiative_response(client, headers, scope=scope, title=title)
    assert response.status_code == 201, response.text
    return response.json()


def _vote(client, headers, initiative_id: int, unit_id: int, option_id: int):
    """A resident casts one ballot for one eligible unit."""
    return client.post(
        f"/initiatives/{initiative_id}/votes",
        json={"unit_id": unit_id, "option_id": option_id},
        headers=headers,
    )


def test_open_initiative_weighted_vote_aggregates(
    client, db_session, bootstrap_admin
):
    """A resident owning two eligible units casts two ballots; counts add up."""
    flow = provision_workflow(client, bootstrap_admin)

    # Empty scope means every unit is eligible: both of the resident's units.
    initiative = _create_initiative(
        client, flow.manager_headers, scope={}, title="Community-wide vote"
    )
    yes, no = (option["id"] for option in initiative["options"])
    initiative_id = initiative["id"]

    # The eligible-units endpoint lists both units, none voted yet.
    eligible = client.get(
        f"/initiatives/{initiative_id}/eligible-units",
        headers=flow.resident_headers,
    ).json()
    assert {row["unit_id"] for row in eligible} == set(flow.resident_unit_ids)
    assert all(row["vote_id"] is None for row in eligible)

    # The resident casts one ballot per owned eligible unit.
    first = _vote(
        client,
        flow.resident_headers,
        initiative_id,
        flow.apartment["id"],
        yes,
    )
    assert first.status_code == 201, first.text
    assert first.json()["option_label"] == "Yes"

    second = _vote(
        client,
        flow.resident_headers,
        initiative_id,
        flow.garage["id"],
        no,
    )
    assert second.status_code == 201, second.text
    assert second.json()["unit_id"] == flow.garage["id"]

    # Two rows really are stored, one per unit.
    stored = db_session.scalars(
        select(Vote).where(Vote.initiative_id == initiative_id)
    ).all()
    assert len(stored) == 2
    assert {vote.unit_id for vote in stored} == set(flow.resident_unit_ids)

    # The eligible-units endpoint now reports both units as voted.
    eligible = client.get(
        f"/initiatives/{initiative_id}/eligible-units",
        headers=flow.resident_headers,
    ).json()
    assert all(row["vote_id"] is not None for row in eligible)

    # Aggregation returns the count of unit ballots per option.
    results = client.get(
        f"/initiatives/{initiative_id}/results", headers=flow.resident_headers
    ).json()
    assert results["total_votes"] == 2
    assert {row["label"]: row["votes"] for row in results["tallies"]} == {
        "Yes": 1,
        "No": 1,
    }


def test_scope_excludes_ineligible_units(client, bootstrap_admin):
    """A unit-type scope limits voting to the matching units only."""
    flow = provision_workflow(client, bootstrap_admin)

    # Scope allows only apartments, so the garage is not eligible.
    initiative = _create_initiative(
        client,
        flow.manager_headers,
        scope={"unit_types": ["apartment"]},
        title="Apartment owners only",
    )
    yes = initiative["options"][0]["id"]
    initiative_id = initiative["id"]

    eligible = client.get(
        f"/initiatives/{initiative_id}/eligible-units",
        headers=flow.resident_headers,
    ).json()
    assert [row["unit_id"] for row in eligible] == [flow.apartment["id"]]

    # Voting for the out-of-scope garage is rejected.
    rejected = _vote(
        client,
        flow.resident_headers,
        initiative_id,
        flow.garage["id"],
        yes,
    )
    assert rejected.status_code == 409, rejected.text

    # The in-scope apartment is accepted.
    assert (
        _vote(
            client,
            flow.resident_headers,
            initiative_id,
            flow.apartment["id"],
            yes,
        ).status_code
        == 201
    )

    results = client.get(
        f"/initiatives/{initiative_id}/results", headers=flow.resident_headers
    ).json()
    assert results["total_votes"] == 1


def test_tag_scope_filters_eligible_units(client, bootstrap_admin):
    """A tag scope makes only tagged units eligible."""
    flow = provision_workflow(client, bootstrap_admin)

    # Tag the garage, then scope an initiative to that tag.
    tag = created(
        client, "POST", "/tags", headers=flow.manager_headers, json={"name": "EV charging"}
    )
    patched = client.patch(
        f"/units/{flow.garage['id']}",
        json={"tag_ids": [tag["id"]]},
        headers=flow.manager_headers,
    )
    assert patched.status_code == 200, patched.text

    initiative = _create_initiative(
        client,
        flow.manager_headers,
        scope={"tag_ids": [tag["id"]]},
        title="Tagged units only",
    )
    yes = initiative["options"][0]["id"]

    eligible = client.get(
        f"/initiatives/{initiative['id']}/eligible-units",
        headers=flow.resident_headers,
    ).json()
    assert [row["unit_id"] for row in eligible] == [flow.garage["id"]]

    assert (
        _vote(
            client,
            flow.resident_headers,
            initiative["id"],
            flow.garage["id"],
            yes,
        ).status_code
        == 201
    )
    assert (
        _vote(
            client,
            flow.resident_headers,
            initiative["id"],
            flow.apartment["id"],
            yes,
        ).status_code
        == 409
    )


def test_second_ballot_for_same_unit_is_rejected(
    client, db_session, bootstrap_admin
):
    """One ballot per unit: a second request for the same unit is refused."""
    flow = provision_workflow(client, bootstrap_admin)
    initiative = _create_initiative(
        client, flow.manager_headers, scope={}, title="One vote per unit"
    )
    yes, no = (option["id"] for option in initiative["options"])

    assert (
        _vote(
            client,
            flow.resident_headers,
            initiative["id"],
            flow.apartment["id"],
            yes,
        ).status_code
        == 201
    )
    duplicate = _vote(
        client,
        flow.resident_headers,
        initiative["id"],
        flow.apartment["id"],
        no,
    )
    assert duplicate.status_code == 409, duplicate.text

    stored = db_session.scalars(
        select(Vote).where(
            Vote.initiative_id == initiative["id"],
            Vote.unit_id == flow.apartment["id"],
        )
    ).all()
    assert len(stored) == 1


def test_closed_initiative_rejects_votes(client, bootstrap_admin):
    """Ballots are refused once the close date has passed."""
    flow = provision_workflow(client, bootstrap_admin)
    closed = created(
        client,
        "POST",
        "/initiatives",
        headers=flow.manager_headers,
        json={
            "title": "Last month's vote",
            "description": "Already decided.",
            "opens_at": (date.today() - timedelta(days=10)).isoformat(),
            "closes_at": (date.today() - timedelta(days=1)).isoformat(),
            "options": [{"label": "Yes"}, {"label": "No"}],
            "scope": {},
        },
    )
    yes = closed["options"][0]["id"]

    # The initiative is reported as not open.
    read = client.get(
        f"/initiatives/{closed['id']}", headers=flow.resident_headers
    ).json()
    assert read["is_open"] is False

    refused = _vote(
        client,
        flow.resident_headers,
        closed["id"],
        flow.apartment["id"],
        yes,
    )
    assert refused.status_code == 409, refused.text

    # A resident may not create an initiative at all.
    assert_denied(
        _create_initiative_response(
            client, flow.resident_headers, scope={}, title="Not allowed"
        )
    )


def test_a_second_resident_votes_independently(client, bootstrap_admin):
    """Two residents in the same community each cast their own unit ballots."""
    flow = provision_workflow(client, bootstrap_admin)
    initiative = _create_initiative(
        client, flow.manager_headers, scope={}, title="Community vote"
    )
    yes, no = (option["id"] for option in initiative["options"])

    # A second resident, assigned another apartment in the same community.
    neighbour_headers, neighbour_unit = _add_neighbour(client, flow)

    # The original resident votes with the apartment; the neighbour with theirs.
    assert (
        _vote(
            client,
            flow.resident_headers,
            initiative["id"],
            flow.apartment["id"],
            yes,
        ).status_code
        == 201
    )
    assert (
        _vote(
            client,
            neighbour_headers,
            initiative["id"],
            neighbour_unit["id"],
            no,
        ).status_code
        == 201
    )

    results = client.get(
        f"/initiatives/{initiative['id']}/results",
        headers=flow.manager_headers,
    ).json()
    assert results["total_votes"] == 2
    assert {row["label"]: row["votes"] for row in results["tallies"]} == {
        "Yes": 1,
        "No": 1,
    }


def _add_neighbour(
    client, flow
) -> tuple[dict[str, str], dict]:
    """Create a second resident and an in-community unit assigned to them."""
    neighbour = create_account(
        client,
        flow.admin_headers,
        email="neighbour@integration.test",
        role=UserRole.RESIDENT,
    )
    neighbour_headers = neighbour.sign_in(client)
    unit = created(
        client,
        "POST",
        "/units",
        headers=flow.manager_headers,
        json={
            "building_id": flow.building["id"],
            "identifier": "A-102",
            "unit_type": "apartment",
        },
    )
    response = client.post(
        "/assignments",
        json={
            "user_id": neighbour.id,
            "unit_id": unit["id"],
            "ownership_type": "tenant",
        },
        headers=flow.manager_headers,
    )
    assert response.status_code == 201, response.text
    return neighbour_headers, unit
