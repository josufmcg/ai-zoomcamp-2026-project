"""Identity models: users, roles, and unit assignments (tasks 6, 7, and 8).

:class:`User` is any person who can sign in, with one of three roles.
:class:`UnitAssignment` links a resident to a unit they own or rent, and
:class:`OwnershipType` records that legal relationship. A resident may hold
several units, so the association is one user to many units.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.columns import enum_column


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


class User(Base):
    """A person who can sign in, with one of three roles.

    Passwords are stored as an Argon2 hash, never in clear text. The role is
    restricted to administrator, manager, or resident both in Python (the
    :class:`UserRole` enum) and in the database.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = enum_column(UserRole, "user_role")
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
    # The communities this user manages (backlog task 8). Empty for residents
    # and for administrators, who have global scope.
    manager_assignments: Mapped[list["ManagerAssignment"]] = relationship(
        back_populates="manager",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"User(id={self.id!r}, email={self.email!r}, role={self.role.value!r})"


class UnitAssignment(Base):
    """Links one resident to one unit they own or occupy (backlog task 7).

    A resident can hold several units, so a user has many assignments; a unit
    belongs to at most one resident at a time, enforced by the unique
    constraint on ``unit_id``.
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
    ownership_type: Mapped[OwnershipType] = enum_column(
        OwnershipType, "ownership_type"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="unit_assignments")
    unit: Mapped["Unit"] = relationship(back_populates="assignments")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"UnitAssignment(id={self.id!r}, user_id={self.user_id!r}, "
            f"unit_id={self.unit_id!r}, ownership_type={self.ownership_type.value!r})"
        )
