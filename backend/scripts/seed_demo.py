"""Idempotent demo seed for EFINGES (backlog task 23).

Creates a complete, explorable scenario so a reviewer can log in and click
through the product immediately after ``make up``: one administrator, one
manager, three residents, a community with two buildings and apartments,
garages, and storage units, tags, resident assignments, bills in all three
display statuses, one incidence per lifecycle stage with comment threads, and
one open initiative with a few ballots already cast.

The script is **idempotent**: every row is looked up by a stable natural key
(email, name, identifier, title, description) before it is created, so running
it twice creates nothing the second time. Run it again after changing an
environment or to top up a database that lost a row, without duplicating data.

Run it with the stack up (or against a local SQLite file):

    make seed

    # or directly, overriding the database:
    cd backend && uv run python -m scripts.seed_demo --database-url postgresql+psycopg://.../db

``--reset`` removes only the demo rows (matched by the same natural keys) before
seeding, so the demo can be restored to its initial state without touching any
other data.

Every account shares the password :data:`DEMO_PASSWORD`, so the printed
credentials are enough to sign in as each role.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import Database
from app.models import (
    Bill,
    BillStatus,
    Building,
    Comment,
    Community,
    Incidence,
    IncidenceStatus,
    Initiative,
    InitiativeOption,
    ManagerAssignment,
    OwnershipType,
    Tag,
    Unit,
    UnitAssignment,
    UnitType,
    User,
    UserRole,
    Vote,
    building_tags,
    unit_tags,
)
from app.security import hash_password

# The password every demo account shares. Long enough for ``UserCreate`` and
# easy to type at a demo.
DEMO_PASSWORD = "efinges-demo-123"

ADMIN_EMAIL = "admin@efinges.demo"
MANAGER_EMAIL = "manager@efinges.demo"
RESIDENT_EMAILS = (
    "alice@efinges.demo",
    "bob@efinges.demo",
    "carol@efinges.demo",
)

COMMUNITY_NAME = "Demo Riverside"
BUILDING_A = "Block A"
BUILDING_B = "Block B"

# Tags group buildings and units; the initiative below reuses one of them.
TAG_DOWNTOWN = "Downtown"
TAG_SEA_VIEW = "Sea view"
TAG_EV_CHARGING = "EV charging"
TAG_QUIET = "Quiet"

# Units are looked up by (building, identifier); the unit type is part of the
# demo so apartments, garages, and storage rooms all appear.
UNITS: tuple[tuple[str, str, UnitType], ...] = (
    (BUILDING_A, "A-101", UnitType.APARTMENT),
    (BUILDING_A, "A-102", UnitType.APARTMENT),
    (BUILDING_A, "G-01", UnitType.GARAGE),
    (BUILDING_A, "S-01", UnitType.STORAGE),
    (BUILDING_B, "B-201", UnitType.APARTMENT),
    (BUILDING_B, "B-202", UnitType.APARTMENT),
    (BUILDING_B, "G-02", UnitType.GARAGE),
    (BUILDING_B, "S-02", UnitType.STORAGE),
)

# Resident -> the units they hold, with the ownership flag. A resident holds
# several units, which is what makes one-ballot-per-unit voting interesting.
ASSIGNMENTS: tuple[tuple[str, str, OwnershipType], ...] = (
    (RESIDENT_EMAILS[0], "A-101", OwnershipType.OWNER),
    (RESIDENT_EMAILS[0], "G-01", OwnershipType.OWNER),
    (RESIDENT_EMAILS[1], "A-102", OwnershipType.TENANT),
    (RESIDENT_EMAILS[1], "S-01", OwnershipType.TENANT),
    (RESIDENT_EMAILS[1], "G-02", OwnershipType.OWNER),
    (RESIDENT_EMAILS[2], "B-201", OwnershipType.OWNER),
    (RESIDENT_EMAILS[2], "B-202", OwnershipType.TENANT),
)

# Bills cover all three display statuses. Only ``pending`` and ``paid`` are
# stored; ``overdue`` is computed from a past due date, so the overdue demo row
# is stored as pending with ``status`` left unset.
INITIATIVE_TITLE = "Install EV chargers in the garages"

COMMENTS_PER_INCIDENCE = 2


@dataclass
class SeedSummary:
    """Tracks how many rows were created versus reused, for the CLI output."""

    created: dict[str, int] = field(default_factory=dict)
    reused: dict[str, int] = field(default_factory=dict)

    def record(self, kind: str, *, created: bool) -> None:
        """Count one row under ``kind`` as newly created or reused."""
        bucket = self.created if created else self.reused
        bucket[kind] = bucket.get(kind, 0) + 1

    def total_created(self) -> int:
        """Return the number of rows this run created."""
        return sum(self.created.values())

    def lines(self) -> list[str]:
        """Return a stable, human-readable report of what this run did."""
        kinds = sorted(set(self.created) | set(self.reused))
        return [
            f"  {kind}: {self.created.get(kind, 0)} created, {self.reused.get(kind, 0)} reused"
            for kind in kinds
        ]


def _lookup(session: Session, model, **filters) -> object | None:
    """Return the single row matching ``filters``, or None."""
    return session.scalars(select(model).filter_by(**filters)).one_or_none()


def _user(
    session: Session,
    summary: SeedSummary,
    *,
    email: str,
    role: UserRole,
) -> User:
    """Return the account with ``email``, creating it when missing."""
    existing = session.scalars(select(User).where(User.email == email)).one_or_none()
    if existing is not None:
        summary.record("users", created=False)
        return existing
    user = User(
        email=email,
        hashed_password=hash_password(DEMO_PASSWORD),
        role=role,
        is_active=True,
    )
    session.add(user)
    session.flush()
    summary.record("users", created=True)
    return user


def _tag(session: Session, summary: SeedSummary, name: str) -> Tag:
    """Return the tag named ``name``, creating it when missing."""
    existing = session.scalars(select(Tag).where(Tag.name == name)).one_or_none()
    if existing is not None:
        summary.record("tags", created=False)
        return existing
    tag = Tag(name=name)
    session.add(tag)
    session.flush()
    summary.record("tags", created=True)
    return tag


def _attach_tags(holder, tags: Sequence[Tag]) -> None:
    """Attach ``tags`` to a building or unit, keeping any already present."""
    for tag in tags:
        if tag not in holder.tags:
            holder.tags.append(tag)


def _community(session: Session, summary: SeedSummary) -> Community:
    """Return the demo community, creating it when missing."""
    existing = session.scalars(
        select(Community).where(Community.name == COMMUNITY_NAME)
    ).one_or_none()
    if existing is not None:
        summary.record("communities", created=False)
        return existing
    community = Community(name=COMMUNITY_NAME)
    session.add(community)
    session.flush()
    summary.record("communities", created=True)
    return community


def _building(
    session: Session,
    summary: SeedSummary,
    *,
    community: Community,
    name: str,
) -> Building:
    """Return a building in ``community``, creating it when missing."""
    existing = session.scalars(
        select(Building).where(Building.community_id == community.id, Building.name == name)
    ).one_or_none()
    if existing is not None:
        summary.record("buildings", created=False)
        return existing
    building = Building(community_id=community.id, name=name)
    session.add(building)
    session.flush()
    summary.record("buildings", created=True)
    return building


def _unit(
    session: Session,
    summary: SeedSummary,
    *,
    building: Building,
    identifier: str,
    unit_type: UnitType,
) -> Unit:
    """Return a unit in ``building``, creating it when missing."""
    existing = session.scalars(
        select(Unit).where(Unit.building_id == building.id, Unit.identifier == identifier)
    ).one_or_none()
    if existing is not None:
        summary.record("units", created=False)
        return existing
    unit = Unit(building_id=building.id, identifier=identifier, unit_type=unit_type)
    session.add(unit)
    session.flush()
    summary.record("units", created=True)
    return unit


def _manager_assignment(
    session: Session,
    summary: SeedSummary,
    *,
    manager: User,
    community: Community,
) -> None:
    """Give the demo manager write access to the demo community."""
    existing = session.scalars(
        select(ManagerAssignment).where(
            ManagerAssignment.manager_id == manager.id,
            ManagerAssignment.community_id == community.id,
        )
    ).one_or_none()
    if existing is not None:
        summary.record("manager assignments", created=False)
        return
    session.add(ManagerAssignment(manager_id=manager.id, community_id=community.id))
    session.flush()
    summary.record("manager assignments", created=True)


def _assignment(
    session: Session,
    summary: SeedSummary,
    *,
    user: User,
    unit: Unit,
    ownership_type: OwnershipType,
) -> None:
    """Assign a resident to a unit unless that unit is already assigned."""
    existing = session.scalars(
        select(UnitAssignment).where(UnitAssignment.unit_id == unit.id)
    ).one_or_none()
    if existing is not None:
        summary.record("unit assignments", created=False)
        return
    session.add(UnitAssignment(user_id=user.id, unit_id=unit.id, ownership_type=ownership_type))
    session.flush()
    summary.record("unit assignments", created=True)


def _bill(
    session: Session,
    summary: SeedSummary,
    *,
    unit: Unit,
    amount: str,
    description: str,
    issue_date: date,
    due_date: date,
    status: BillStatus = BillStatus.PENDING,
) -> Bill:
    """Create a bill for ``unit`` unless one with the same description exists."""
    existing = session.scalars(
        select(Bill).where(Bill.unit_id == unit.id, Bill.description == description)
    ).one_or_none()
    if existing is not None:
        summary.record("bills", created=False)
        return existing
    bill = Bill(
        unit_id=unit.id,
        amount=Decimal(amount),
        description=description,
        issue_date=issue_date,
        due_date=due_date,
        status=status,
    )
    session.add(bill)
    session.flush()
    summary.record("bills", created=True)
    return bill


def _incidence(
    session: Session,
    summary: SeedSummary,
    *,
    unit: Unit,
    author: User,
    title: str,
    description: str,
    status: IncidenceStatus,
    comments: Sequence[tuple[User, str]],
) -> Incidence:
    """Create an incidence and its comments, unless the title already exists."""
    existing = session.scalars(
        select(Incidence).where(Incidence.unit_id == unit.id, Incidence.title == title)
    ).one_or_none()
    if existing is not None:
        summary.record("incidences", created=False)
        for _ in comments:
            summary.record("comments", created=False)
        return existing
    incidence = Incidence(
        unit_id=unit.id,
        created_by_id=author.id,
        title=title,
        description=description,
        status=status,
    )
    session.add(incidence)
    session.flush()
    summary.record("incidences", created=True)
    for comment_author, body in comments:
        session.add(Comment(incidence_id=incidence.id, author_id=comment_author.id, body=body))
        summary.record("comments", created=True)
    return incidence


def _reset_demo(session: Session) -> None:
    """Delete every demo row, matched by its natural key, then flush.

    Only rows the seed owns are removed: accounts by email, the community by
    name, the initiative by title, and the children that hang off them. Rows
    created by hand (a different community, a different account) are left
    untouched.
    """
    user_ids = list(
        session.scalars(
            select(User.id).where(User.email.in_((ADMIN_EMAIL, MANAGER_EMAIL, *RESIDENT_EMAILS)))
        ).all()
    )
    community_ids = list(
        session.scalars(select(Community.id).where(Community.name == COMMUNITY_NAME)).all()
    )
    building_ids = list(
        session.scalars(select(Building.id).where(Building.community_id.in_(community_ids))).all()
    )
    unit_ids = list(
        session.scalars(select(Unit.id).where(Unit.building_id.in_(building_ids))).all()
    )
    initiative_ids = list(
        session.scalars(select(Initiative.id).where(Initiative.title == INITIATIVE_TITLE)).all()
    )
    incidence_ids = list(
        session.scalars(
            select(Incidence.id).where(
                Incidence.unit_id.in_(unit_ids) | Incidence.created_by_id.in_(user_ids)
            )
        ).all()
    )

    # Children before parents, and every level explicitly: SQLite does not
    # enforce ``ON DELETE CASCADE`` unless foreign keys are switched on, so the
    # reset must not rely on the database to clean up after a parent delete.
    if initiative_ids or unit_ids or user_ids:
        session.execute(
            delete(Vote).where(
                Vote.initiative_id.in_(initiative_ids)
                | Vote.unit_id.in_(unit_ids)
                | Vote.voter_id.in_(user_ids)
            )
        )
    if initiative_ids:
        session.execute(
            delete(InitiativeOption).where(InitiativeOption.initiative_id.in_(initiative_ids))
        )
        session.execute(delete(Initiative).where(Initiative.id.in_(initiative_ids)))
    if incidence_ids or user_ids:
        session.execute(
            delete(Comment).where(
                Comment.incidence_id.in_(incidence_ids) | Comment.author_id.in_(user_ids)
            )
        )
        session.execute(delete(Incidence).where(Incidence.id.in_(incidence_ids)))
    if unit_ids:
        session.execute(delete(Bill).where(Bill.unit_id.in_(unit_ids)))
        session.execute(
            delete(UnitAssignment).where(
                UnitAssignment.unit_id.in_(unit_ids) | UnitAssignment.user_id.in_(user_ids)
            )
        )
        session.execute(unit_tags.delete().where(unit_tags.c.unit_id.in_(unit_ids)))
    if building_ids:
        session.execute(building_tags.delete().where(building_tags.c.building_id.in_(building_ids)))
        session.execute(delete(Unit).where(Unit.building_id.in_(building_ids)))
        session.execute(delete(Building).where(Building.id.in_(building_ids)))
    if community_ids:
        session.execute(
            delete(ManagerAssignment).where(
                ManagerAssignment.community_id.in_(community_ids)
                | ManagerAssignment.manager_id.in_(user_ids)
            )
        )
        session.execute(delete(Community).where(Community.id.in_(community_ids)))
    if user_ids:
        session.execute(delete(User).where(User.id.in_(user_ids)))
    session.flush()


def run(database: Database, *, reset: bool = False) -> SeedSummary:
    """Seed the demo data through ``database`` and return what it created.

    The whole seed runs in one transaction and commits once, so a failure
    halfway through leaves the database exactly as it was.
    """
    summary = SeedSummary()
    today = date.today()

    with database.session() as session:
        if reset:
            _reset_demo(session)

        admin = _user(session, summary, email=ADMIN_EMAIL, role=UserRole.ADMINISTRATOR)
        manager = _user(session, summary, email=MANAGER_EMAIL, role=UserRole.MANAGER)
        residents = [
            _user(session, summary, email=email, role=UserRole.RESIDENT)
            for email in RESIDENT_EMAILS
        ]

        tags = {
            name: _tag(session, summary, name)
            for name in (TAG_DOWNTOWN, TAG_SEA_VIEW, TAG_EV_CHARGING, TAG_QUIET)
        }
        community = _community(session, summary)
        _manager_assignment(session, summary, manager=manager, community=community)

        building_a = _building(session, summary, community=community, name=BUILDING_A)
        building_b = _building(session, summary, community=community, name=BUILDING_B)
        buildings = {BUILDING_A: building_a, BUILDING_B: building_b}
        _attach_tags(building_a, [tags[TAG_DOWNTOWN], tags[TAG_QUIET]])
        _attach_tags(building_b, [tags[TAG_DOWNTOWN], tags[TAG_SEA_VIEW]])

        units: dict[str, Unit] = {}
        for building_name, identifier, unit_type in UNITS:
            unit = _unit(
                session,
                summary,
                building=buildings[building_name],
                identifier=identifier,
                unit_type=unit_type,
            )
            units[identifier] = unit
        # Garages are what the demo initiative targets, so tag them.
        for unit in units.values():
            if unit.unit_type is UnitType.GARAGE:
                _attach_tags(unit, [tags[TAG_EV_CHARGING]])

        users_by_email = {admin.email: admin, manager.email: manager}
        users_by_email.update({resident.email: resident for resident in residents})
        for email, identifier, ownership_type in ASSIGNMENTS:
            _assignment(
                session,
                summary,
                user=users_by_email[email],
                unit=units[identifier],
                ownership_type=ownership_type,
            )

        # Bills in all three display statuses: one pending, one paid, and one
        # pending-but-overdue (the stored status stays pending; the API computes
        # ``overdue`` from the past due date).
        _bill(
            session,
            summary,
            unit=units["A-101"],
            amount="120.50",
            description="Monthly community fee (pending)",
            issue_date=today - timedelta(days=2),
            due_date=today + timedelta(days=10),
        )
        _bill(
            session,
            summary,
            unit=units["G-01"],
            amount="45.00",
            description="Garage maintenance (paid)",
            issue_date=today - timedelta(days=20),
            due_date=today - timedelta(days=10),
            status=BillStatus.PAID,
        )
        _bill(
            session,
            summary,
            unit=units["A-102"],
            amount="120.50",
            description="Monthly community fee (overdue)",
            issue_date=today - timedelta(days=30),
            due_date=today - timedelta(days=10),
        )
        _bill(
            session,
            summary,
            unit=units["B-201"],
            amount="98.00",
            description="Monthly community fee (pending)",
            issue_date=today,
            due_date=today + timedelta(days=14),
        )

        # One incidence per lifecycle stage, each with a short two-message
        # thread so the resident and manager screens both have content.
        _incidence(
            session,
            summary,
            unit=units["A-101"],
            author=users_by_email[RESIDENT_EMAILS[0]],
            title="Kitchen sink is leaking",
            description="The tap under the sink drips constantly and the cabinet is damp.",
            status=IncidenceStatus.SUBMITTED,
            comments=[(users_by_email[RESIDENT_EMAILS[0]], "It started this morning.")],
        )
        _incidence(
            session,
            summary,
            unit=units["A-102"],
            author=users_by_email[RESIDENT_EMAILS[1]],
            title="Elevator is noisy at night",
            description="A loud grinding noise after 22:00, mostly between the 2nd and 3rd floor.",
            status=IncidenceStatus.IN_PROGRESS,
            comments=[
                (users_by_email[RESIDENT_EMAILS[1]], "It happened again last night."),
                (manager, "A technician is booked for Thursday; we will confirm by phone."),
            ],
        )
        _incidence(
            session,
            summary,
            unit=units["B-201"],
            author=users_by_email[RESIDENT_EMAILS[2]],
            title="Garage door remote does not work",
            description="The remote stopped opening the shared garage door after the last storm.",
            status=IncidenceStatus.RESOLVED,
            comments=[
                (users_by_email[RESIDENT_EMAILS[2]], "Replacing the battery did not help."),
                (manager, "We reprogrammed the remote at the entrance panel yesterday."),
            ],
        )
        _incidence(
            session,
            summary,
            unit=units["S-01"],
            author=users_by_email[RESIDENT_EMAILS[1]],
            title="Storage room light flickers",
            description="The ceiling light in storage room S-01 flickers and sometimes turns off.",
            status=IncidenceStatus.CLOSED,
            comments=[
                (users_by_email[RESIDENT_EMAILS[1]], "Sometimes it stays dark for minutes."),
                (manager, "The ballast was replaced; closing this as resolved."),
            ],
        )

        initiative = session.scalars(
            select(Initiative).where(Initiative.title == INITIATIVE_TITLE)
        ).one_or_none()
        if initiative is not None:
            summary.record("initiatives", created=False)
            options = list(
                session.scalars(
                    select(InitiativeOption)
                    .where(InitiativeOption.initiative_id == initiative.id)
                    .order_by(InitiativeOption.position)
                ).all()
            )
        else:
            # Open today, targeting every garage: the two garages are held by
            # different residents, which is what the per-unit ballots show.
            initiative = Initiative(
                created_by_id=manager.id,
                title=INITIATIVE_TITLE,
                description=(
                    "Should the firm install shared EV chargers in the garages of Demo Riverside?"
                ),
                opens_at=today - timedelta(days=5),
                closes_at=today + timedelta(days=7),
                scope={"unit_types": [UnitType.GARAGE.value]},
                options=[
                    InitiativeOption(label="Yes, install in all garages", position=0),
                    InitiativeOption(label="Only for owner-occupied units", position=1),
                    InitiativeOption(label="No, keep the garages as they are", position=2),
                ],
            )
            session.add(initiative)
            session.flush()
            summary.record("initiatives", created=True)
            options = list(initiative.options)

        # A few ballots already cast, one per eligible garage, so the results
        # endpoint has something to aggregate on first load.
        for identifier in ("G-01", "G-02"):
            unit = units[identifier]
            existing_vote = session.scalars(
                select(Vote).where(
                    Vote.initiative_id == initiative.id,
                    Vote.unit_id == unit.id,
                )
            ).one_or_none()
            if existing_vote is not None:
                summary.record("votes", created=False)
                continue
            assignment = session.scalars(
                select(UnitAssignment).where(UnitAssignment.unit_id == unit.id)
            ).one_or_none()
            if assignment is None:  # pragma: no cover - the seed assigns both garages
                continue
            session.add(
                Vote(
                    initiative_id=initiative.id,
                    option_id=options[0].id,
                    unit_id=unit.id,
                    voter_id=assignment.user_id,
                )
            )
            summary.record("votes", created=True)

        session.commit()

    return summary


def main(argv: Sequence[str] | None = None) -> None:
    """Seed the demo data against ``DATABASE_URL`` (or ``--database-url``)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database to seed; defaults to the DATABASE_URL setting.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the demo rows (matched by their natural keys) before seeding.",
    )
    args = parser.parse_args(argv)

    settings: Settings = get_settings()
    if args.database_url:
        settings = settings.model_copy(update={"database_url": args.database_url})

    database = Database(settings.database_url)
    try:
        # Create any missing tables so the script also works against a bare
        # SQLite file. Against PostgreSQL this is a no-op once the migrations
        # have run, which is what the compose backend does on startup.
        database.create_all()
        summary = run(database, reset=args.reset)
    finally:
        database.dispose()

    print(f"Demo seed complete against {settings.database_url}")
    print(f"  rows created this run: {summary.total_created()}")
    for line in summary.lines():
        print(line)
    print(f"Sign in with any of these accounts (password: {DEMO_PASSWORD}):")
    print(f"  administrator: {ADMIN_EMAIL}")
    print(f"  manager:       {MANAGER_EMAIL}")
    for email in RESIDENT_EMAILS:
        print(f"  resident:      {email}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
