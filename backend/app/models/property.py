"""Property hierarchy and tag models (backlog tasks 5 and 8).

The property tree is Community -> Building -> Unit. A unit is an apartment, a
garage, or a storage room, and is managed and billed individually. Managers can
attach free-text :class:`Tag` labels to buildings and units for grouping and
scoping.

Backlog task 8 adds full CRUD endpoints for this tree plus the
:class:`ManagerAssignment` model, which records which communities a manager is
responsible for. Administrators see every property; managers only see the
communities they are assigned to.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.columns import enum_column


class UnitType(str, enum.Enum):
    """The kinds of unit a building can contain."""

    APARTMENT = "apartment"
    GARAGE = "garage"
    STORAGE = "storage"


# Association tables for the many-to-many tag relationships. Tags are shared
# labels, so the same tag row can be attached to many buildings and units.
building_tags = Table(
    "building_tags",
    Base.metadata,
    Column(
        "building_id",
        ForeignKey("buildings.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

unit_tags = Table(
    "unit_tags",
    Base.metadata,
    Column(
        "unit_id",
        ForeignKey("units.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Community(Base):
    """A residential community (neighborhood) made up of buildings."""

    __tablename__ = "communities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    buildings: Mapped[list["Building"]] = relationship(
        back_populates="community",
        cascade="all, delete-orphan",
        order_by="Building.name",
    )
    manager_assignments: Mapped[list["ManagerAssignment"]] = relationship(
        back_populates="community",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Community(id={self.id!r}, name={self.name!r})"


class Building(Base):
    """A building (or block) inside a community."""

    __tablename__ = "buildings"
    __table_args__ = (
        UniqueConstraint("community_id", "name", name="uq_building_community_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    community: Mapped[Community] = relationship(back_populates="buildings")
    units: Mapped[list["Unit"]] = relationship(
        back_populates="building",
        cascade="all, delete-orphan",
        order_by="Unit.identifier",
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary=building_tags,
        back_populates="buildings",
        order_by="Tag.name",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Building(id={self.id!r}, name={self.name!r})"


class Unit(Base):
    """An individual apartment, garage, or storage room inside a building."""

    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("building_id", "identifier", name="uq_unit_building_identifier"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_type: Mapped[UnitType] = enum_column(UnitType, "unit_type")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    building: Mapped[Building] = relationship(back_populates="units")
    tags: Mapped[list["Tag"]] = relationship(
        secondary=unit_tags,
        back_populates="units",
        order_by="Tag.name",
    )
    assignments: Mapped[list["UnitAssignment"]] = relationship(
        back_populates="unit",
        cascade="all, delete-orphan",
    )
    bills: Mapped[list["Bill"]] = relationship(
        back_populates="unit",
        cascade="all, delete-orphan",
        order_by="Bill.id",
    )
    incidences: Mapped[list["Incidence"]] = relationship(
        back_populates="unit",
        cascade="all, delete-orphan",
        order_by="Incidence.id",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"Unit(id={self.id!r}, identifier={self.identifier!r}, "
            f"unit_type={self.unit_type.value!r})"
        )


class Tag(Base):
    """A free-text label managers attach to buildings and units."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    buildings: Mapped[list[Building]] = relationship(
        secondary=building_tags,
        back_populates="tags",
    )
    units: Mapped[list[Unit]] = relationship(
        secondary=unit_tags,
        back_populates="tags",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Tag(id={self.id!r}, name={self.name!r})"


class ManagerAssignment(Base):
    """Assigns one manager to one community (backlog task 8).

    Administrators have global scope, so they are never stored here. A manager
    can be responsible for several communities and a community can have several
    managers; the unique constraint stops the same pair being recorded twice.
    """

    __tablename__ = "manager_assignments"
    __table_args__ = (
        UniqueConstraint(
            "manager_id", "community_id", name="uq_manager_assignment_pair"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    manager_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    community_id: Mapped[int] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    manager: Mapped["User"] = relationship(back_populates="manager_assignments")
    community: Mapped[Community] = relationship(back_populates="manager_assignments")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"ManagerAssignment(id={self.id!r}, manager_id={self.manager_id!r}, "
            f"community_id={self.community_id!r})"
        )
