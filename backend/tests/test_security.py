"""Tests for the password hashing and JWT helpers (backlog task 6)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

# HMAC-SHA256 warns below 32 bytes, so tests use a long enough secret.
SECRET = "test-secret-key-at-least-32-bytes-long"
OTHER_SECRET = "a-different-test-secret-key-long"


def test_password_hashing_is_salted_and_verifiable() -> None:
    password = "correct horse battery staple"
    first = hash_password(password)
    second = hash_password(password)

    # The plaintext is never stored, and two hashes of the same password differ
    # because each is salted.
    assert password not in first
    assert first != second
    assert verify_password(password, first)
    assert verify_password(password, second)


def test_password_verification_rejects_wrong_password() -> None:
    hashed = hash_password("right-password")
    assert verify_password("wrong-password", hashed) is False


def test_password_verification_fails_closed_on_malformed_hash() -> None:
    # A corrupt stored hash must not raise; it must simply fail.
    assert verify_password("anything", "not-a-valid-hash") is False


def test_access_token_round_trip_carries_id_and_role() -> None:
    token = create_access_token(
        user_id=42,
        role="manager",
        secret_key=SECRET,
        expires_minutes=5,
    )

    claims = decode_access_token(token, secret_key=SECRET)
    assert claims["sub"] == "42"
    assert claims["role"] == "manager"


def test_access_token_rejects_a_different_secret() -> None:
    token = create_access_token(user_id=1, role="resident", secret_key=SECRET)

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token, secret_key=OTHER_SECRET)


def test_expired_access_token_is_rejected() -> None:
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "1",
            "role": "resident",
            "iat": now - timedelta(minutes=10),
            "exp": now - timedelta(minutes=5),
        },
        SECRET,
        algorithm="HS256",
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token, secret_key=SECRET)
