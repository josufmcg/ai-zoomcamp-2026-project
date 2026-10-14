"""Integration workflow 1: incidence lifecycle and comment thread.

From the architecture document: *resident submits an incidence → manager updates
status → both exchange comments*. This test drives that workflow end to end
through the HTTP API against a real database, and pins the two boundaries the
workflow depends on: another resident cannot see or touch the incidence, and
only the manager responsible for the unit can advance it.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models import Incidence, IncidenceStatus, UserRole
from tests.integration.helpers import (
    assert_denied,
    assert_hidden,
    create_account,
    created,
    provision_workflow,
)


def _report(client, headers, unit_id: int, *, title: str = "Leaking kitchen tap"):
    """A resident reports an incidence against one of their units."""
    return created(
        client,
        "POST",
        "/incidences",
        headers=headers,
        json={
            "unit_id": unit_id,
            "title": title,
            "description": "The tap under the sink has been dripping for days.",
        },
    )


def test_resident_reports_manager_resolves_and_thread_is_shared(
    client, db_session, bootstrap_admin
):
    """The whole lifecycle plus a shared two-way comment thread."""
    flow = provision_workflow(client, bootstrap_admin)

    # --- the resident reports an incidence on their apartment -------------
    incidence = _report(client, flow.resident_headers, flow.apartment["id"])
    assert incidence["status"] == "submitted"
    assert incidence["unit_identifier"] == flow.apartment["identifier"]
    assert incidence["created_by_id"] == flow.resident.id
    assert incidence["comments"] == []
    incidence_id = incidence["id"]

    # The stored row really is 'submitted', not just the response.
    stored = db_session.execute(
        select(Incidence.status).where(Incidence.id == incidence_id)
    ).scalar_one()
    assert stored is IncidenceStatus.SUBMITTED

    # --- the resident opens the conversation ------------------------------
    resident_comment = created(
        client,
        "POST",
        f"/incidences/{incidence_id}/comments",
        headers=flow.resident_headers,
        json={"body": "Is anyone able to take a look this week?"},
    )
    assert resident_comment["author_id"] == flow.resident.id
    assert resident_comment["author_email"] == flow.resident.email

    # --- the manager advances the status one step at a time ---------------
    for stage in ("in progress", "resolved", "closed"):
        response = client.patch(
            f"/incidences/{incidence_id}/status",
            json={"status": stage},
            headers=flow.manager_headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == stage

    stored = db_session.execute(
        select(Incidence.status).where(Incidence.id == incidence_id)
    ).scalar_one()
    assert stored is IncidenceStatus.CLOSED

    # --- the manager answers in the same thread ---------------------------
    manager_comment = created(
        client,
        "POST",
        f"/incidences/{incidence_id}/comments",
        headers=flow.manager_headers,
        json={"body": "A plumber visited today; the washer was replaced."},
    )
    assert manager_comment["author_id"] == flow.manager.id

    # --- both sides read the same ordered thread --------------------------
    thread = client.get(
        f"/incidences/{incidence_id}/comments", headers=flow.resident_headers
    ).json()
    assert [row["body"] for row in thread] == [
        "Is anyone able to take a look this week?",
        "A plumber visited today; the washer was replaced.",
    ]
    assert {row["author_email"] for row in thread} == {
        flow.resident.email,
        flow.manager.email,
    }

    # The incidence list carries the thread so the resident screen is one call.
    listed = client.get("/incidences", headers=flow.resident_headers).json()
    assert [row["id"] for row in listed] == [incidence_id]
    assert len(listed[0]["comments"]) == 2


def test_incidence_is_hidden_from_another_resident(client, bootstrap_admin):
    """A second resident cannot see, comment on, or report against the unit."""
    flow = provision_workflow(client, bootstrap_admin)
    other = create_account(
        client,
        flow.admin_headers,
        email="other-resident@integration.test",
        role=UserRole.RESIDENT,
    )
    other_headers = other.sign_in(client)

    incidence = _report(client, flow.resident_headers, flow.apartment["id"])
    incidence_id = incidence["id"]

    # Reading, listing comments, and commenting are all hidden behind 404 so
    # the incidence id cannot be probed for existence.
    assert_hidden(client.get(f"/incidences/{incidence_id}", headers=other_headers))
    assert_hidden(client.get(f"/incidences/{incidence_id}/comments", headers=other_headers))
    assert_hidden(
        client.post(
            f"/incidences/{incidence_id}/comments",
            json={"body": "Not mine."},
            headers=other_headers,
        )
    )

    # The other resident has no units, so they cannot report on the apartment.
    assert_hidden(
        client.post(
            "/incidences",
            json={
                "unit_id": flow.apartment["id"],
                "title": "Nope",
                "description": "Nope.",
            },
            headers=other_headers,
        )
    )
    # And the list is scoped to their own (empty) set.
    assert client.get("/incidences", headers=other_headers).json() == []


def test_only_the_managing_manager_can_advance_the_lifecycle(client, bootstrap_admin):
    """Status changes are a manager action, scoped to the unit's community."""
    flow = provision_workflow(client, bootstrap_admin)
    incidence = _report(client, flow.resident_headers, flow.apartment["id"])
    incidence_id = incidence["id"]

    # A resident may not advance the status.
    assert_denied(
        client.patch(
            f"/incidences/{incidence_id}/status",
            json={"status": "in progress"},
            headers=flow.resident_headers,
        )
    )
    # Nor may an anonymous caller.
    assert_denied(
        client.patch(
            f"/incidences/{incidence_id}/status",
            json={"status": "in progress"},
        )
    )

    # A manager with no scope over the community also may not (403: the role is
    # right, the assignment is not).
    outsider = create_account(
        client,
        flow.admin_headers,
        email="outsider-manager@integration.test",
        role=UserRole.MANAGER,
    )
    outsider_headers = outsider.sign_in(client)
    assert_denied(
        client.patch(
            f"/incidences/{incidence_id}/status",
            json={"status": "in progress"},
            headers=outsider_headers,
        )
    )

    # Skipping or reversing a stage is rejected with the allowed next stage.
    skipped = client.patch(
        f"/incidences/{incidence_id}/status",
        json={"status": "resolved"},
        headers=flow.manager_headers,
    )
    assert skipped.status_code == 409, skipped.text
    assert "in progress" in skipped.json()["detail"]

    # The managing manager (and an administrator) can advance it.
    assert (
        client.patch(
            f"/incidences/{incidence_id}/status",
            json={"status": "in progress"},
            headers=flow.manager_headers,
        ).status_code
        == 200
    )
    backwards = client.patch(
        f"/incidences/{incidence_id}/status",
        json={"status": "submitted"},
        headers=flow.admin_headers,
    )
    assert backwards.status_code == 409, backwards.text
