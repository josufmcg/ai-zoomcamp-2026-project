"""Tests for bill management (backlog task 10).

Covers manual creation by managers, the paid transition, the *computed*
overdue status (including proof that the stored status never changes), the
status filter, and the role boundaries.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Bill,
    BillStatus,
    ManagerAssignment,
    OwnershipType,
    UnitAssignment,
    User,
    UserRole,
)
from tests.conftest import PropertyTree

YESTERDAY = date.today() - timedelta(days=1)
TOMORROW = date.today() + timedelta(days=1)


def _create_bill(
    client: TestClient,
    headers: dict[str, str],
    *,
    unit_id: int,
    amount: str = "120.50",
    due_date: date = TOMORROW,
    issue_date: date | None = None,
    description: str = "Monthly rent",
):
    payload: dict[str, object] = {
        "unit_id": unit_id,
        "amount": amount,
        "description": description,
        "due_date": due_date.isoformat(),
    }
    if issue_date is not None:
        payload["issue_date"] = issue_date.isoformat()
    return client.post("/bills", json=payload, headers=headers)


# --- Creation ---------------------------------------------------------------


def test_manager_creates_a_bill(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)

    response = _create_bill(api_client, auth_token(manager), unit_id=tree.apartment.id)

    assert response.status_code == 201
    body = response.json()
    assert body["unit_id"] == tree.apartment.id
    assert body["unit_identifier"] == "A-101"
    assert body["amount"] == "120.50"
    assert body["status"] == "pending"
    assert body["issue_date"] == date.today().isoformat()


def test_the_amount_is_stored_exactly(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    """A value that is not exact in binary floating point must round-trip."""
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)

    response = _create_bill(
        api_client, auth_token(manager), unit_id=tree.apartment.id, amount="0.30"
    )

    assert response.status_code == 201
    assert response.json()["amount"] == "0.30"


def test_a_manager_cannot_bill_a_unit_outside_their_scope(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()

    response = _create_bill(api_client, auth_token(manager), unit_id=tree.apartment.id)

    assert response.status_code == 403


def test_a_resident_cannot_create_a_bill(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()

    response = _create_bill(api_client, auth_token(resident), unit_id=tree.apartment.id)

    assert response.status_code == 403


def test_a_non_positive_amount_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    headers = auth_token(manager)

    zero = _create_bill(api_client, headers, unit_id=tree.apartment.id, amount="0")
    negative = _create_bill(api_client, headers, unit_id=tree.apartment.id, amount="-5.00")

    assert zero.status_code == 422
    assert negative.status_code == 422


def test_a_due_date_before_the_issue_date_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)

    response = _create_bill(
        api_client,
        auth_token(manager),
        unit_id=tree.apartment.id,
        issue_date=date.today(),
        due_date=YESTERDAY,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "due_date must not be before issue_date"


def test_billing_a_missing_unit_returns_404(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)

    response = _create_bill(api_client, auth_token(manager), unit_id=9999)

    assert response.status_code == 404


# --- The paid transition ----------------------------------------------------


def test_manager_marks_a_bill_paid(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    headers = auth_token(manager)
    bill = _create_bill(api_client, headers, unit_id=tree.apartment.id).json()

    response = api_client.post(f"/bills/{bill['id']}/pay", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "paid"


def test_paying_twice_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    headers = auth_token(manager)
    bill = _create_bill(api_client, headers, unit_id=tree.apartment.id).json()

    api_client.post(f"/bills/{bill['id']}/pay", headers=headers)
    second = api_client.post(f"/bills/{bill['id']}/pay", headers=headers)

    assert second.status_code == 409


def test_a_resident_cannot_mark_a_bill_paid(
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
    bill = _create_bill(api_client, auth_token(manager), unit_id=tree.apartment.id).json()

    response = api_client.post(f"/bills/{bill['id']}/pay", headers=auth_token(resident))

    assert response.status_code == 403


# --- Computed overdue -------------------------------------------------------


def test_a_pending_bill_past_its_due_date_reads_as_overdue(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    headers = auth_token(manager)
    bill = _create_bill(
        api_client,
        headers,
        unit_id=tree.apartment.id,
        issue_date=date.today() - timedelta(days=10),
        due_date=YESTERDAY,
    ).json()

    response = api_client.get(f"/bills/{bill['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "overdue"


def test_overdue_is_never_stored(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
    db_session: Session,
) -> None:
    """The response says ``overdue`` while the row still says ``pending``."""
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    headers = auth_token(manager)
    bill = _create_bill(
        api_client,
        headers,
        unit_id=tree.apartment.id,
        issue_date=date.today() - timedelta(days=10),
        due_date=YESTERDAY,
    ).json()

    assert api_client.get(f"/bills/{bill['id']}", headers=headers).json()["status"] == "overdue"

    db_session.expire_all()
    stored = db_session.get(Bill, bill["id"])
    assert stored is not None
    assert stored.status is BillStatus.PENDING


def test_a_paid_bill_is_never_overdue(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    """Paying an overdue bill reports ``paid``; the due date stops mattering."""
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    headers = auth_token(manager)
    bill = _create_bill(
        api_client,
        headers,
        unit_id=tree.apartment.id,
        issue_date=date.today() - timedelta(days=10),
        due_date=YESTERDAY,
    ).json()

    paid = api_client.post(f"/bills/{bill['id']}/pay", headers=headers)

    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"


def test_the_status_filter_selects_on_the_computed_status(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    headers = auth_token(manager)

    overdue = _create_bill(
        api_client,
        headers,
        unit_id=tree.apartment.id,
        description="Overdue rent",
        issue_date=date.today() - timedelta(days=10),
        due_date=YESTERDAY,
    ).json()
    upcoming = _create_bill(
        api_client, headers, unit_id=tree.garage.id, description="Upcoming rent"
    ).json()

    overdue_listing = api_client.get("/bills?status=overdue", headers=headers)
    pending_listing = api_client.get("/bills?status=pending", headers=headers)

    assert [row["id"] for row in overdue_listing.json()] == [overdue["id"]]
    assert [row["id"] for row in pending_listing.json()] == [upcoming["id"]]


# --- Resident scoping -------------------------------------------------------


def test_a_resident_sees_only_their_own_units_bills(
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

    mine = _create_bill(
        api_client, manager_headers, unit_id=tree.apartment.id, description="Mine"
    ).json()
    _create_bill(api_client, manager_headers, unit_id=tree.garage.id, description="Not mine")

    response = api_client.get("/bills", headers=auth_token(resident))

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [mine["id"]]


def test_a_resident_cannot_read_another_units_bill(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    resident = create_user("resident@efinges.test")
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    bill = _create_bill(api_client, auth_token(manager), unit_id=tree.apartment.id).json()

    response = api_client.get(f"/bills/{bill['id']}", headers=auth_token(resident))

    assert response.status_code == 404


def test_a_manager_can_filter_bills_by_unit(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    headers = auth_token(manager)
    _create_bill(api_client, headers, unit_id=tree.apartment.id)
    garage = _create_bill(api_client, headers, unit_id=tree.garage.id).json()

    response = api_client.get(f"/bills?unit_id={tree.garage.id}", headers=headers)

    assert [row["id"] for row in response.json()] == [garage["id"]]


def test_bills_require_a_token(api_client: TestClient) -> None:
    assert api_client.get("/bills").status_code == 401
    assert api_client.post("/bills/1/pay").status_code == 401


def test_a_manager_can_combine_a_scope_with_the_unit_filter(
    api_client: TestClient,
    create_user: Callable[..., User],
    create_property_tree: Callable[..., PropertyTree],
    assign_manager: Callable[..., ManagerAssignment],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    """Regression: the manager scope and ``?unit_id=`` must not double-join."""
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)
    tree = create_property_tree()
    assign_manager(manager, tree.community)
    headers = auth_token(manager)
    _create_bill(api_client, headers, unit_id=tree.apartment.id)
    garage_bill = _create_bill(api_client, headers, unit_id=tree.garage.id).json()

    unfiltered = api_client.get("/bills", headers=headers)
    filtered = api_client.get(f"/bills?unit_id={tree.garage.id}", headers=headers)

    assert unfiltered.status_code == 200
    assert len(unfiltered.json()) == 2
    assert [row["id"] for row in filtered.json()] == [garage_bill["id"]]
