"""Administrator user-management endpoints (backlog task 9).

Administrators are the only role that can create and edit accounts, including
assigning the manager role and activating or deactivating an account. Every
response uses :class:`~app.schemas.auth.UserRead`, which excludes the password
hash, so a hash can never leak through the API.

Deactivation is preferred over deletion because a deactivated account keeps
its unit assignments, bills, and audit history intact while immediately
failing authentication.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas import UserCreate, UserRead, UserUpdate
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])

AdminUser = Annotated[User, Depends(require_role(UserRole.ADMINISTRATOR))]


def _load_user(session: Session, user_id: int) -> User:
    """Return one user by id or raise 404."""
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("", response_model=list[UserRead])
def list_users(
    _admin: AdminUser,
    session: Annotated[Session, Depends(get_db)],
    role: Annotated[UserRole | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> list[User]:
    """List accounts, optionally filtered by role or activation state."""
    statement = select(User).order_by(User.email)
    if role is not None:
        statement = statement.where(User.role == role)
    if is_active is not None:
        statement = statement.where(User.is_active == is_active)
    return list(session.scalars(statement).all())


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    _admin: AdminUser,
    session: Annotated[Session, Depends(get_db)],
) -> User:
    """Create an account. Returns 409 when the email is already registered."""
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that email already exists",
        ) from exc
    session.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    _admin: AdminUser,
    session: Annotated[Session, Depends(get_db)],
) -> User:
    """Return one account."""
    return _load_user(session, user_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    admin: AdminUser,
    session: Annotated[Session, Depends(get_db)],
) -> User:
    """Change a user's role, activation state, or password.

    An administrator cannot deactivate or demote their own account: doing so
    would lock the firm out of user management with no way back in.
    """
    user = _load_user(session, user_id)
    if user.id == admin.id:
        if payload.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Administrators cannot deactivate their own account",
            )
        if payload.role is not None and payload.role is not UserRole.ADMINISTRATOR:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Administrators cannot change their own role",
            )

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)

    session.commit()
    session.refresh(user)
    return user
