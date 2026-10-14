"""Bill models (backlog task 10).

A bill is issued manually by a manager for one unit. It stores a money amount,
a description, the issue and due dates, and a status that is only ever
``pending`` or ``paid``. **Overdue is never stored**: it is computed from the
due date and the stored status every time a bill is serialized, so a bill
cannot drift out of date just because time passed.
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.columns import enum_column

if TYPE_CHECKING:
    # Imported for the string relationship annotations only; importing these at
    # runtime would create an import cycle between the model modules.
    from app.models.property import Unit


class BillStatus(enum.StrEnum):
    """The status stored on a bill. ``overdue`` is computed, not stored."""

    PENDING = "pending"
    PAID = "paid"


# A computed, non-persisted status used by the API so clients can filter on
# ``overdue`` without the database ever storing that value.
class BillDisplayStatus(enum.StrEnum):
    """The status a client sees: the stored status or ``overdue``."""

    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"


class Bill(Base):
    """A manual charge issued by a manager against one unit (backlog task 10).

    ``amount`` uses :class:`~decimal.Decimal` through a ``NUMERIC(12, 2)``
    column: money is never handled as binary floating point, so rounding is
    exact and totals are reproducible.
    """

    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    # A new bill is always issued as pending; only ``POST /bills/{id}/pay``
    # moves it to paid. The default is Python-side only, so it adds no column
    # and needs no migration, but it means an omitted status can never leave a
    # NULL in the database.
    status: Mapped[BillStatus] = enum_column(BillStatus, "bill_status", default=BillStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    unit: Mapped[Unit] = relationship(back_populates="bills")

    def display_status(self, today: date) -> BillDisplayStatus:
        """Return the status a client should see for this bill.

        A pending bill whose due date is in the past is reported as
        ``overdue`` without its stored status changing. ``today`` is passed in
        rather than read from the clock so callers (and tests) control it.
        """
        if self.status is BillStatus.PAID:
            return BillDisplayStatus.PAID
        if self.due_date < today:
            return BillDisplayStatus.OVERDUE
        return BillDisplayStatus.PENDING

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"Bill(id={self.id!r}, unit_id={self.unit_id!r}, "
            f"amount={self.amount!r}, status={self.status.value!r})"
        )
