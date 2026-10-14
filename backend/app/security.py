"""Password hashing and JWT helpers (backlog task 6).

Passwords are never stored in clear text: :func:`hash_password` derives an
Argon2 hash and :func:`verify_password` checks a candidate against it. Access
tokens are signed JWTs carrying the user id (``sub``) and role (``role``),
issued by ``POST /auth/token`` and validated by the request dependencies.

The signing algorithm and token lifetime come from the application settings so
tests can override them and production can pick a strong ``SECRET_KEY``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

# Argon2 is the recommended default for new applications. The hasher is
# stateless and safe to share between requests.
_password_hash = PasswordHash.recommended()

# Raised for any reason a token cannot be trusted: bad signature, expired,
# malformed, or missing claims.
JWT_ERRORS = (jwt.PyJWTError,)


def hash_password(password: str) -> str:
    """Return a salted Argon2 hash of ``password``."""
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return True when ``password`` matches the stored ``password_hash``."""
    try:
        return _password_hash.verify(password, password_hash)
    except Exception:
        # A malformed or unknown hash scheme must fail closed.
        return False


def create_access_token(
    *,
    user_id: int,
    role: str,
    secret_key: str,
    algorithm: str = "HS256",
    expires_minutes: int = 60,
) -> str:
    """Return a signed JWT identifying ``user_id`` and their ``role``."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(
    token: str,
    *,
    secret_key: str,
    algorithm: str = "HS256",
) -> dict[str, object]:
    """Decode and verify ``token``, returning its claims.

    Raises :class:`jwt.PyJWTError` (see :data:`JWT_ERRORS`) when the token is
    invalid or expired; callers translate that into an HTTP 401.
    """
    return jwt.decode(token, secret_key, algorithms=[algorithm])
