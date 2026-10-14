"""Property hierarchy and tag models (backlog task 5).

The property tree is Community -> Building -> Unit. A unit is an apartment, a
garage, or a storage room, and is managed and billed individually. Managers can
attach free-text :class:`Tag` labels to buildings and units for grouping and
scoping.

Backlog task 6 adds :class:`User`, whose :class:`UserRole` is restricted to
administrator, manager, or resident.

Backlog task 7 adds :class:`UnitAssignment`, which links a resident to a unit
they own or rent. A resident may hold several units (for example an apartment
plus a garage and a storage room), so the relationship is one user to many
units with the pair kept unique.

The restricted value sets (unit type, user role, ownership type) are enforced
both in Python (the enums) and in the database (native enums on PostgreSQL,
``VARCHAR`` columns with ``CHECK`` constraints on SQLite), so an invalid value
is rejected even by a direct SQL insert.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Table,
    Column,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UnitType(str, enum.Enum):
    """The kinds of unit a building can contain."""

    APARTMENT = "apartment"
    GARAGE = "garage"
    STORAGE = "storage"


class UserRole(str, enum.Enum):
    """The three roles a user can hold (backlog task 6)."""

    ADMINISTRATOR = "administrator"
    MANAGER = "manager"
    RESIDENT = "resident"


class OwnershipType(str, enum.Enum):
    """How a resident holds a unit (backlog task 7).

    ``OWNER`` covers outright ownership; ``TENANT`` covers a rental or other
    occupancy agreement. Both are billed and voted on the same way, so the flag
    only records the legal relationship to the unit.
    """

    OWNER = "owner"
    TENANT = "tenant"


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
    assignments: Mapped[list["UnitAssignment"]] = relationship(
        back_populates="unit",
        cascade="all, delete-orphan",
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


class User(Base):
    """A person who can sign in, with one of three roles (backlog task 6).

    Passwords are stored as an Argon2 hash, never in clear text. The role is
    restricted to administrator, manager, or resident both in Python (the
    :class:`UserRole` enum) and in the database (a native enum on PostgreSQL, a
    ``VARCHAR`` with a ``CHECK`` constraint on SQLite).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=True,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # The units this user owns or rents (backlog task 7). Only residents are
    # given assignments by the manager endpoints, but the relationship itself
    # does not restrict the role so administrators can inspect every row.
    unit_assignments: Mapped[list["UnitAssignment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"User(id={self.id!r}, email={self.email!r}, role={self.role.value!r})"


class UnitAssignment(Base):
    """Links one resident to one unit they own or occupy (backlog task 7).

    A resident can hold several units, so a user has many assignments; a unit
    belongs to at most one resident at a time, enforced by the unique
    constraint on ``unit_id``. The :class:`OwnershipType` flag records whether
    the resident owns the unit or rents it and is restricted in the database
    just like the unit type and user role.
    """

    __tablename__ = "unit_assignments"
    __table_args__ = (
        # A unit has at most one assignment, so the same resident cannot be
        # assigned the same unit twice. Residents still hold many units,
        # because only ``unit_id`` carries the unique constraint.
        UniqueConstraint("unit_id", name="uq_unit_assignment_unit"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ownership_type: Mapped[OwnershipType] = mapped_column(
        Enum(
            OwnershipType,
            name="ownership_type",
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

    user: Mapped[User] = relationship(back_populates="unit_assignments")
    unit: Mapped[Unit] = relationship(back_populates="assignments")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"UnitAssignment(id={self.id!r}, user_id={self.user_id!r}, "
            f"unit_id={self.unit_id!r}, ownership_type={self.ownership_type.value!r})"
        )
