"""Incidence and comment models (backlog task 11).

A resident reports an incidence against one of their units. The incidence
moves through a strict lifecycle, ``submitted -> in progress -> resolved ->
closed``, and only managers may advance it. All conversation happens in
:class:`Comment` rows attached to the incidence: there is no direct messaging.

The allowed transitions live in :data:`INCIDENCE_TRANSITIONS` so the rule is
declared once and both the endpoint and the tests read the same table.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.columns import enum_column


class IncidenceStatus(str, enum.Enum):
    """The four stages of an incidence, in lifecycle order."""

    SUBMITTED = "submitted"
    IN_PROGRESS = "in progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


# The only allowed forward moves. A manager may advance one step at a time;
# every other transition (skipping ahead, going backwards, or editing a closed
# incidence) is rejected with 409. ``closed`` maps to an empty set because it
# is terminal.
INCIDENCE_TRANSITIONS: dict[IncidenceStatus, frozenset[IncidenceStatus]] = {
    IncidenceStatus.SUBMITTED: frozenset({IncidenceStatus.IN_PROGRESS}),
    IncidenceStatus.IN_PROGRESS: frozenset({IncidenceStatus.RESOLVED}),
    IncidenceStatus.RESOLVED: frozenset({IncidenceStatus.CLOSED}),
    IncidenceStatus.CLOSED: frozenset(),
}


class Incidence(Base):
    """A maintenance request raised by a resident for one unit (task 11)."""

    __tablename__ = "incidences"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Every incidence starts submitted; a manager advances it from there. The
    # default is Python-side only, so it adds no column and needs no migration.
    status: Mapped[IncidenceStatus] = enum_column(
        IncidenceStatus, "incidence_status", default=IncidenceStatus.SUBMITTED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    unit: Mapped["Unit"] = relationship(back_populates="incidences")
    created_by: Mapped["User"] = relationship()
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="incidence",
        cascade="all, delete-orphan",
        order_by="Comment.id",
    )

    def can_transition_to(self, target: IncidenceStatus) -> bool:
        """Return True when ``target`` is the next allowed lifecycle stage."""
        return target in INCIDENCE_TRANSITIONS[self.status]

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"Incidence(id={self.id!r}, unit_id={self.unit_id!r}, "
            f"status={self.status.value!r})"
        )


class Comment(Base):
    """A message on an incidence thread (backlog task 11).

    Residents may comment on their own incidences and managers may comment on
    incidences for the units they manage; the author is always recorded so the
    thread stays auditable.
    """

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    incidence_id: Mapped[int] = mapped_column(
        ForeignKey("incidences.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    incidence: Mapped[Incidence] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Comment(id={self.id!r}, incidence_id={self.incidence_id!r})"
