"""Initiative and vote models (backlog task 12).

Managers create an :class:`Initiative` with a title, description, open and
close dates, a set of :class:`InitiativeOption` choices, and an *eligible scope*
expressed as a filter over communities, buildings, unit types, and tags. The
scope is stored as JSON because it is open-ended (any combination of the four
filters) and is only ever read as a whole.

Voting follows the one-ballot-per-unit rule: a resident owning several eligible
units casts one :class:`Vote` per unit. The unique constraint on
``(initiative_id, unit_id)`` makes a second ballot for the same unit
impossible even if two requests race. Ballots cast after the close date are
rejected by the endpoint, not by the database, because "now" is not a fact the
database can check.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    # Imported for the string relationship annotations only; importing these at
    # runtime would create an import cycle between the model modules.
    from app.models.identity import User
    from app.models.property import Unit


class Initiative(Base):
    """A community vote created by a manager (backlog task 12)."""

    __tablename__ = "initiatives"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    opens_at: Mapped[date] = mapped_column(Date, nullable=False)
    closes_at: Mapped[date] = mapped_column(Date, nullable=False)
    # Eligibility filter, for example
    # {"community_ids": [1], "unit_types": ["garage"], "tag_ids": [4]}.
    # Absent keys mean "no restriction"; an empty object means "every unit".
    scope: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    created_by: Mapped[User] = relationship()
    options: Mapped[list[InitiativeOption]] = relationship(
        back_populates="initiative",
        cascade="all, delete-orphan",
        order_by="InitiativeOption.position",
    )
    votes: Mapped[list[Vote]] = relationship(
        back_populates="initiative",
        cascade="all, delete-orphan",
        order_by="Vote.id",
    )

    def is_open_on(self, today: date) -> bool:
        """Return True when ballots are accepted on ``today``.

        ``today`` is passed in rather than read from the clock so the endpoint
        and the tests agree on a single, explicit "now".
        """
        return self.opens_at <= today <= self.closes_at

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Initiative(id={self.id!r}, title={self.title!r})"


class InitiativeOption(Base):
    """One selectable answer on an initiative (backlog task 12).

    An initiative always has two or more options; the ``position`` column keeps
    them in the order the manager entered them, which is the order the frontend
    renders.
    """

    __tablename__ = "initiative_options"
    __table_args__ = (
        UniqueConstraint("initiative_id", "label", name="uq_initiative_option_label"),
        UniqueConstraint("initiative_id", "position", name="uq_initiative_option_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    initiative_id: Mapped[int] = mapped_column(
        ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    initiative: Mapped[Initiative] = relationship(back_populates="options")
    votes: Mapped[list[Vote]] = relationship(back_populates="option")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"InitiativeOption(id={self.id!r}, initiative_id={self.initiative_id!r}, "
            f"label={self.label!r})"
        )


class Vote(Base):
    """One ballot: a chosen option for one eligible unit (backlog task 12).

    ``unit_id`` is the vote's key, not ``voter_id``: a resident with three
    eligible units casts three independent ballots. ``voter_id`` is recorded
    alongside so the ballot stays auditable and so the resident can list their
    own votes.
    """

    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("initiative_id", "unit_id", name="uq_vote_initiative_unit"),
        CheckConstraint("unit_id > 0", name="ck_vote_unit_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    initiative_id: Mapped[int] = mapped_column(
        ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    option_id: Mapped[int] = mapped_column(
        ForeignKey("initiative_options.id", ondelete="CASCADE"), nullable=False
    )
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    voter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    initiative: Mapped[Initiative] = relationship(back_populates="votes")
    option: Mapped[InitiativeOption] = relationship(back_populates="votes")
    unit: Mapped[Unit] = relationship()
    voter: Mapped[User] = relationship()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"Vote(id={self.id!r}, initiative_id={self.initiative_id!r}, "
            f"unit_id={self.unit_id!r}, option_id={self.option_id!r})"
        )
