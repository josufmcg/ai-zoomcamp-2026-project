"""Bill schemas (backlog task 10).

``BillRead`` exposes ``status`` as the *display* status: the stored
``pending``/``paid`` value, or ``overdue`` when a pending bill is past its due
date. The stored status is never rewritten, so the response is computed at
serialization time from the bill and an explicit "today".
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models import Bill, BillDisplayStatus, UnitType


class BillCreate(BaseModel):
    """Request body for ``POST /bills`` (manager for the unit's community).

    ``amount`` is a :class:`~decimal.Decimal` with at most two decimal places
    and a positive value, so money never travels as binary floating point.
    ``issue_date`` defaults to today when the manager omits it.
    """

    unit_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str = Field(min_length=1, max_length=500)
    issue_date: date | None = None
    due_date: date


class BillRead(BaseModel):
    """Public representation of a bill, with the computed display status."""

    id: int
    unit_id: int
    unit_identifier: str
    unit_type: UnitType
    amount: Decimal
    description: str
    issue_date: date
    due_date: date
    status: BillDisplayStatus

    @classmethod
    def from_bill(cls, bill: Bill, *, today: date) -> BillRead:
        """Build the response, computing ``overdue`` from the due date."""
        return cls(
            id=bill.id,
            unit_id=bill.unit_id,
            unit_identifier=bill.unit.identifier,
            unit_type=bill.unit.unit_type,
            amount=bill.amount,
            description=bill.description,
            issue_date=bill.issue_date,
            due_date=bill.due_date,
            status=bill.display_status(today),
        )
