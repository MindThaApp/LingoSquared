from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import User


def token_user_id(auth_header):
    return decode_token(auth_header["Authorization"].split()[1])


def create_managed_user(client, admin, email="beta-user@example.com"):
    response = client.post(
        "/admin/users",
        headers=admin,
        json={"email": email, "display_name": "Beta User"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_create_user_returns_working_temporary_password(client, admin):
    email = "created-beta@example.com"
    created = create_managed_user(client, admin, email=email)

    assert created["temporary_password"]
    assert created["user"]["email"] == email
    assert created["user"]["is_active"] is True

    login = client.post(
        "/auth/login",
        json={"email": email, "password": created["temporary_password"]},
    )
    assert login.status_code == 200, login.text
    assert login.json()["user"]["email"] == email


def test_admin_reset_password_invalidates_old_password(client, admin):
    email = "reset-beta@example.com"
    created = create_managed_user(client, admin, email=email)
    user_id = created["user"]["id"]
    old_password = created["temporary_password"]

    reset = client.post(
        f"/admin/users/{user_id}/reset-password",
        headers=admin,
    )
    assert reset.status_code == 200, reset.text
    new_password = reset.json()["temporary_password"]
    assert new_password and new_password != old_password

    old_login = client.post(
        "/auth/login",
        json={"email": email, "password": old_password},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/auth/login",
        json={"email": email, "password": new_password},
    )
    assert new_login.status_code == 200, new_login.text


def test_admin_deactivate_blocks_login_and_existing_access_token(client, admin):
    email = "deactivate-beta@example.com"
    created = create_managed_user(client, admin, email=email)
    user_id = created["user"]["id"]
    password = created["temporary_password"]
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    user_auth = {"Authorization": f"Bearer {login.json()['access_token']}"}

    deactivated = client.post(
        f"/admin/users/{user_id}/deactivate",
        headers=admin,
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["is_active"] is False

    blocked_login = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert blocked_login.status_code == 401

    blocked_token = client.get("/auth/me", headers=user_auth)
    assert blocked_token.status_code == 401


def test_last_admin_demotion_refused(client, admin):
    created = create_managed_user(
        client,
        admin,
        email="persisted-admin@example.com",
    )
    persisted_admin_id = created["user"]["id"]
    password = created["temporary_password"]

    promoted = client.post(
        f"/admin/users/{persisted_admin_id}/admin",
        headers=admin,
        json={"is_admin": True},
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["is_admin"] is True

    login = client.post(
        "/auth/login",
        json={"email": "persisted-admin@example.com", "password": password},
    )
    assert login.status_code == 200, login.text
    persisted_admin_auth = {"Authorization": f"Bearer {login.json()['access_token']}"}
    bootstrap_admin_id = token_user_id(admin)

    try:
        deactivated_bootstrap = client.post(
            f"/admin/users/{bootstrap_admin_id}/deactivate",
            headers=persisted_admin_auth,
        )
        assert deactivated_bootstrap.status_code == 200, deactivated_bootstrap.text

        demotion = client.post(
            f"/admin/users/{persisted_admin_id}/admin",
            headers=persisted_admin_auth,
            json={"is_admin": False},
        )
        assert demotion.status_code == 409
        assert demotion.json()["error"]["code"] == "last_admin"
    finally:
        with SessionLocal() as db:
            bootstrap = db.get(User, bootstrap_admin_id)
            if bootstrap:
                bootstrap.is_active = True
                db.commit()
