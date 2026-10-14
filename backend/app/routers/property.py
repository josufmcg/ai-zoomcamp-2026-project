"""Property, tag, and manager-assignment endpoints (backlog task 8).

This router exposes the property tree so the frontend no longer needs seeded
rows:

* ``/communities`` - administrators create, rename, and delete communities;
  everyone signed in lists the ones they may read.
* ``/buildings`` - buildings live inside a community; managers maintain the
  ones in the communities they are assigned to.
* ``/units`` - the billable objects. Residents see only their own units,
  managers see the units in their communities, administrators see everything.
* ``/tags`` - shared free-text labels attached to buildings and units.
* ``/manager-assignments`` - the administrator-only mechanism that gives a
  manager write access to a community.

Row-level access is enforced by :mod:`app.access`; this module only decides
which helper to call and how to translate the result into 403 or 404.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import access
from app.dependencies import CurrentUser, get_db, require_role
from app.models import (
    Building,
    Community,
    ManagerAssignment,
    Tag,
    Unit,
    UnitAssignment,
    User,
    UserRole,
)
from app.schemas import (
    BuildingCreate,
    BuildingRead,
    BuildingUpdate,
    CommunityCreate,
    CommunityRead,
    CommunityUpdate,
    ManagerAssignmentCreate,
    ManagerAssignmentRead,
    TagCreate,
    TagRead,
    UnitCreate,
    UnitRead,
    UnitUpdate,
)

router = APIRouter(tags=["properties"])

AdminUser = Annotated[User, Depends(require_role(UserRole.ADMINISTRATOR))]
ManagerUser = Annotated[
    User, Depends(require_role(UserRole.MANAGER, UserRole.ADMINISTRATOR))
]


# --- shared helpers ---------------------------------------------------------


def _conflict(session: Session, detail: str) -> None:
    """Commit, translating a uniqueness violation into a 409."""
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=detail
        ) from exc


def _load_tags(session: Session, tag_ids: list[int]) -> list[Tag]:
    """Return the tags with the given ids, or raise 404 for an unknown one."""
    if not tag_ids:
        return []
    tags = list(session.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all())
    missing = set(tag_ids) - {tag.id for tag in tags}
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown tag ids: {sorted(missing)}",
        )
    return tags


def _load_community(session: Session, community_id: int) -> Community:
    """Return one community by id or raise 404."""
    community = session.get(Community, community_id)
    if community is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Community not found"
        )
    return community


def _load_building(session: Session, building_id: int) -> Building:
    """Return one building by id, with its community loaded, or raise 404."""
    building = session.scalars(
        select(Building)
        .where(Building.id == building_id)
        .options(selectinload(Building.tags))
    ).one_or_none()
    if building is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Building not found"
        )
    return building


def _load_unit(session: Session, unit_id: int) -> Unit:
    """Return one unit by id, with tags and building loaded, or raise 404."""
    unit = session.scalars(
        select(Unit)
        .where(Unit.id == unit_id)
        .options(selectinload(Unit.tags))
    ).one_or_none()
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found"
        )
    return unit


def _scope_communities(statement, community_ids: set[int] | None):
    """Restrict a statement over communities to ``community_ids``.

    ``None`` means unrestricted (administrator). An empty set means the user
    may read nothing, which is expressed as an always-false predicate so the
    query returns no rows rather than every row.
    """
    if community_ids is None:
        return statement
    if not community_ids:
        return statement.where(Community.id.in_([]))
    return statement.where(Community.id.in_(community_ids))


def _require_write(session: Session, user: User, community_id: int) -> None:
    """Raise 403 unless ``user`` may write to the given community."""
    if not access.can_write_community(session, user, community_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role"
        )


# --- communities ------------------------------------------------------------


@router.get("/communities", response_model=list[CommunityRead])
def list_communities(
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[Community]:
    """List the communities the caller may read, including nested buildings."""
    allowed = access.readable_community_ids(session, user)
    statement = _scope_communities(select(Community), allowed).order_by(Community.name)
    return list(session.scalars(statement).all())


@router.post(
    "/communities",
    response_model=CommunityRead,
    status_code=status.HTTP_201_CREATED,
)
def create_community(
    payload: CommunityCreate,
    _admin: AdminUser,
    session: Annotated[Session, Depends(get_db)],
) -> Community:
    """Create a community. Administrator only, as it defines a manager's scope."""
    community = Community(name=payload.name)
    session.add(community)
    session.commit()
    session.refresh(community)
    return community


@router.get("/communities/{community_id}", response_model=CommunityRead)
def read_community(
    community_id: int,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> Community:
    """Return one community the caller may read."""
    community = _load_community(session, community_id)
    allowed = access.readable_community_ids(session, user)
    if allowed is not None and community.id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Community not found"
        )
    return community


@router.patch("/communities/{community_id}", response_model=CommunityRead)
def update_community(
    community_id: int,
    payload: CommunityUpdate,
    _admin: AdminUser,
    session: Annotated[Session, Depends(get_db)],
) -> Community:
    """Rename a community. Administrator only."""
    community = _load_community(session, community_id)
    if payload.name is not None:
        community.name = payload.name
    session.commit()
    session.refresh(community)
    return community


@router.delete(
    "/communities/{community_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_community(
    community_id: int,
    _admin: AdminUser,
    session: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a community, cascading to its buildings, units, and records."""
    community = _load_community(session, community_id)
    session.delete(community)
    session.commit()


# --- buildings --------------------------------------------------------------


@router.get("/buildings", response_model=list[BuildingRead])
def list_buildings(
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
    community_id: Annotated[int | None, Query()] = None,
) -> list[Building]:
    """List buildings in the communities the caller may read."""
    allowed = access.readable_community_ids(session, user)
    statement = (
        select(Building)
        .options(selectinload(Building.tags), selectinload(Building.community))
        .order_by(Building.name, Building.id)
    )
    if allowed is not None:
        statement = statement.where(Building.community_id.in_(allowed or []))
    if community_id is not None:
        statement = statement.where(Building.community_id == community_id)
    return list(session.scalars(statement).all())


@router.post(
    "/buildings", response_model=BuildingRead, status_code=status.HTTP_201_CREATED
)
def create_building(
    payload: BuildingCreate,
    manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
) -> Building:
    """Create a building inside a community the caller may write to."""
    _load_community(session, payload.community_id)
    _require_write(session, manager, payload.community_id)

    building = Building(
        community_id=payload.community_id,
        name=payload.name,
        tags=_load_tags(session, payload.tag_ids),
    )
    session.add(building)
    _conflict(session, "A building with that name already exists here")
    session.refresh(building)
    return building


@router.get("/buildings/{building_id}", response_model=BuildingRead)
def read_building(
    building_id: int,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> Building:
    """Return one building the caller may read."""
    building = _load_building(session, building_id)
    allowed = access.readable_community_ids(session, user)
    if allowed is not None and building.community_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Building not found"
        )
    return building


@router.patch("/buildings/{building_id}", response_model=BuildingRead)
def update_building(
    building_id: int,
    payload: BuildingUpdate,
    manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
) -> Building:
    """Rename a building or replace its tags, within the caller's scope."""
    building = _load_building(session, building_id)
    _require_write(session, manager, building.community_id)

    if payload.name is not None:
        building.name = payload.name
    if payload.tag_ids is not None:
        building.tags = _load_tags(session, payload.tag_ids)
    _conflict(session, "A building with that name already exists here")
    session.refresh(building)
    return building


@router.delete(
    "/buildings/{building_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_building(
    building_id: int,
    manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a building, cascading to its units and their records."""
    building = _load_building(session, building_id)
    _require_write(session, manager, building.community_id)
    session.delete(building)
    session.commit()


# --- units ------------------------------------------------------------------


@router.get("/units", response_model=list[UnitRead])
def list_units(
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
    building_id: Annotated[int | None, Query()] = None,
    community_id: Annotated[int | None, Query()] = None,
    tag_id: Annotated[int | None, Query()] = None,
) -> list[Unit]:
    """List units visible to the caller, with optional filters.

    A resident only ever sees their own units; a manager sees the units in the
    communities they manage; an administrator sees every unit.

    Every filter is written as a correlated ``EXISTS`` (``.has()`` / ``.any()``)
    rather than a join, so combining the scope rule with the ``community_id``
    filter cannot join ``buildings`` twice.
    """
    statement = (
        select(Unit)
        .options(selectinload(Unit.tags))
        .order_by(Unit.building_id, Unit.identifier)
    )

    if user.role is UserRole.RESIDENT:
        statement = statement.where(
            Unit.assignments.any(UnitAssignment.user_id == user.id)
        )
    else:
        allowed = access.readable_community_ids(session, user)
        if allowed is not None:
            statement = statement.where(
                Unit.building.has(Building.community_id.in_(allowed or []))
            )

    if building_id is not None:
        statement = statement.where(Unit.building_id == building_id)
    if community_id is not None:
        statement = statement.where(
            Unit.building.has(Building.community_id == community_id)
        )
    if tag_id is not None:
        statement = statement.where(Unit.tags.any(Tag.id == tag_id))
    return list(session.scalars(statement).all())


@router.post("/units", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
def create_unit(
    payload: UnitCreate,
    manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
) -> Unit:
    """Create a unit inside a building the caller may write to."""
    building = _load_building(session, payload.building_id)
    _require_write(session, manager, building.community_id)

    unit = Unit(
        building_id=building.id,
        identifier=payload.identifier,
        unit_type=payload.unit_type,
        tags=_load_tags(session, payload.tag_ids),
    )
    session.add(unit)
    _conflict(session, "A unit with that identifier already exists here")
    session.refresh(unit)
    return unit


@router.get("/units/{unit_id}", response_model=UnitRead)
def read_unit(
    unit_id: int,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> Unit:
    """Return one unit, limited to the caller's own scope.

    A unit outside the caller's scope is reported as 404 rather than 403 so
    the endpoint does not reveal that it exists.
    """
    unit = _load_unit(session, unit_id)
    if not access.can_read_unit(session, user, unit):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found"
        )
    return unit


@router.patch("/units/{unit_id}", response_model=UnitRead)
def update_unit(
    unit_id: int,
    payload: UnitUpdate,
    manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
) -> Unit:
    """Change a unit's identifier, type, or tags within the caller's scope."""
    unit = _load_unit(session, unit_id)
    _require_write(session, manager, _community_of(session, unit))

    if payload.identifier is not None:
        unit.identifier = payload.identifier
    if payload.unit_type is not None:
        unit.unit_type = payload.unit_type
    if payload.tag_ids is not None:
        unit.tags = _load_tags(session, payload.tag_ids)
    _conflict(session, "A unit with that identifier already exists here")
    session.refresh(unit)
    return unit


@router.delete("/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unit(
    unit_id: int,
    manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a unit, cascading to its assignments, bills, and incidences."""
    unit = _load_unit(session, unit_id)
    _require_write(session, manager, _community_of(session, unit))
    session.delete(unit)
    session.commit()


def _community_of(session: Session, unit: Unit) -> int:
    """Return the community id that owns ``unit``."""
    building = session.get(Building, unit.building_id)
    if building is None:  # pragma: no cover - guarded by foreign keys
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found"
        )
    return building.community_id


# --- tags -------------------------------------------------------------------


@router.get("/tags", response_model=list[TagRead])
def list_tags(
    _user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[Tag]:
    """List every tag. Tags are shared labels, so any signed-in user may read."""
    return list(session.scalars(select(Tag).order_by(Tag.name)).all())


@router.post("/tags", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: TagCreate,
    _manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
) -> Tag:
    """Create a tag. Managers and administrators only."""
    tag = Tag(name=payload.name)
    session.add(tag)
    _conflict(session, "A tag with that name already exists")
    session.refresh(tag)
    return tag


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: int,
    _manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a tag, detaching it from every building and unit."""
    tag = session.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )
    session.delete(tag)
    session.commit()


# --- manager-to-community assignments ---------------------------------------


@router.get("/manager-assignments", response_model=list[ManagerAssignmentRead])
def list_manager_assignments(
    _admin: AdminUser,
    session: Annotated[Session, Depends(get_db)],
    manager_id: Annotated[int | None, Query()] = None,
) -> list[ManagerAssignment]:
    """List manager-to-community assignments (administrator only)."""
    statement = (
        select(ManagerAssignment)
        .options(
            selectinload(ManagerAssignment.manager),
            selectinload(ManagerAssignment.community),
        )
        .order_by(ManagerAssignment.id)
    )
    if manager_id is not None:
        statement = statement.where(ManagerAssignment.manager_id == manager_id)
    return list(session.scalars(statement).all())


@router.post(
    "/manager-assignments",
    response_model=ManagerAssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_manager_assignment(
    payload: ManagerAssignmentCreate,
    _admin: AdminUser,
    session: Annotated[Session, Depends(get_db)],
) -> ManagerAssignment:
    """Give a manager write access to a community (administrator only).

    Returns 404 for an unknown manager or community, 422 when the user is not
    a manager, and 409 when the pair is already assigned.
    """
    manager = session.get(User, payload.manager_id)
    if manager is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Manager not found"
        )
    if manager.role is not UserRole.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only managers can be assigned to communities",
        )
    _load_community(session, payload.community_id)

    assignment = ManagerAssignment(
        manager_id=manager.id, community_id=payload.community_id
    )
    session.add(assignment)
    _conflict(session, "Manager is already assigned to that community")
    session.refresh(assignment)
    return assignment


@router.delete(
    "/manager-assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_manager_assignment(
    assignment_id: int,
    _admin: AdminUser,
    session: Annotated[Session, Depends(get_db)],
) -> None:
    """Remove a manager's access to a community (administrator only)."""
    assignment = session.get(ManagerAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manager assignment not found",
        )
    session.delete(assignment)
    session.commit()
