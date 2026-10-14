"""Property, tag, and unit-assignment schemas (backlog tasks 7 and 8).

The read models embed their tag labels so a client can render a building or
unit row without a second request. Request models carry ``tag_ids`` to attach
existing tags, keeping tag creation separate from tag attachment.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models import OwnershipType, UnitAssignment, UnitType
from app.schemas.auth import UserRead


class TagRead(BaseModel):
    """A free-text label attached to a building or a unit."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TagCreate(BaseModel):
    """Request body for creating a tag (managers and administrators)."""

    name: str = Field(min_length=1, max_length=100)


class CommunityCreate(BaseModel):
    """Request body for ``POST /communities`` (administrators only)."""

    name: str = Field(min_length=1, max_length=200)


class CommunityUpdate(BaseModel):
    """Request body for ``PATCH /communities/{id}`` (administrators only)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)


class CommunityRead(BaseModel):
    """Public representation of a community."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class BuildingCreate(BaseModel):
    """Request body for ``POST /buildings`` (administrators only).

    A building belongs to a fixed community, so ``community_id`` is required
    and immutable; moving a building means deleting and recreating it.
    """

    community_id: int
    name: str = Field(min_length=1, max_length=200)
    tag_ids: list[int] = Field(default_factory=list)


class BuildingUpdate(BaseModel):
    """Request body for ``PATCH /buildings/{id}`` (manager for its community)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    tag_ids: list[int] | None = None


class BuildingRead(BaseModel):
    """Public representation of a building, with its tags."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    community_id: int
    name: str
    tags: list[TagRead] = Field(default_factory=list)


class UnitCreate(BaseModel):
    """Request body for ``POST /units`` (manager for the building's community)."""

    building_id: int
    identifier: str = Field(min_length=1, max_length=100)
    unit_type: UnitType
    tag_ids: list[int] = Field(default_factory=list)


class UnitUpdate(BaseModel):
    """Request body for ``PATCH /units/{id}``."""

    identifier: str | None = Field(default=None, min_length=1, max_length=100)
    unit_type: UnitType | None = None
    tag_ids: list[int] | None = None


class UnitRead(BaseModel):
    """Public representation of a unit, with its tags.

    The parent building id is included so the frontend can group units without
    extra requests.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int
    identifier: str
    unit_type: UnitType
    tags: list[TagRead] = Field(default_factory=list)


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
            tags=[TagRead.model_validate(tag) for tag in unit.tags],
            ownership_type=assignment.ownership_type,
        )


class ManagerAssignmentCreate(BaseModel):
    """Request body for assigning a manager to a community (administrators only)."""

    manager_id: int
    community_id: int


class ManagerAssignmentRead(BaseModel):
    """Public representation of a manager-to-community assignment."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    manager_id: int
    community_id: int
    manager: UserRead
    community: CommunityRead
