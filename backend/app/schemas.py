"""Pydantic schemas for authentication, users, and unit assignments."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models import OwnershipType, UnitAssignment, UnitType, UserRole


class Token(BaseModel):
    """Response body for a successful ``POST /auth/token`` login."""

    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    """Public representation of a user. Never exposes the password hash.

    ``email`` is a plain string: the database stores emails without a format
    constraint, so the response schema must serialize stored data faithfully
    rather than fail on addresses that use reserved domains such as ``.test``.
    Email *format* validation belongs on the create/update request models that
    arrive with the administrator user-management endpoints (backlog task 9).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: UserRole
    is_active: bool


class UnitRead(BaseModel):
    """Public representation of a unit (backlog task 7).

    The parent building id is included so the frontend can group a resident's
    units without extra requests; the full property tree endpoints arrive with
    backlog task 8.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int
    identifier: str
    unit_type: UnitType


class AssignmentCreate(BaseModel):
    """Request body for assigning a resident to a unit."""

    user_id: int
    unit_id: int
    ownership_type: OwnershipType


class AssignmentRead(BaseModel):
    """Public representation of a unit assignment.

    The embedded user and unit objects let manager screens render a table
    without a second request, and they never contain the password hash.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    unit_id: int
    ownership_type: OwnershipType
    user: UserRead
    unit: UnitRead


class MyUnitRead(UnitRead):
    """A unit belonging to the signed-in resident, with the ownership flag.

    Built from a :class:`app.models.UnitAssignment` so the resident can tell
    which units they own from the ones they rent.
    """

    ownership_type: OwnershipType

    @classmethod
    def from_assignment(cls, assignment: UnitAssignment) -> "MyUnitRead":
        """Build the response from an assignment and its loaded unit."""
        unit = assignment.unit
        return cls(
            id=unit.id,
            building_id=unit.building_id,
            identifier=unit.identifier,
            unit_type=unit.unit_type,
            ownership_type=assignment.ownership_type,
        )

