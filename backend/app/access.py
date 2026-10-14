"""Row-level access rules for properties (backlog task 8).

Three roles see three different property trees:

* **Administrator** - everything, everywhere.
* **Manager** - only the communities they are assigned to, and the buildings
  and units inside them.
* **Resident** - only the units assigned to them personally.

The scoping questions ("which communities may this user write to?", "is this
unit theirs?") are answered here and nowhere else, so the routers stay thin and
the rule cannot drift between endpoints. A sentinel is used for the
administrator case: :func:`writable_community_ids` returns ``None`` (not an
empty set) to mean *unrestricted*, because "no restrictions" and "no
communities" must never be confused.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Building,
    ManagerAssignment,
    Unit,
    UnitAssignment,
    User,
    UserRole,
)


def is_administrator(user: User) -> bool:
    """Return True when ``user`` has global scope."""
    return user.role is UserRole.ADMINISTRATOR


def managed_community_ids(session: Session, user: User) -> set[int]:
    """Return the communities a manager is assigned to (empty for others)."""
    if user.role is not UserRole.MANAGER:
        return set()
    return set(
        session.scalars(
            select(ManagerAssignment.community_id).where(ManagerAssignment.manager_id == user.id)
        ).all()
    )


def writable_community_ids(session: Session, user: User) -> set[int] | None:
    """Return the communities ``user`` may write to.

    ``None`` means unrestricted (administrator). An empty set means the user
    may write to nothing (an unassigned manager).
    """
    if is_administrator(user):
        return None
    return managed_community_ids(session, user)


def readable_community_ids(session: Session, user: User) -> set[int] | None:
    """Return the communities ``user`` may read.

    Administrators get ``None`` (all). Managers get the communities they are
    assigned to. Residents get the communities that contain at least one of
    their units.
    """
    if is_administrator(user):
        return None
    if user.role is UserRole.MANAGER:
        return managed_community_ids(session, user)
    return set(
        session.scalars(
            select(Building.community_id)
            .join(Unit, Unit.building_id == Building.id)
            .join(UnitAssignment, UnitAssignment.unit_id == Unit.id)
            .where(UnitAssignment.user_id == user.id)
            .distinct()
        ).all()
    )


def resident_unit_ids(session: Session, user: User) -> set[int]:
    """Return the ids of the units assigned to ``user``."""
    return set(
        session.scalars(
            select(UnitAssignment.unit_id).where(UnitAssignment.user_id == user.id)
        ).all()
    )


def can_write_community(session: Session, user: User, community_id: int) -> bool:
    """Return True when ``user`` may create or change properties there."""
    allowed = writable_community_ids(session, user)
    return allowed is None or community_id in allowed


def can_write_building(session: Session, user: User, building: Building) -> bool:
    """Return True when ``user`` may change ``building``."""
    return can_write_community(session, user, building.community_id)


def can_write_unit(session: Session, user: User, unit: Unit) -> bool:
    """Return True when ``user`` may change ``unit`` and its bills."""
    building = session.get(Building, unit.building_id)
    if building is None:  # pragma: no cover - guarded by foreign keys
        return False
    return can_write_building(session, user, building)


def can_read_unit(session: Session, user: User, unit: Unit) -> bool:
    """Return True when ``user`` may read ``unit`` and its records.

    Managers need write access to the unit's community; residents need the
    unit to be assigned to them.
    """
    if user.role is UserRole.RESIDENT:
        return unit.id in resident_unit_ids(session, user)
    return can_write_unit(session, user, unit)


def can_comment_on_unit(session: Session, user: User, unit: Unit) -> bool:
    """Return True when ``user`` may join the unit's incidence threads.

    Same rule as reading the unit; named separately so callers express intent
    (a comment is a write, but residents may write to their own unit's thread)
    rather than reusing a helper whose name suggests read-only.
    """
    return can_read_unit(session, user, unit)
