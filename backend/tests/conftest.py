import os

# Tests run with weak placeholder secrets (short JWT secret, "change-me" DB
# password); the production-like startup checks in app.main only apply when
# APP_ENV is not dev/test, so declare the test environment explicitly.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://lingosquared:change-me@localhost:5432/lingosquared_test")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from app.core import rate_limit
from app.db.session import engine, SessionLocal
from app.main import app
from app.content.seed import main as seed
from app.models import User

# Per-exercise tests generated from the compiled docs/content corpus. They
# verify content, not code, and make up ~98% of the test count. Select with
# `-m content` / deselect with `-m "not content"`; with no -m the full suite
# runs exactly as before.
CONTENT_TEST_FILES = {"test_content_answer_shapes.py"}


def pytest_collection_modifyitems(items):
    for item in items:
        if item.path.name in CONTENT_TEST_FILES:
            item.add_marker(pytest.mark.content)


@pytest.fixture(scope="session", autouse=True)
def database():
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    from app.db.session import Base
    Base.metadata.create_all(engine)
    seed()
    yield

@pytest.fixture(autouse=True)
def reset_rate_limits():
    # The rate limiters are process-wide in-memory state
    # (app/core/rate_limit.py), shared across every test in this session
    # via the single imported `app` module — without resetting between
    # tests, the many register/login/answer calls the existing suite
    # already makes (the `auth`/`admin` fixtures below, plus every
    # phase-specific test file) would trip each other's limits well
    # before any test actually intends to exercise rate limiting.
    rate_limit.reset_all()
    yield

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth(client):
    email = f"user-{os.urandom(4).hex()}@example.com"
    response = client.post("/auth/register", json={"email": email, "password": "password123", "display_name": "Test User"})
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

@pytest.fixture
def admin(client):
    response = client.post("/auth/register", json={"email": "admin@example.com", "password": "password123", "display_name": "Admin"})
    if response.status_code == 409:
        response = client.post("/auth/login", json={"email": "admin@example.com", "password": "password123"})
    assert response.status_code in (200, 201), response.text
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "admin@example.com"))
        user.is_admin = True
        db.commit()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
