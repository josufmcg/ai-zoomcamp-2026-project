"""Incidence and comment endpoints (backlog task 11).

Residents report incidences against their own units and may comment on them.
Managers advance the status through the strict lifecycle and may comment on
incidences for the units they manage. All conversation stays in the comment
thread attached to the incidence.

The lifecycle rule lives in :data:`app.models.INCIDENCE_TRANSITIONS`; this
router only asks the model whether a transition is allowed and turns a "no"
into a 409 that names the allowed next stage.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import access
from app.dependencies import CurrentUser, get_db, require_role
from app.models import (
    INCIDENCE_TRANSITIONS,
    Building,
    Comment,
    Incidence,
    IncidenceStatus,
    Unit,
    User,
    UserRole,
)
from app.schemas import (
    CommentCreate,
    CommentRead,
    IncidenceCreate,
    IncidenceRead,
    IncidenceStatusUpdate,
)

router = APIRouter(tags=["incidences"])

ManagerUser = Annotated[User, Depends(require_role(UserRole.MANAGER, UserRole.ADMINISTRATOR))]


def _load_incidence(session: Session, incidence_id: int) -> Incidence:
    """Return one incidence with its unit, author, and thread loaded, or 404."""
    incidence = session.scalars(
        select(Incidence)
        .where(Incidence.id == incidence_id)
        .options(
            selectinload(Incidence.unit),
            selectinload(Incidence.created_by),
            selectinload(Incidence.comments).selectinload(Comment.author),
        )
    ).one_or_none()
    if incidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidence not found")
    return incidence


def _comment_read(comment: Comment) -> CommentRead:
    """Build the response for one comment, including its author's email."""
    return CommentRead(
        id=comment.id,
        incidence_id=comment.incidence_id,
        author_id=comment.author_id,
        author_email=comment.author.email,
        body=comment.body,
        created_at=comment.created_at,
    )


def _incidence_read(incidence: Incidence) -> IncidenceRead:
    """Build the response for one incidence and its whole comment thread."""
    return IncidenceRead(
        id=incidence.id,
        unit_id=incidence.unit_id,
        unit_identifier=incidence.unit.identifier,
        created_by_id=incidence.created_by_id,
        created_by_email=incidence.created_by.email,
        title=incidence.title,
        description=incidence.description,
        status=incidence.status,
        created_at=incidence.created_at,
        comments=[_comment_read(comment) for comment in incidence.comments],
    )


def _scope_statement(statement, session: Session, user: User):
    """Restrict an incidence query to the rows ``user`` may read.

    Residents see incidences they raised; managers see incidences for the units
    in the communities they manage; administrators see everything. The manager
    rule uses a correlated ``EXISTS`` so it cannot collide with the join any
    later filter adds.
    """
    if user.role is UserRole.RESIDENT:
        return statement.where(Incidence.created_by_id == user.id)
    allowed = access.readable_community_ids(session, user)
    if allowed is None:
        return statement
    return statement.where(
        Incidence.unit.has(Unit.building.has(Building.community_id.in_(allowed or [])))
    )


@router.get("/incidences", response_model=list[IncidenceRead])
def list_incidences(
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
    unit_id: Annotated[int | None, Query()] = None,
    incidence_status: Annotated[IncidenceStatus | None, Query(alias="status")] = None,
) -> list[IncidenceRead]:
    """List incidences visible to the caller, optionally filtered."""
    statement = (
        select(Incidence)
        .options(
            selectinload(Incidence.unit),
            selectinload(Incidence.created_by),
            selectinload(Incidence.comments).selectinload(Comment.author),
        )
        .order_by(Incidence.id)
    )
    statement = _scope_statement(statement, session, user)
    if unit_id is not None:
        statement = statement.where(Incidence.unit_id == unit_id)
    if incidence_status is not None:
        statement = statement.where(Incidence.status == incidence_status)
    return [_incidence_read(row) for row in session.scalars(statement).unique().all()]


@router.post("/incidences", response_model=IncidenceRead, status_code=status.HTTP_201_CREATED)
def create_incidence(
    payload: IncidenceCreate,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> IncidenceRead:
    """Report an incidence against one of the caller's own units.

    Managers and administrators may also raise one (for a unit in their scope)
    so staff can log issues they notice while inspecting a property.
    """
    unit = session.get(Unit, payload.unit_id)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    if not access.can_comment_on_unit(session, user, unit):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")

    incidence = Incidence(
        unit_id=unit.id,
        created_by_id=user.id,
        title=payload.title,
        description=payload.description,
        status=IncidenceStatus.SUBMITTED,
    )
    session.add(incidence)
    session.commit()
    return _incidence_read(_load_incidence(session, incidence.id))


@router.get("/incidences/{incidence_id}", response_model=IncidenceRead)
def read_incidence(
    incidence_id: int,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> IncidenceRead:
    """Return one incidence and its comment thread, if the caller may read it."""
    incidence = _load_incidence(session, incidence_id)
    if user.role is UserRole.RESIDENT:
        allowed = incidence.created_by_id == user.id
    else:
        allowed = access.can_write_unit(session, user, incidence.unit)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidence not found")
    return _incidence_read(incidence)


@router.patch("/incidences/{incidence_id}/status", response_model=IncidenceRead)
def update_incidence_status(
    incidence_id: int,
    payload: IncidenceStatusUpdate,
    manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
) -> IncidenceRead:
    """Advance an incidence one step along its lifecycle. Manager action.

    Only the immediate next stage is accepted (``submitted -> in progress``,
    ``in progress -> resolved``, ``resolved -> closed``); anything else,
    including moving backwards or touching a closed incidence, returns 409
    with the allowed next stage in the detail.
    """
    incidence = _load_incidence(session, incidence_id)
    if not access.can_write_unit(session, manager, incidence.unit):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if not incidence.can_transition_to(payload.status):
        allowed = sorted(stage.value for stage in INCIDENCE_TRANSITIONS[incidence.status])
        detail = (
            "Cannot transition from "
            f"'{incidence.status.value}' to '{payload.status.value}'; "
            + (f"allowed: {', '.join(allowed)}" if allowed else "this incidence is closed")
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    incidence.status = payload.status
    session.commit()
    return _incidence_read(_load_incidence(session, incidence.id))


@router.get("/incidences/{incidence_id}/comments", response_model=list[CommentRead])
def list_comments(
    incidence_id: int,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[CommentRead]:
    """Return the comment thread of an incidence the caller may read."""
    incidence = _load_incidence(session, incidence_id)
    if user.role is UserRole.RESIDENT:
        allowed = incidence.created_by_id == user.id
    else:
        allowed = access.can_write_unit(session, user, incidence.unit)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidence not found")
    return [_comment_read(comment) for comment in incidence.comments]


@router.post(
    "/incidences/{incidence_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    incidence_id: int,
    payload: CommentCreate,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> CommentRead:
    """Add a comment to an incidence thread.

    A resident may comment on their own incidence; a manager may comment on
    incidences for the units they manage. Comments stay open even after the
    incidence is closed, so a final note can be recorded.
    """
    incidence = session.get(Incidence, incidence_id)
    if incidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidence not found")
    if user.role is UserRole.RESIDENT:
        allowed = incidence.created_by_id == user.id
    else:
        allowed = access.can_write_unit(session, user, incidence.unit)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidence not found")

    comment = Comment(incidence_id=incidence.id, author_id=user.id, body=payload.body)
    session.add(comment)
    session.commit()
    session.refresh(comment)
    comment.author = user
    return _comment_read(comment)
