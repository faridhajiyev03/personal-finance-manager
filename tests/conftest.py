"""Shared test setup.

Database tests run against a separate PostgreSQL database given in
TEST_DATABASE_URL. Its name must end with "_test", so a real database can
never be wiped by mistake. Every test starts with empty tables.
"""

import os

import pytest
from sqlalchemy.engine import make_url

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if TEST_DATABASE_URL:
    test_database_name = make_url(TEST_DATABASE_URL).database or ""
    if not test_database_name.endswith("_test"):
        raise RuntimeError(
            "TEST_DATABASE_URL must point to a database whose name ends with '_test'"
        )

# The application reads its settings at import time, so they must be set
# before the application is imported. Environment variables take priority
# over a local .env file.
os.environ["DATABASE_URL"] = (
    TEST_DATABASE_URL or "postgresql+psycopg://localhost/not_configured_test"
)
os.environ["JWT_SECRET"] = "test-secret-key-not-for-production"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import app.models  # noqa: E402,F401  (registers all tables on Base.metadata)
from app.database import Base, engine  # noqa: E402
from main import app  # noqa: E402

PASSWORD = "test-password-123"


@pytest.fixture(scope="session")
def test_engine():
    """Create all tables once per test run and drop them at the end."""
    if not TEST_DATABASE_URL:
        pytest.skip("Set TEST_DATABASE_URL to run database tests")

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(test_engine):
    """Empty every table before each test, so tests never affect each other."""
    with test_engine.begin() as connection:
        connection.execute(
            text("TRUNCATE transactions, users RESTART IDENTITY CASCADE")
        )

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def account(client):
    """Register and log in a user; return the user and its auth headers."""

    def create(email="owner@example.com"):
        credentials = {"email": email, "password": PASSWORD}

        registered = client.post("/auth/register", json=credentials)
        assert registered.status_code == 201, registered.text

        logged_in = client.post("/auth/login", json=credentials)
        assert logged_in.status_code == 200, logged_in.text

        token = logged_in.json()["access_token"]
        return registered.json(), {"Authorization": f"Bearer {token}"}

    return create


@pytest.fixture
def add_transaction(client):
    """Create a transaction through the API and return the response body."""

    def create(headers, **fields):
        payload = {
            "type": "expense",
            "amount": "10.00",
            "category": "Food",
            "date": "2026-11-01",
            **fields,
        }
        response = client.post("/transactions", json=payload, headers=headers)
        assert response.status_code == 201, response.text
        return response.json()

    return create
