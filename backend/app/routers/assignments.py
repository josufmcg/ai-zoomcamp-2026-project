"""Resident and unit assignment endpoints (backlog task 7).

Assignments link a resident to the units they own or rent. Managers (and
administrators) create, list, and remove them:

* ``GET /assignments`` lists every assignment, optionally filtered by resident
  or unit.
* ``POST /assignments`` assigns one resident to one unit.
* ``DELETE /assignments/{assignment_id}`` removes an assignment.

A resident may hold several units, so creating several assignments for the
same user is expected. Assigning the *same unit* twice is rejected with 409:
a unit has at most one resident at a time.

Residents cannot manage assignments. Instead, ``GET /auth/me/units`` returns
the units belonging to the signed-in resident, which is the helper the resident
screens and the later billing, incidence, and voting tasks build on.

``GET /residents`` is the minimal resident lookup the manager screens need to
pick whom to assign to a unit: it lists resident accounts (never their
password), so a manager does not need the administrator-only ``GET /users``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.dependencies import CurrentUser, get_db, require_role
from app.models import Unit, UnitAssignment, User, UserRole
from app.schemas import AssignmentCreate, AssignmentRead, MyUnitRead, UserRead

router = APIRouter(tags=["assignments"])

# Managers and administrators manage assignments; residents only read their
# own. The dependency returns 401 for a missing token and 403 for a resident.
ManagerUser = Annotated[User, Depends(require_role(UserRole.MANAGER, UserRole.ADMINISTRATOR))]


@router.get("/residents", response_model=list[UserRead])
def list_residents(
    _manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
    is_active: Annotated[bool | None, Query()] = None,
) -> list[User]:
    """List resident accounts so a manager can pick whom to assign.

    Only residents are returned (never managers or administrators) and the
    response uses :class:`~app.schemas.auth.UserRead`, so a password hash can
    never leak. ``is_active`` optionally filters to active or deactivated
    residents; by default every resident is listed.
    """
    statement = select(User).where(User.role == UserRole.RESIDENT)
    if is_active is not None:
        statement = statement.where(User.is_active == is_active)
    return list(session.scalars(statement.order_by(User.email)).all())


def list_assignments_for_user(session: Session, user_id: int) -> list[UnitAssignment]:
    """Return the assignments belonging to one resident, units preloaded.

    Used both by the manager listing endpoints and by the resident helper
    below, so the resident-scope rule lives in exactly one place.
    """
    return list(
        session.scalars(
            select(UnitAssignment)
            .where(UnitAssignment.user_id == user_id)
            .options(
                selectinload(UnitAssignment.unit),
                selectinload(UnitAssignment.user),
            )
            .order_by(UnitAssignment.unit_id)
        ).all()
    )


def units_for_user(session: Session, user_id: int) -> list[MyUnitRead]:
    """Return every unit assigned to one resident, with the ownership flag."""
    return [
        MyUnitRead.from_assignment(assignment)
        for assignment in list_assignments_for_user(session, user_id)
    ]


def _load_assignment(session: Session, assignment_id: int) -> UnitAssignment:
    """Return one assignment by id or raise 404."""
    assignment = session.scalars(
        select(UnitAssignment)
        .where(UnitAssignment.id == assignment_id)
        .options(
            selectinload(UnitAssignment.unit),
            selectinload(UnitAssignment.user),
        )
    ).one_or_none()
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    return assignment


@router.get("/auth/me/units", response_model=list[MyUnitRead])
def read_my_units(
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[MyUnitRead]:
    """Return the units belonging to the signed-in user (the resident helper).

    A resident can hold several units, so the response is always a list. The
    endpoint only ever reads the caller's own assignments, so no role check is
    needed: an administrator calling it simply sees their own (usually empty)
    list.
    """
    return units_for_user(session, user.id)


@router.get("/assignments", response_model=list[AssignmentRead])
def list_assignments(
    _manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
    user_id: Annotated[int | None, Query()] = None,
    unit_id: Annotated[int | None, Query()] = None,
) -> list[UnitAssignment]:
    """List assignments, optionally filtered by resident or unit."""
    statement = (
        select(UnitAssignment)
        .options(
            selectinload(UnitAssignment.unit),
            selectinload(UnitAssignment.user),
        )
        .order_by(UnitAssignment.id)
    )
    if user_id is not None:
        statement = statement.where(UnitAssignment.user_id == user_id)
    if unit_id is not None:
        statement = statement.where(UnitAssignment.unit_id == unit_id)
    return list(session.scalars(statement).all())


@router.post(
    "/assignments",
    response_model=AssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    payload: AssignmentCreate,
    _manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
) -> UnitAssignment:
    """Assign one resident to one unit.

    Returns 404 when the user or unit does not exist, 409 when the unit is
    already assigned, and 422 when the target user is not a resident.
    """
    user = session.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role is not UserRole.RESIDENT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only residents can be assigned to units",
        )

    unit = session.get(Unit, payload.unit_id)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")

    existing = session.scalars(
        select(UnitAssignment).where(UnitAssignment.unit_id == payload.unit_id)
    ).one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unit is already assigned",
        )

    assignment = UnitAssignment(
        user_id=user.id,
        unit_id=unit.id,
        ownership_type=payload.ownership_type,
    )
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    return assignment


@router.delete(
    "/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_assignment(
    assignment_id: int,
    _manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
) -> None:
    """Remove an assignment (the resident loses access to that unit)."""
    assignment = _load_assignment(session, assignment_id)
    session.delete(assignment)
    session.commit()
