"""Initiative and voting schemas (backlog task 12).

The eligible scope is a plain object with four optional keys; an absent key
means "no restriction" and an entirely empty object means "every unit". This
mirrors how the filter is stored on the model, so the same JSON round-trips
between the API and the database.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator

from app.models import UnitType


class InitiativeScope(BaseModel):
    """Eligibility filter over communities, buildings, unit types, and tags.

    All keys are optional and combine with AND: a unit is eligible when it
    matches every filter that is present.
    """

    community_ids: list[int] = Field(default_factory=list)
    building_ids: list[int] = Field(default_factory=list)
    unit_types: list[UnitType] = Field(default_factory=list)
    tag_ids: list[int] = Field(default_factory=list)

    def as_filter(self) -> dict[str, list[str]]:
        """Return the scope as a plain JSON dict, dropping empty keys.

        Uses ``mode="json"`` so the unit types come out as strings such as
        ``"garage"`` rather than enum members, which is exactly what the JSON
        column and the query helper expect.
        """
        payload = self.model_dump(mode="json", exclude_defaults=True)
        return {key: value for key, value in payload.items() if value}


class InitiativeOptionCreate(BaseModel):
    """One choice in the initiative request body."""

    label: str = Field(min_length=1, max_length=200)


class InitiativeCreate(BaseModel):
    """Request body for ``POST /initiatives`` (managers only).

    ``closes_at`` must not precede ``opens_at`` and there must be at least two
    distinct options, both enforced by the validator below so an invalid
    initiative can never be stored.
    """

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    opens_at: date
    closes_at: date
    options: list[InitiativeOptionCreate] = Field(min_length=2)
    scope: InitiativeScope = Field(default_factory=InitiativeScope)

    @model_validator(mode="after")
    def _check_dates_and_options(self) -> InitiativeCreate:
        if self.closes_at < self.opens_at:
            raise ValueError("closes_at must not be before opens_at")
        labels = [option.label.strip().lower() for option in self.options]
        if len(set(labels)) != len(labels):
            raise ValueError("option labels must be unique")
        return self


class InitiativeOptionRead(BaseModel):
    """Public representation of one choice, with its running ballot count."""

    id: int
    label: str
    position: int
    votes: int = 0


class InitiativeRead(BaseModel):
    """Public representation of an initiative, with options and ballot counts.

    ``is_open`` is computed against the request's "today" so the frontend can
    disable the voting form without duplicating the date rule; ``scope`` is
    echoed back so the manager screens can render the eligibility filter.
    """

    id: int
    title: str
    description: str
    opens_at: date
    closes_at: date
    is_open: bool
    scope: InitiativeScope
    created_by_id: int
    options: list[InitiativeOptionRead] = Field(default_factory=list)


class VoteCast(BaseModel):
    """Request body for ``POST /initiatives/{id}/votes`` (residents only).

    One ballot covers one of the caller's eligible units, so both the unit and
    the chosen option are required.
    """

    unit_id: int
    option_id: int


class EligibleUnitRead(BaseModel):
    """One of the caller's units that may vote in an initiative.

    ``option_id`` is ``None`` (with ``vote_id`` ``None``) until the unit votes,
    so the resident form can render both "cast a ballot here" and "you chose
    X" from a single list.
    """

    unit_id: int
    unit_identifier: str
    unit_type: UnitType
    vote_id: int | None = None
    option_id: int | None = None


class VoteRead(BaseModel):
    """Public representation of one cast ballot."""

    id: int
    initiative_id: int
    option_id: int
    option_label: str
    unit_id: int
    unit_identifier: str


class VoteTally(BaseModel):
    """Ballot count for one option in an aggregation response."""

    option_id: int
    label: str
    votes: int


class VoteResult(BaseModel):
    """Aggregation response for ``GET /initiatives/{id}/results``.

    ``total_votes`` is the number of eligible unit ballots cast, and
    ``tallies`` reports the count per option in the manager's ordering.
    """

    initiative_id: int
    total_votes: int
    tallies: list[VoteTally] = Field(default_factory=list)
