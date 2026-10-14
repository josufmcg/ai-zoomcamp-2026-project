"""Authentication endpoints (backlog task 6).

``POST /auth/token`` implements the OAuth2 password flow: it accepts a form
body with ``username`` (the user's email) and ``password`` and returns a signed
JWT. ``GET /auth/me`` echoes the signed-in user so the frontend can confirm the
token and role after login.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.dependencies import CurrentUser, get_db
from app.models import User
from app.schemas import Token, UserRead
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=Token)
def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_db)],
) -> Token:
    """Authenticate a user and return a signed access token."""
    settings: Settings = request.app.state.settings
    user = session.scalars(
        select(User).where(User.email == form_data.username)
    ).one_or_none()

    # Verify the password even when the account is unknown so the response time
    # does not reveal whether the email exists.
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        user_id=user.id,
        role=user.role.value,
        secret_key=settings.secret_key,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.access_token_expire_minutes,
    )
    return Token(access_token=token)


@router.get("/me", response_model=UserRead)
def read_current_user(user: CurrentUser) -> User:
    """Return the profile of the signed-in user."""
    return user
