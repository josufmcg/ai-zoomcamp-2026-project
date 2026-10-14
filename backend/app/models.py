"""Property hierarchy and tag models (backlog task 5).

The property tree is Community -> Building -> Unit. A unit is an apartment, a
garage, or a storage room, and is managed and billed individually. Managers can
attach free-text :class:`Tag` labels to buildings and units for grouping and
scoping.

The unit type is restricted to the three allowed values both in Python (the
:class:`UnitType` enum) and in the database (a native enum on PostgreSQL, a
``VARCHAR`` with a ``CHECK`` constraint on SQLite), so an invalid type is
rejected even by a direct SQL insert.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Table,
    Column,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


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
    unit_type: Mapped[UnitType] = mapped_column(
        Enum(
            UnitType,
            name="unit_type",
            native_enum=True,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    building: Mapped[Building] = relationship(back_populates="units")
    tags: Mapped[list["Tag"]] = relationship(
        secondary=unit_tags,
        back_populates="units",
        order_by="Tag.name",
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
