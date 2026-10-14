"""Bill management endpoints (backlog task 10).

Managers issue manual bills against individual units; residents read the bills
for their own units. Marking a bill paid is a manager action. **Overdue is
never stored**: every response computes it from the due date and an explicit
"today", so a pending bill becomes overdue the moment the date passes without
any background job.

Scoping reuses :mod:`app.access`: a manager needs write access to the unit's
community, and a resident needs the unit to be one of theirs.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import access
from app.dependencies import CurrentUser, get_db, require_role
from app.models import (
    Bill,
    BillDisplayStatus,
    BillStatus,
    Building,
    Unit,
    UnitAssignment,
    User,
    UserRole,
)
from app.schemas import BillCreate, BillRead

router = APIRouter(tags=["bills"])

ManagerUser = Annotated[User, Depends(require_role(UserRole.MANAGER, UserRole.ADMINISTRATOR))]


def _load_bill(session: Session, bill_id: int) -> Bill:
    """Return one bill by id, with its unit loaded, or raise 404."""
    bill = session.scalars(
        select(Bill).where(Bill.id == bill_id).options(selectinload(Bill.unit))
    ).one_or_none()
    if bill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return bill


def _load_unit(session: Session, unit_id: int) -> Unit:
    """Return one unit by id or raise 404."""
    unit = session.get(Unit, unit_id)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    return unit


@router.get("/bills", response_model=list[BillRead])
def list_bills(
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
    unit_id: Annotated[int | None, Query()] = None,
    bill_status: Annotated[BillDisplayStatus | None, Query(alias="status")] = None,
) -> list[BillRead]:
    """List bills visible to the caller, optionally filtered.

    Residents only see bills for their own units. ``status`` filters on the
    computed status, so ``status=overdue`` returns pending bills past their
    due date without changing anything in the database.
    """
    today = date.today()
    statement = select(Bill).options(selectinload(Bill.unit)).order_by(Bill.id)

    if user.role is UserRole.RESIDENT:
        # ``Bill.unit.has(...)`` correlates ``units`` with ``bills``; writing
        # ``Unit.assignments.any(...)`` directly would add ``units`` to the
        # query's FROM clause as a cartesian product and match every bill.
        statement = statement.where(
            Bill.unit.has(Unit.assignments.any(UnitAssignment.user_id == user.id))
        )
    else:
        allowed = access.readable_community_ids(session, user)
        if allowed is not None:
            statement = statement.where(
                Bill.unit.has(Unit.building.has(Building.community_id.in_(allowed or [])))
            )

    if unit_id is not None:
        statement = statement.where(Bill.unit_id == unit_id)

    bills = list(session.scalars(statement).all())
    responses = [BillRead.from_bill(bill, today=today) for bill in bills]
    if bill_status is not None:
        responses = [row for row in responses if row.status is bill_status]
    return responses


@router.post("/bills", response_model=BillRead, status_code=status.HTTP_201_CREATED)
def create_bill(
    payload: BillCreate,
    manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
) -> BillRead:
    """Issue a manual bill for a unit the caller manages.

    ``issue_date`` defaults to today. ``due_date`` before ``issue_date`` is
    rejected with 422 because the bill would be overdue the moment it is
    issued.
    """
    unit = _load_unit(session, payload.unit_id)
    if not access.can_write_unit(session, manager, unit):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    issue_date = payload.issue_date or date.today()
    if payload.due_date < issue_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="due_date must not be before issue_date",
        )

    bill = Bill(
        unit_id=unit.id,
        amount=payload.amount,
        description=payload.description,
        issue_date=issue_date,
        due_date=payload.due_date,
        status=BillStatus.PENDING,
    )
    session.add(bill)
    session.commit()
    session.refresh(bill)
    return BillRead.from_bill(bill, today=date.today())


@router.get("/bills/{bill_id}", response_model=BillRead)
def read_bill(
    bill_id: int,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> BillRead:
    """Return one bill the caller may see (own unit, or managed community)."""
    bill = _load_bill(session, bill_id)
    if not access.can_read_unit(session, user, bill.unit):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return BillRead.from_bill(bill, today=date.today())


@router.post("/bills/{bill_id}/pay", response_model=BillRead)
def pay_bill(
    bill_id: int,
    manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
) -> BillRead:
    """Mark a bill paid. Manager action; the stored status becomes ``paid``.

    Paying an already paid bill is rejected with 409: the transition is
    one-way and idempotency here would hide a double payment.
    """
    bill = _load_bill(session, bill_id)
    if not access.can_write_unit(session, manager, bill.unit):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if bill.status is BillStatus.PAID:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bill is already paid")

    bill.status = BillStatus.PAID
    session.commit()
    session.refresh(bill)
    return BillRead.from_bill(bill, today=date.today())
