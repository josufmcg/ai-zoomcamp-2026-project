"""Initiative and voting endpoints (backlog task 12).

Managers create an initiative with two or more options and an eligible scope
expressed as a filter over communities, buildings, unit types, and tags.
Residents cast **one ballot per eligible unit they hold**: owning three
eligible units means three independent ballots, and the unique constraint on
``(initiative_id, unit_id)`` rejects a second ballot for the same unit. Ballots
are rejected after the close date, and the results endpoint aggregates the
ballot count per option.

The scope is stored as JSON on the initiative. :func:`eligible_unit_ids`
translates that JSON into one query, and every rule that needs to know what a
resident may vote with goes through it.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.dependencies import CurrentUser, get_db, require_role
from app.models import (
    Building,
    Initiative,
    InitiativeOption,
    Tag,
    Unit,
    UnitAssignment,
    UnitType,
    User,
    UserRole,
    Vote,
)
from app.schemas import (
    EligibleUnitRead,
    InitiativeCreate,
    InitiativeOptionRead,
    InitiativeRead,
    VoteCast,
    VoteRead,
    VoteResult,
    VoteTally,
)

router = APIRouter(tags=["initiatives"])

ManagerUser = Annotated[User, Depends(require_role(UserRole.MANAGER, UserRole.ADMINISTRATOR))]
ResidentUser = Annotated[User, Depends(require_role(UserRole.RESIDENT))]


def eligible_unit_ids(session: Session, scope: dict[str, list[str]]) -> set[int]:
    """Return the ids of every unit matching an initiative's scope.

    An empty scope means "every unit". The filters combine with AND, so a unit
    is eligible only when it satisfies each filter that is present.
    """
    statement = select(Unit.id)
    if scope.get("community_ids"):
        statement = statement.join(Building).where(
            Building.community_id.in_(scope["community_ids"])
        )
    if scope.get("building_ids"):
        statement = statement.where(Unit.building_id.in_(scope["building_ids"]))
    if scope.get("unit_types"):
        statement = statement.where(
            Unit.unit_type.in_([UnitType(value) for value in scope["unit_types"]])
        )
    if scope.get("tag_ids"):
        statement = statement.where(Unit.tags.any(Tag.id.in_(scope["tag_ids"])))
    return set(session.scalars(statement).all())


def resident_eligible_unit_ids(
    session: Session, user_id: int, scope: dict[str, list[str]]
) -> set[int]:
    """Return the ids of ``user_id``'s units that fall inside ``scope``."""
    own_units = set(
        session.scalars(
            select(UnitAssignment.unit_id).where(UnitAssignment.user_id == user_id)
        ).all()
    )
    return own_units & eligible_unit_ids(session, scope)


def _load_initiative(session: Session, initiative_id: int) -> Initiative:
    """Return one initiative with its options and votes loaded, or raise 404."""
    initiative = session.scalars(
        select(Initiative)
        .where(Initiative.id == initiative_id)
        .options(
            selectinload(Initiative.options),
            selectinload(Initiative.votes),
        )
    ).one_or_none()
    if initiative is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found")
    return initiative


def _ballot_counts(session: Session, initiative_id: int) -> dict[int, int]:
    """Return the number of ballots cast for each option of an initiative."""
    rows = session.execute(
        select(Vote.option_id, func.count())
        .where(Vote.initiative_id == initiative_id)
        .group_by(Vote.option_id)
    ).all()
    return dict(rows)


def _initiative_read(session: Session, initiative: Initiative) -> InitiativeRead:
    """Build the response for one initiative, including ballot counts."""
    counts = _ballot_counts(session, initiative.id)
    return InitiativeRead(
        id=initiative.id,
        title=initiative.title,
        description=initiative.description,
        opens_at=initiative.opens_at,
        closes_at=initiative.closes_at,
        is_open=initiative.is_open_on(date.today()),
        scope=initiative.scope,
        created_by_id=initiative.created_by_id,
        options=[
            InitiativeOptionRead(
                id=option.id,
                label=option.label,
                position=option.position,
                votes=counts.get(option.id, 0),
            )
            for option in initiative.options
        ],
    )


@router.get("/initiatives", response_model=list[InitiativeRead])
def list_initiatives(
    _user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
    is_open: Annotated[bool | None, Query()] = None,
) -> list[InitiativeRead]:
    """List initiatives, optionally limited to the ones open today.

    Any signed-in user may list initiatives; ``?is_open=true`` is what the
    resident screens use to show only the votes that are currently running.
    """
    statement = (
        select(Initiative)
        .options(
            selectinload(Initiative.options),
            selectinload(Initiative.votes),
        )
        .order_by(Initiative.id)
    )
    today = date.today()
    if is_open is True:
        statement = statement.where(Initiative.opens_at <= today, Initiative.closes_at >= today)
    elif is_open is False:
        statement = statement.where((Initiative.closes_at < today) | (Initiative.opens_at > today))
    return [_initiative_read(session, row) for row in session.scalars(statement).all()]


@router.post("/initiatives", response_model=InitiativeRead, status_code=status.HTTP_201_CREATED)
def create_initiative(
    payload: InitiativeCreate,
    manager: ManagerUser,
    session: Annotated[Session, Depends(get_db)],
) -> InitiativeRead:
    """Create an initiative with its options and eligible scope. Manager only."""
    initiative = Initiative(
        created_by_id=manager.id,
        title=payload.title,
        description=payload.description,
        opens_at=payload.opens_at,
        closes_at=payload.closes_at,
        scope=payload.scope.as_filter(),
        options=[
            InitiativeOption(label=option.label, position=position)
            for position, option in enumerate(payload.options)
        ],
    )
    session.add(initiative)
    session.commit()
    return _initiative_read(session, _load_initiative(session, initiative.id))


@router.get("/initiatives/{initiative_id}", response_model=InitiativeRead)
def read_initiative(
    initiative_id: int,
    _user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> InitiativeRead:
    """Return one initiative with its options and running ballot counts."""
    return _initiative_read(session, _load_initiative(session, initiative_id))


@router.get(
    "/initiatives/{initiative_id}/eligible-units",
    response_model=list[EligibleUnitRead],
)
def list_eligible_units(
    initiative_id: int,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[EligibleUnitRead]:
    """Return the caller's units that may vote, and any ballot already cast.

    This is what the resident voting form is built from: one row per unit the
    user holds inside the scope, with the chosen option when a ballot exists so
    the form can show it as already voted instead of offering a second ballot.
    """
    initiative = _load_initiative(session, initiative_id)
    candidate_ids = resident_eligible_unit_ids(session, user.id, initiative.scope)
    if not candidate_ids:
        return []

    votes = {
        vote.unit_id: vote
        for vote in session.scalars(
            select(Vote).where(
                Vote.initiative_id == initiative.id,
                Vote.unit_id.in_(candidate_ids),
            )
        ).all()
    }
    units = session.scalars(
        select(Unit).where(Unit.id.in_(candidate_ids)).order_by(Unit.identifier)
    ).all()
    return [
        EligibleUnitRead(
            unit_id=unit.id,
            unit_identifier=unit.identifier,
            unit_type=unit.unit_type,
            vote_id=votes[unit.id].id if unit.id in votes else None,
            option_id=votes[unit.id].option_id if unit.id in votes else None,
        )
        for unit in units
    ]


@router.post(
    "/initiatives/{initiative_id}/votes",
    response_model=VoteRead,
    status_code=status.HTTP_201_CREATED,
)
def cast_vote(
    initiative_id: int,
    payload: VoteCast,
    resident: ResidentUser,
    session: Annotated[Session, Depends(get_db)],
) -> VoteRead:
    """Cast one ballot for one eligible unit. Residents only.

    Returns 409 when the initiative is not open, when the unit is outside the
    scope, or when that unit has already voted; 404 when the initiative or
    option does not exist (including an option from a different initiative).
    """
    initiative = _load_initiative(session, initiative_id)
    if not initiative.is_open_on(date.today()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Initiative is not open for voting",
        )

    option = session.get(InitiativeOption, payload.option_id)
    if option is None or option.initiative_id != initiative.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")

    eligible = resident_eligible_unit_ids(session, resident.id, initiative.scope)
    if payload.unit_id not in eligible:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unit is not eligible for this initiative",
        )

    vote = Vote(
        initiative_id=initiative.id,
        option_id=option.id,
        unit_id=payload.unit_id,
        voter_id=resident.id,
    )
    session.add(vote)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unit has already voted in this initiative",
        ) from exc
    session.refresh(vote)

    unit = session.get(Unit, vote.unit_id)
    return VoteRead(
        id=vote.id,
        initiative_id=vote.initiative_id,
        option_id=vote.option_id,
        option_label=option.label,
        unit_id=vote.unit_id,
        unit_identifier=unit.identifier if unit else "",
    )


@router.get("/initiatives/{initiative_id}/results", response_model=VoteResult)
def read_results(
    initiative_id: int,
    _user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> VoteResult:
    """Aggregate ballots per option for one initiative."""
    initiative = _load_initiative(session, initiative_id)
    counts = _ballot_counts(session, initiative.id)
    return VoteResult(
        initiative_id=initiative.id,
        total_votes=sum(counts.values()),
        tallies=[
            VoteTally(
                option_id=option.id,
                label=option.label,
                votes=counts.get(option.id, 0),
            )
            for option in initiative.options
        ],
    )
