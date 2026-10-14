"""Pydantic schemas for authentication and users (backlog task 6)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models import UserRole


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
