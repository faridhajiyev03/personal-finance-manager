from datetime import datetime, timedelta, timezone

import jwt
import pytest

from tests.conftest import PASSWORD


def test_register_returns_user_without_password(client):
    response = client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": PASSWORD},
    )

    assert response.status_code == 201
    assert response.json() == {"id": 1, "email": "new@example.com"}


def test_duplicate_email_is_rejected_ignoring_case(client):
    client.post("/auth/register", json={"email": "anna@example.com", "password": PASSWORD})

    response = client.post(
        "/auth/register",
        json={"email": "ANNA@example.com", "password": PASSWORD},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": PASSWORD},
        {"email": "short@example.com", "password": "1234567"},
        {"email": "missing-password@example.com"},
    ],
)
def test_invalid_registration_is_rejected(client, payload):
    response = client.post("/auth/register", json=payload)

    assert response.status_code == 422


def test_login_and_get_current_user(client, account):
    user, headers = account("Owner@Example.com")

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json() == user
    assert user["email"] == "owner@example.com"


@pytest.mark.parametrize(
    "credentials",
    [
        {"email": "owner@example.com", "password": "wrong-password"},
        {"email": "nobody@example.com", "password": PASSWORD},
    ],
)
def test_wrong_credentials_get_the_same_401(client, account, credentials):
    account()

    response = client.post("/auth/login", json=credentials)

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}


def make_token(**claims):
    return jwt.encode(claims, "test-secret-key-not-for-production", algorithm="HS256")


def future():
    return datetime.now(timezone.utc) + timedelta(minutes=5)


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        make_token(sub="1", exp=datetime.now(timezone.utc) - timedelta(minutes=1)),
        make_token(sub="1"),
        make_token(sub="999", exp=future()),
        make_token(sub="abc", exp=future()),
        jwt.encode({"sub": "1", "exp": future()}, "another-secret", algorithm="HS256"),
    ],
    ids=["garbage", "expired", "no-exp", "unknown-user", "bad-subject", "wrong-secret"],
)
def test_invalid_tokens_are_rejected(client, account, token):
    account()

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


def test_missing_token_is_rejected(client):
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
