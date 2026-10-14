"""Tests for administrator user management (backlog task 9).

Covers administrator-only access, the create and update flows, password
hashing, and the rule that a password hash is never returned.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, UserRole
from app.security import verify_password

NEW_PASSWORD = "a-different-password"


def _create(
    client: TestClient,
    headers: dict[str, str],
    *,
    email: str = "new.manager@efinges.test",
    password: str = NEW_PASSWORD,
    role: str = "manager",
):
    return client.post(
        "/users",
        json={"email": email, "password": password, "role": role},
        headers=headers,
    )


# --- Access control ---------------------------------------------------------


def test_administrator_creates_a_user(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)

    response = _create(api_client, auth_token(admin))

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new.manager@efinges.test"
    assert body["role"] == "manager"
    assert body["is_active"] is True


def test_the_password_hash_is_never_returned(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)

    response = _create(api_client, auth_token(admin))

    assert "password" not in response.text
    assert NEW_PASSWORD not in response.text


def test_the_password_is_stored_hashed(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
    db_session: Session,
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)

    _create(api_client, auth_token(admin))

    created = db_session.query(User).filter_by(email="new.manager@efinges.test").one()
    assert created.hashed_password != NEW_PASSWORD
    assert verify_password(NEW_PASSWORD, created.hashed_password)


def test_a_manager_cannot_create_users(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    manager = create_user("manager@efinges.test", role=UserRole.MANAGER)

    response = _create(api_client, auth_token(manager))

    assert response.status_code == 403


def test_a_resident_cannot_list_users(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    resident = create_user("resident@efinges.test")

    response = api_client.get("/users", headers=auth_token(resident))

    assert response.status_code == 403


def test_user_management_requires_a_token(api_client: TestClient) -> None:
    assert api_client.get("/users").status_code == 401
    assert (
        api_client.post(
            "/users", json={"email": "x@efinges.test", "password": NEW_PASSWORD}
        ).status_code
        == 401
    )


# --- Creation rules ---------------------------------------------------------


def test_a_duplicate_email_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    headers = auth_token(admin)
    create_user("taken@efinges.test")

    response = _create(api_client, headers, email="taken@efinges.test")

    assert response.status_code == 409


def test_a_short_password_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)

    response = _create(api_client, auth_token(admin), password="short")

    assert response.status_code == 422


def test_an_invalid_role_is_rejected(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)

    response = _create(api_client, auth_token(admin), role="superuser")

    assert response.status_code == 422


def test_a_newly_created_user_can_log_in(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    _create(api_client, auth_token(admin))

    response = api_client.post(
        "/auth/token",
        data={"username": "new.manager@efinges.test", "password": NEW_PASSWORD},
    )

    assert response.status_code == 200


# --- Listing and filtering --------------------------------------------------


def test_administrator_lists_users_and_filters_by_role(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    create_user("manager@efinges.test", role=UserRole.MANAGER)
    create_user("resident@efinges.test")
    headers = auth_token(admin)

    everyone = api_client.get("/users", headers=headers).json()
    managers = api_client.get("/users?role=manager", headers=headers).json()

    assert len(everyone) == 3
    assert [row["email"] for row in managers] == ["manager@efinges.test"]


def test_listing_can_filter_by_activation(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    create_user("gone@efinges.test", is_active=False)
    headers = auth_token(admin)

    inactive = api_client.get("/users?is_active=false", headers=headers).json()

    assert [row["email"] for row in inactive] == ["gone@efinges.test"]


# --- Updates ----------------------------------------------------------------


def test_administrator_changes_a_role(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    resident = create_user("resident@efinges.test")

    response = api_client.patch(
        f"/users/{resident.id}", json={"role": "manager"}, headers=auth_token(admin)
    )

    assert response.status_code == 200
    assert response.json()["role"] == "manager"


def test_deactivating_a_user_blocks_login(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    resident = create_user("resident@efinges.test")

    response = api_client.patch(
        f"/users/{resident.id}",
        json={"is_active": False},
        headers=auth_token(admin),
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    blocked = api_client.post(
        "/auth/token",
        data={
            "username": "resident@efinges.test",
            "password": "correct horse battery staple",
        },
    )
    assert blocked.status_code == 401


def test_administrator_resets_a_password(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    resident = create_user("resident@efinges.test")

    response = api_client.patch(
        f"/users/{resident.id}",
        json={"password": "brand-new-password"},
        headers=auth_token(admin),
    )
    assert response.status_code == 200
    assert "brand-new-password" not in response.text

    relogin = api_client.post(
        "/auth/token",
        data={"username": "resident@efinges.test", "password": "brand-new-password"},
    )
    assert relogin.status_code == 200


def test_an_administrator_cannot_deactivate_their_own_account(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)

    response = api_client.patch(
        f"/users/{admin.id}",
        json={"is_active": False},
        headers=auth_token(admin),
    )

    assert response.status_code == 409


def test_an_administrator_cannot_demote_their_own_account(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)

    response = api_client.patch(
        f"/users/{admin.id}",
        json={"role": "manager"},
        headers=auth_token(admin),
    )

    assert response.status_code == 409


def test_an_administrator_may_keep_their_own_administrator_role(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    """Re-sending the current role is a no-op, not a self-demotion."""
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)

    response = api_client.patch(
        f"/users/{admin.id}",
        json={"role": "administrator"},
        headers=auth_token(admin),
    )

    assert response.status_code == 200


def test_updating_a_missing_user_returns_404(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)

    response = api_client.patch("/users/9999", json={"role": "manager"}, headers=auth_token(admin))

    assert response.status_code == 404


def test_reading_a_single_user(
    api_client: TestClient,
    create_user: Callable[..., User],
    auth_token: Callable[[User], dict[str, str]],
) -> None:
    admin = create_user("admin@efinges.test", role=UserRole.ADMINISTRATOR)
    resident = create_user("resident@efinges.test")
    headers = auth_token(admin)

    response = api_client.get(f"/users/{resident.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["email"] == "resident@efinges.test"
    assert "password" not in response.text
