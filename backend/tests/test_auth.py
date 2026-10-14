"""Tests for the authentication endpoints and role enforcement (task 6)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from app.dependencies import require_role
from app.models import User, UserRole
from app.security import decode_access_token

PASSWORD = "correct horse battery staple"


def _login(client: TestClient, email: str, password: str = PASSWORD):
    """POST the OAuth2 password form with ``username`` set to the email."""
    return client.post(
        "/auth/token",
        data={"username": email, "password": password},
    )


def test_login_success_returns_a_token_with_id_and_role(
    api_client: TestClient, create_user: Callable[..., User]
) -> None:
    user = create_user("manager@efinges.test", role=UserRole.MANAGER)

    response = _login(api_client, "manager@efinges.test")

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    claims = decode_access_token(
        body["access_token"], secret_key="test-secret-key-at-least-32-bytes-long"
    )
    assert claims["sub"] == str(user.id)
    assert claims["role"] == "manager"


def test_login_failure_with_wrong_password(
    api_client: TestClient, create_user: Callable[..., User]
) -> None:
    create_user("resident@efinges.test")

    response = _login(api_client, "resident@efinges.test", password="wrong")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_failure_with_unknown_email(api_client: TestClient) -> None:
    response = _login(api_client, "nobody@efinges.test")

    assert response.status_code == 401


def test_login_failure_when_account_is_inactive(
    api_client: TestClient, create_user: Callable[..., User]
) -> None:
    create_user("inactive@efinges.test", is_active=False)

    response = _login(api_client, "inactive@efinges.test")

    assert response.status_code == 401


def test_me_returns_the_current_user_without_the_password(
    api_client: TestClient, create_user: Callable[..., User]
) -> None:
    user = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    token = _login(api_client, "admin@efinges.test").json()["access_token"]

    response = api_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "email": "admin@efinges.test",
        "role": "administrator",
        "is_active": True,
    }
    assert "password" not in response.text


def test_me_without_a_token_returns_401(api_client: TestClient) -> None:
    assert api_client.get("/auth/me").status_code == 401


def test_me_with_an_invalid_token_returns_401(api_client: TestClient) -> None:
    response = api_client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401


def test_me_with_a_token_for_a_deleted_user_returns_401(
    api_client: TestClient, create_user: Callable[..., User]
) -> None:
    create_user("ghost@efinges.test")
    token = _login(api_client, "ghost@efinges.test").json()["access_token"]

    # Delete the account after issuing the token.
    with api_client.app.state.db.session() as db_session:
        db_session.query(User).delete()
        db_session.commit()

    response = api_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_me_with_a_token_for_a_deactivated_user_returns_401(
    api_client: TestClient, create_user: Callable[..., User]
) -> None:
    user = create_user("soon-inactive@efinges.test")
    token = _login(api_client, "soon-inactive@efinges.test").json()["access_token"]

    with api_client.app.state.db.session() as db_session:
        stored = db_session.get(User, user.id)
        assert stored is not None
        stored.is_active = False
        db_session.commit()

    response = api_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


# --- Role enforcement -------------------------------------------------------


def _mount_protected_route(app: FastAPI) -> None:
    """Add a manager/administrator-only route to exercise require_role."""

    @app.get("/manager-area")
    def manager_area(
        user: Annotated[
            User,
            Depends(require_role(UserRole.MANAGER, UserRole.ADMINISTRATOR)),
        ],
    ) -> dict[str, str]:
        return {"email": user.email}


def test_role_is_allowed(api_app: FastAPI, create_user: Callable[..., User]) -> None:
    _mount_protected_route(api_app)
    create_user("manager@efinges.test", role=UserRole.MANAGER)
    create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)

    with TestClient(api_app) as client:
        for email in ("manager@efinges.test", "admin@efinges.test"):
            token = _login(client, email).json()["access_token"]
            response = client.get("/manager-area", headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 200
            assert response.json() == {"email": email}


def test_role_rejection_returns_403(api_app: FastAPI, create_user: Callable[..., User]) -> None:
    _mount_protected_route(api_app)
    create_user("resident@efinges.test", role=UserRole.RESIDENT)

    with TestClient(api_app) as client:
        token = _login(client, "resident@efinges.test").json()["access_token"]
        response = client.get("/manager-area", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient role"


def test_role_rejection_prefers_401_over_403_without_a_token(
    api_app: FastAPI,
) -> None:
    """A missing token is an authentication failure (401), not a 403."""
    _mount_protected_route(api_app)

    with TestClient(api_app) as client:
        response = client.get("/manager-area")

    assert response.status_code == 401


def test_require_role_returns_403_directly(create_user: Callable[..., User]) -> None:
    """The dependency itself raises 403 for an insufficient role."""
    dependency = require_role(UserRole.ADMINISTRATOR)
    resident = User(
        email="resident@efinges.test",
        hashed_password="x",
        role=UserRole.RESIDENT,
    )

    with pytest.raises(HTTPException) as excinfo:
        dependency(resident)

    assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN
