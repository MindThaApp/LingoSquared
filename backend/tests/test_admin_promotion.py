from app.db.session import SessionLocal
from app.main import validate_startup_settings
from app.models import User
from app.scripts.promote_admin import promote_admin


def test_startup_rejects_default_jwt_secret_outside_dev_or_test():
    class Settings:
        jwt_secret = "development-only-secret"
        app_env = "production"

    import pytest

    with pytest.raises(RuntimeError, match="built-in JWT secret"):
        validate_startup_settings(Settings())

    Settings.app_env = "test"
    validate_startup_settings(Settings())


def test_registration_does_not_grant_admin_from_admin_emails(client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "listed-admin@example.com")
    response = client.post(
        "/auth/register",
        json={"email": "listed-admin@example.com", "password": "password123"},
    )

    assert response.status_code == 201, response.text
    assert response.json()["user"]["is_admin"] is False
    assert client.get(
        "/admin/content/issues",
        headers={"Authorization": f"Bearer {response.json()['access_token']}"},
    ).json()["error"]["code"] == "admin_required"


def test_promote_admin_sets_existing_user_admin(client):
    response = client.post(
        "/auth/register",
        json={"email": "promote-existing@example.com", "password": "password123"},
    )
    assert response.status_code == 201, response.text

    with SessionLocal() as db:
        assert promote_admin(db, " PROMOTE-EXISTING@example.com ") is True
        user = db.query(User).filter_by(email="promote-existing@example.com").one()
        assert user.is_admin is True
        user.is_admin = False
        db.commit()


def test_promote_admin_does_not_create_missing_user():
    with SessionLocal() as db:
        assert promote_admin(db, "missing-promotion-target@example.com") is False
