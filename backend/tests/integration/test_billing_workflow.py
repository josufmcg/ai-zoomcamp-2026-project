"""Integration workflow 3: manual billing from pending to paid.

From the architecture document: *manager creates a manual bill → resident sees
it move from pending to paid*. This test drives that workflow through the HTTP
API against a real database, including the computed ``overdue`` status, the
one-way paid transition, and the scope boundaries that keep one resident's bills
away from another.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.models import Bill, BillStatus, UserRole
from tests.integration.helpers import (
    assert_denied,
    assert_hidden,
    create_account,
    provision_workflow,
)

TODAY = date.today()


def _issue_response(
    client,
    headers,
    unit_id: int,
    *,
    due_date: date,
    issue_date: date = TODAY,
    amount: str = "120.50",
):
    """Issue a bill and return the raw response (for denial assertions)."""
    return client.post(
        "/bills",
        json={
            "unit_id": unit_id,
            "amount": amount,
            "description": "Monthly community fee",
            "issue_date": issue_date.isoformat(),
            "due_date": due_date.isoformat(),
        },
        headers=headers,
    )


def _issue(client, headers, unit_id: int, *, due_date: date, amount: str = "120.50"):
    """A manager issues a bill for one unit."""
    response = _issue_response(client, headers, unit_id, due_date=due_date, amount=amount)
    assert response.status_code == 201, response.text
    return response.json()


def test_bill_moves_from_pending_to_paid(client, db_session, bootstrap_admin):
    """A resident sees a pending bill, then the same bill as paid."""
    flow = provision_workflow(client, bootstrap_admin)

    future_due = TODAY + timedelta(days=15)
    bill = _issue(client, flow.manager_headers, flow.apartment["id"], due_date=future_due)
    bill_id = bill["id"]
    assert bill["status"] == "pending"
    # The amount round-trips exactly through NUMERIC(12, 2)/Decimal.
    assert bill["amount"] == "120.50"
    assert bill["unit_identifier"] == flow.apartment["identifier"]

    # The stored status is pending; 'overdue'/'paid' are not stored yet.
    stored = db_session.execute(
        select(Bill.status).where(Bill.id == bill_id)
    ).scalar_one()
    assert stored is BillStatus.PENDING

    # The resident sees it on their own unit.
    resident_bills = client.get("/bills", headers=flow.resident_headers).json()
    assert [row["id"] for row in resident_bills] == [bill_id]
    assert resident_bills[0]["status"] == "pending"

    # The manager marks it paid; the transition is one-way.
    paid = client.post(f"/bills/{bill_id}/pay", headers=flow.manager_headers)
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "paid"

    stored = db_session.execute(
        select(Bill.status).where(Bill.id == bill_id)
    ).scalar_one()
    assert stored is BillStatus.PAID

    # The resident now reads it as paid through both the list and the detail.
    assert client.get("/bills", headers=flow.resident_headers).json()[0][
        "status"
    ] == "paid"
    assert (
        client.get(f"/bills/{bill_id}", headers=flow.resident_headers).json()[
            "status"
        ]
        == "paid"
    )

    # Paying again is refused.
    again = client.post(f"/bills/{bill_id}/pay", headers=flow.manager_headers)
    assert again.status_code == 409, again.text


def test_overdue_is_computed_and_never_stored(client, db_session, bootstrap_admin):
    """A pending bill past its due date reports overdue while stored pending."""
    flow = provision_workflow(client, bootstrap_admin)

    past_due = TODAY - timedelta(days=3)
    bill = _issue_response(
        client,
        flow.manager_headers,
        flow.apartment["id"],
        due_date=past_due,
        issue_date=TODAY - timedelta(days=10),
    ).json()
    bill_id = bill["id"]

    # Every response shows the computed display status.
    assert bill["status"] == "overdue"
    assert (
        client.get(f"/bills/{bill_id}", headers=flow.resident_headers).json()[
            "status"
        ]
        == "overdue"
    )

    # The database still holds 'pending'; overdue was never persisted.
    stored = db_session.execute(
        select(Bill.status).where(Bill.id == bill_id)
    ).scalar_one()
    assert stored is BillStatus.PENDING

    # The status filter selects on the computed value.
    overdue = client.get(
        "/bills?status=overdue", headers=flow.resident_headers
    ).json()
    assert [row["id"] for row in overdue] == [bill_id]
    pending = client.get(
        "/bills?status=pending", headers=flow.resident_headers
    ).json()
    assert pending == []

    # Paying an overdue bill is allowed and clears the computed status.
    paid = client.post(f"/bills/{bill_id}/pay", headers=flow.manager_headers).json()
    assert paid["status"] == "paid"
    assert (
        client.get("/bills?status=overdue", headers=flow.resident_headers).json()
        == []
    )


def test_bills_are_scoped_to_the_owning_resident(client, bootstrap_admin):
    """One resident cannot see or read another resident's bills."""
    flow = provision_workflow(client, bootstrap_admin)
    other = create_account(
        client,
        flow.admin_headers,
        email="other-known@integration.test",
        role=UserRole.RESIDENT,
    )
    other_headers = other.sign_in(client)

    bill = _issue(client, flow.manager_headers, flow.apartment["id"], due_date=TODAY)
    bill_id = bill["id"]

    # The other resident (no units) sees nothing and cannot read the bill.
    assert client.get("/bills", headers=other_headers).json() == []
    assert_hidden(client.get(f"/bills/{bill_id}", headers=other_headers))

    # A resident may not issue or settle bills.
    assert_denied(
        _issue_response(
            client, flow.resident_headers, flow.apartment["id"], due_date=TODAY
        )
    )
    assert_denied(
        client.post(f"/bills/{bill_id}/pay", headers=flow.resident_headers)
    )

    # A manager without scope over the community may not issue a bill either.
    outsider = create_account(
        client,
        flow.admin_headers,
        email="outsider-billing@integration.test",
        role=UserRole.MANAGER,
    )
    outsider_headers = outsider.sign_in(client)
    assert_denied(
        _issue_response(
            client, outsider_headers, flow.apartment["id"], due_date=TODAY
        )
    )


def test_due_date_before_issue_date_is_rejected(client, bootstrap_admin):
    """An already-overdue bill cannot be created (422, not stored)."""
    flow = provision_workflow(client, bootstrap_admin)
    response = client.post(
        "/bills",
        json={
            "unit_id": flow.apartment["id"],
            "amount": "10.00",
            "description": "Bad dates",
            "issue_date": TODAY.isoformat(),
            "due_date": (TODAY - timedelta(days=1)).isoformat(),
        },
        headers=flow.manager_headers,
    )
    assert response.status_code == 422, response.text
