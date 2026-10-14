"""Incidence and comment schemas (backlog task 11)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models import IncidenceStatus


class CommentCreate(BaseModel):
    """Request body for ``POST /incidences/{id}/comments``."""

    body: str = Field(min_length=1, max_length=4000)


class CommentRead(BaseModel):
    """Public representation of one comment in a thread."""

    id: int
    incidence_id: int
    author_id: int
    author_email: str
    body: str
    created_at: datetime


class IncidenceCreate(BaseModel):
    """Request body for ``POST /incidences`` (residents only).

    The unit must be one of the caller's own units, so only ``unit_id`` is
    needed; the reporter is the signed-in user.
    """

    unit_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)


class IncidenceStatusUpdate(BaseModel):
    """Request body for ``PATCH /incidences/{id}/status`` (managers only)."""

    status: IncidenceStatus


class IncidenceRead(BaseModel):
    """Public representation of an incidence.

    ``comments`` is included so a detail response carries the whole thread;
    the list endpoint returns the same shape with the comment list populated,
    which keeps the frontend on one type.
    """

    id: int
    unit_id: int
    unit_identifier: str
    created_by_id: int
    created_by_email: str
    title: str
    description: str
    status: IncidenceStatus
    created_at: datetime
    comments: list[CommentRead] = Field(default_factory=list)
