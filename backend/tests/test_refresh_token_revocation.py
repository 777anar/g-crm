"""Covers RELEASE_CHECKLIST.md M7 (refresh tokens cannot be revoked)."""
import pytest

from core.auth.models import User
from core.auth.security import hash_password


@pytest.fixture()
def user(db_session):
    user = User(email="revoke@test.example", password_hash=hash_password("Password123!"), full_name="Revoke User")
    db_session.add(user)
    db_session.commit()
    return user


def _login(app_client):
    response = app_client.post(
        "/api/v1/auth/login", json={"email": "revoke@test.example", "password": "Password123!"}
    )
    assert response.status_code == 200
    return response.json()


def test_refresh_succeeds_before_logout(app_client, user):
    tokens = _login(app_client)
    response = app_client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_logout_revokes_the_refresh_token(app_client, user):
    tokens = _login(app_client)

    logout_response = app_client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout_response.status_code == 200

    refresh_response = app_client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_response.status_code == 401
    assert refresh_response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_logout_does_not_revoke_a_different_users_token(app_client, db_session, user):
    other = User(email="other@test.example", password_hash=hash_password("Password123!"), full_name="Other User")
    db_session.add(other)
    db_session.commit()

    revoke_tokens = _login(app_client)
    other_login = app_client.post(
        "/api/v1/auth/login", json={"email": "other@test.example", "password": "Password123!"}
    )
    assert other_login.status_code == 200
    other_tokens = other_login.json()

    app_client.post("/api/v1/auth/logout", json={"refresh_token": revoke_tokens["refresh_token"]})

    other_refresh = app_client.post("/api/v1/auth/refresh", json={"refresh_token": other_tokens["refresh_token"]})
    assert other_refresh.status_code == 200


def test_logging_in_again_after_logout_issues_a_usable_refresh_token(app_client, user):
    first_tokens = _login(app_client)
    app_client.post("/api/v1/auth/logout", json={"refresh_token": first_tokens["refresh_token"]})

    second_tokens = _login(app_client)
    response = app_client.post("/api/v1/auth/refresh", json={"refresh_token": second_tokens["refresh_token"]})
    assert response.status_code == 200


def test_logout_is_idempotent_and_never_errors_on_a_malformed_token(app_client):
    response = app_client.post("/api/v1/auth/logout", json={"refresh_token": "not-a-real-token"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_logout_twice_in_a_row_is_safe(app_client, user):
    tokens = _login(app_client)
    first = app_client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    second = app_client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    assert second.status_code == 200


def test_in_memory_denylist_generation_semantics():
    from core.auth.token_denylist import InMemoryTokenDenylist

    denylist = InMemoryTokenDenylist()
    assert denylist.current_generation("user-1") == 0
    assert denylist.is_revoked("user-1", 0) is False

    denylist.revoke_all("user-1")
    assert denylist.current_generation("user-1") == 1
    assert denylist.is_revoked("user-1", 0) is True
    assert denylist.is_revoked("user-1", 1) is False

    # a different user's generation is tracked independently
    assert denylist.current_generation("user-2") == 0
    assert denylist.is_revoked("user-2", 0) is False
