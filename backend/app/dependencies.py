"""FastAPI dependencies for authentication and role enforcement (task 6).

:func:`get_current_user` resolves the signed-in user from the ``Authorization:
Bearer <token>`` header. It returns 401 when the header is missing, the token
is invalid or expired, the token identifies no user, or the account is
deactivated.

:func:`require_role` builds a dependency that additionally enforces one of the
three roles, returning 403 when the signed-in user has an insufficient role.
Role checks always happen server-side; the frontend is never trusted to hide
access.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Database
from app.models import User, UserRole
from app.security import JWT_ERRORS, decode_access_token

# ``tokenUrl`` points at the login endpoint so the Swagger UI can obtain a
# token. ``auto_error=True`` makes a missing header return 401 automatically.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def _invalid_credentials() -> HTTPException:
    """Return a fresh 401 so every failure looks identical to the caller.

    The same message is used for a bad password, an unknown account, an invalid
    token, and a deactivated user, so attackers cannot tell them apart.
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_db(request: Request) -> Session:
    """Yield a request-scoped database session, closing it afterwards."""
    database: Database = request.app.state.db
    session = database.session()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_db)],
) -> User:
    """Resolve and return the signed-in user, or raise 401."""
    settings: Settings = request.app.state.settings
    try:
        claims = decode_access_token(
            token,
            secret_key=settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )
    except JWT_ERRORS as exc:
        raise _invalid_credentials() from exc

    subject = claims.get("sub")
    if subject is None:
        raise _invalid_credentials()

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise _invalid_credentials() from exc

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise _invalid_credentials()
    return user


# Convenient annotated dependency for endpoints that only need the current user.
CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: UserRole) -> Callable[[CurrentUser], User]:
    """Return a dependency that allows only the given roles.

    A user whose role is not listed receives 403 Forbidden. Authentication
    failures (missing or invalid token) surface first as 401.
    """
    allowed = frozenset(roles)

    def dependency(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return user

    return dependency
