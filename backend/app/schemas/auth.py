"""Authentication and user schemas (backlog tasks 6 and 9).

``UserRead`` is the public shape of a user and never carries the password
hash; ``UserCreate`` and ``UserUpdate`` are the administrator request bodies
that do accept a password.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

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
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: UserRole
    is_active: bool


class UserCreate(BaseModel):
    """Request body for ``POST /users`` (administrator only).

    Validation is intentionally narrow: a non-empty email, a password of at
    least eight characters, and one of the three roles. The concrete email
    format is the administrator's responsibility because the platform is
    deployed inside a firm that seeds accounts from its own directory.
    """

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.RESIDENT


class UserUpdate(BaseModel):
    """Request body for ``PATCH /users/{id}`` (administrator only).

    Every field is optional so a patch can change only the role, only the
    activation flag, or only the password. ``None`` means "leave unchanged".
    """

    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
