import hashlib
import secrets
import threading
import time
from datetime import timedelta

import pytest
from sqlalchemy import func, inspect, select

from app.api.router import find_refresh_token, lock_user_sessions, rotate_refresh_token, utc_now
from app.core.config import get_settings
from app.core.security import decode_token
from app.db.session import SessionLocal, engine
from app.models import RefreshToken
from app.scripts.prune_refresh_tokens import main as prune_refresh_tokens_main


def register(client, email):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Refresh"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(access_token):
    return {"Authorization": f"Bearer {access_token}"}


def digest(raw_token):
    return hashlib.sha256(raw_token.encode()).hexdigest()


def age_rotation(raw_token, seconds):
    """Pretend the rotation of raw_token happened `seconds` ago."""
    with SessionLocal() as db:
        token = db.scalar(select(RefreshToken).where(RefreshToken.token_sha256 == digest(raw_token)))
        assert token.revoked_at is not None
        token.revoked_at = utc_now() - timedelta(seconds=seconds)
        db.commit()


def outside_grace():
    return get_settings().refresh_reuse_grace_seconds + 5


def live_token_count(user_id):
    with SessionLocal() as db:
        return db.scalar(
            select(func.count())
            .select_from(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        )


def proposal():
    return secrets.token_urlsafe(48)


def test_refresh_issues_new_working_access_token(client):
    first = register(client, "refresh-success@example.com")

    refreshed = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )

    assert refreshed.status_code == 200, refreshed.text
    body = refreshed.json()
    assert body["expires_in"] == 1800
    assert body["access_token"] != first["access_token"]
    assert body["refresh_token"] != first["refresh_token"]

    me = client.get("/auth/me", headers=auth_header(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "refresh-success@example.com"


def test_refresh_uses_digest_lookup_and_rejects_legacy_row(client):
    first = register(client, "refresh-digest@example.com")
    user_id = decode_token(first["access_token"])

    with SessionLocal() as db:
        token = db.scalar(select(RefreshToken).where(RefreshToken.user_id == user_id))
        assert token.token_sha256 == hashlib.sha256(first["refresh_token"].encode()).hexdigest()
        token.token_sha256 = None
        db.commit()

    refreshed = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert refreshed.status_code == 401
    assert refreshed.json()["error"]["code"] == "invalid_refresh_token"


def test_refresh_rotation_invalidates_old_refresh_token(client):
    first = register(client, "refresh-rotation@example.com")
    refreshed = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert refreshed.status_code == 200, refreshed.text
    age_rotation(first["refresh_token"], outside_grace())

    reused = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )

    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "refresh_token_reused"


def test_refresh_reuse_detection_revokes_all_user_refresh_tokens(client):
    first = register(client, "refresh-reuse@example.com")
    login = client.post(
        "/auth/login",
        json={"email": "refresh-reuse@example.com", "password": "password123"},
    )
    assert login.status_code == 200, login.text

    rotated = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert rotated.status_code == 200, rotated.text
    user_id = decode_token(rotated.json()["access_token"])
    age_rotation(first["refresh_token"], outside_grace())

    reused = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "refresh_token_reused"

    with SessionLocal() as db:
        unrevoked = db.scalar(
            select(func.count())
            .select_from(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
    assert unrevoked == 0

    second_session = client.post(
        "/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    )
    assert second_session.status_code == 401
    assert second_session.json()["error"]["code"] == "refresh_token_reused"

    rotated_session = client.post(
        "/auth/refresh",
        json={"refresh_token": rotated.json()["refresh_token"]},
    )
    assert rotated_session.status_code == 401
    assert rotated_session.json()["error"]["code"] == "refresh_token_reused"


def test_expired_refresh_token_is_rejected(client):
    first = register(client, "refresh-expired@example.com")
    user_id = decode_token(first["access_token"])

    with SessionLocal() as db:
        token = db.scalar(
            select(RefreshToken).where(RefreshToken.user_id == user_id)
        )
        token.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()

    refreshed = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )

    assert refreshed.status_code == 401
    assert refreshed.json()["error"]["code"] == "invalid_refresh_token"


def test_logout_revokes_presented_refresh_token(client):
    first = register(client, "refresh-logout@example.com")

    logout = client.post(
        "/auth/logout",
        json={"refresh_token": first["refresh_token"]},
    )
    assert logout.status_code == 204
    assert logout.content == b""

    refreshed = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert refreshed.status_code == 401
    assert refreshed.json()["error"]["code"] == "refresh_token_reused"


def _add_refresh_token(db, user_id, token_id, expires_at, revoked_at=None):
    db.add(
        RefreshToken(
            id=token_id,
            token_hash=f"not-used-{token_id}",
            token_sha256=None,
            user_id=user_id,
            issued_at=utc_now() - timedelta(days=20),
            expires_at=expires_at,
            revoked_at=revoked_at,
        )
    )


def test_login_and_refresh_prune_same_users_expired_and_old_revoked_rows(client):
    first = register(client, "refresh-prune-login@example.com")
    user_id = decode_token(first["access_token"])
    now = utc_now()
    with SessionLocal() as db:
        _add_refresh_token(db, user_id, "expired-login", now - timedelta(seconds=1))
        _add_refresh_token(
            db,
            user_id,
            "old-revoked-login",
            now + timedelta(days=30),
            now - timedelta(days=8),
        )
        _add_refresh_token(
            db,
            user_id,
            "recent-revoked-login",
            now + timedelta(days=30),
            now - timedelta(days=2),
        )
        db.commit()

    logged_in = client.post(
        "/auth/login",
        json={"email": "refresh-prune-login@example.com", "password": "password123"},
    )
    assert logged_in.status_code == 200, logged_in.text
    with SessionLocal() as db:
        rows = set(db.scalars(select(RefreshToken.id).where(RefreshToken.user_id == user_id)))
    assert "expired-login" not in rows
    assert "old-revoked-login" not in rows
    assert "recent-revoked-login" in rows

    new_token = logged_in.json()["refresh_token"]
    now = utc_now()
    with SessionLocal() as db:
        _add_refresh_token(db, user_id, "expired-refresh", now - timedelta(seconds=1))
        _add_refresh_token(
            db,
            user_id,
            "old-revoked-refresh",
            now + timedelta(days=30),
            now - timedelta(days=9),
        )
        db.commit()

    refreshed = client.post("/auth/refresh", json={"refresh_token": new_token})
    assert refreshed.status_code == 200, refreshed.text
    with SessionLocal() as db:
        rows = set(db.scalars(select(RefreshToken.id).where(RefreshToken.user_id == user_id)))
    assert "expired-refresh" not in rows
    assert "old-revoked-refresh" not in rows


def test_global_refresh_token_pruner_removes_only_expired_or_old_revoked(client, capsys):
    registered = register(client, "refresh-prune-global@example.com")
    user_id = decode_token(registered["access_token"])
    now = utc_now()
    with SessionLocal() as db:
        _add_refresh_token(db, user_id, "global-expired", now - timedelta(seconds=1))
        _add_refresh_token(
            db,
            user_id,
            "global-old-revoked",
            now + timedelta(days=10),
            now - timedelta(days=8),
        )
        _add_refresh_token(
            db,
            user_id,
            "global-recent-revoked",
            now + timedelta(days=10),
            now - timedelta(days=1),
        )
        db.commit()

    prune_refresh_tokens_main()
    assert capsys.readouterr().out == "Pruned 2 refresh token rows.\n"
    with SessionLocal() as db:
        remaining = set(db.scalars(select(RefreshToken.id).where(RefreshToken.user_id == user_id)))
    assert "global-expired" not in remaining
    assert "global-old-revoked" not in remaining
    assert "global-recent-revoked" in remaining


# --- Lost-response / concurrent-refresh handling -------------------------
#
# A rotation whose response never reaches the client (page reloaded or
# closed mid-request) leaves the client holding the rotated-out token. That
# must not log the user out, while a rotated-out token replayed outside the
# grace window must still revoke every session.


def test_reuse_inside_grace_window_returns_the_same_successor(client):
    first = register(client, "refresh-grace-inside@example.com")
    user_id = decode_token(first["access_token"])
    rotated = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200, rotated.text
    successor = rotated.json()["refresh_token"]

    # The client lost that response and retries with the old token.
    retried = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert retried.status_code == 200, retried.text
    assert retried.json()["refresh_token"] == successor
    me = client.get("/auth/me", headers=auth_header(retried.json()["access_token"]))
    assert me.status_code == 200

    # Nothing new was minted: the chain did not branch.
    assert live_token_count(user_id) == 1

    # The successor is still the working head of the chain.
    onward = client.post("/auth/refresh", json={"refresh_token": successor})
    assert onward.status_code == 200, onward.text
    head = onward.json()["refresh_token"]

    # Once the successor has itself been rotated, the original token no
    # longer qualifies, even inside the window: that is real reuse.
    stale = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert stale.status_code == 401
    assert stale.json()["error"]["code"] == "refresh_token_reused"
    assert live_token_count(user_id) == 0
    dead_head = client.post("/auth/refresh", json={"refresh_token": head})
    assert dead_head.status_code == 401


def test_reuse_after_grace_window_revokes_the_family(client):
    first = register(client, "refresh-grace-after@example.com")
    user_id = decode_token(first["access_token"])
    rotated = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200, rotated.text
    age_rotation(first["refresh_token"], outside_grace())

    replayed = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert replayed.status_code == 401
    assert replayed.json()["error"]["code"] == "refresh_token_reused"
    assert live_token_count(user_id) == 0

    successor = client.post("/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]})
    assert successor.status_code == 401
    assert successor.json()["error"]["code"] == "refresh_token_reused"


def test_grace_window_can_be_disabled(client, monkeypatch):
    monkeypatch.setenv("REFRESH_REUSE_GRACE_SECONDS", "0")
    get_settings.cache_clear()
    try:
        first = register(client, "refresh-grace-disabled@example.com")
        rotated = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
        assert rotated.status_code == 200, rotated.text
        replayed = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
        assert replayed.status_code == 401
        assert replayed.json()["error"]["code"] == "refresh_token_reused"
    finally:
        get_settings.cache_clear()


def test_logout_revoked_token_gets_no_grace(client):
    first = register(client, "refresh-grace-logout@example.com")
    rotated = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200, rotated.text
    successor = rotated.json()["refresh_token"]
    logout = client.post("/auth/logout", json={"refresh_token": successor})
    assert logout.status_code == 204

    # The successor is logged out, so the predecessor must not revive it.
    replayed = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert replayed.status_code == 401
    assert replayed.json()["error"]["code"] == "refresh_token_reused"
    again = client.post("/auth/refresh", json={"refresh_token": successor})
    assert again.status_code == 401


def test_concurrent_refresh_of_one_token_yields_one_successor(client):
    first = register(client, "refresh-concurrent@example.com")
    user_id = decode_token(first["access_token"])
    # One rotation plus the grace window's replay cap.
    workers = 1 + get_settings().refresh_reuse_grace_max_replays
    barrier = threading.Barrier(workers)
    results = [None] * workers

    def refresh(index):
        barrier.wait()
        results[index] = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})

    threads = [threading.Thread(target=refresh, args=(i,)) for i in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert all(r is not None and r.status_code == 200 for r in results), [
        (r.status_code, r.text) if r is not None else None for r in results
    ]
    successors = {r.json()["refresh_token"] for r in results}
    assert len(successors) == 1
    assert live_token_count(user_id) == 1
    onward = client.post("/auth/refresh", json={"refresh_token": successors.pop()})
    assert onward.status_code == 200, onward.text


def test_client_proposed_successor_is_used(client):
    first = register(client, "refresh-proposal@example.com")
    proposed = proposal()
    rotated = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"], "next_refresh_token": proposed},
    )
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["refresh_token"] == proposed
    onward = client.post("/auth/refresh", json={"refresh_token": proposed})
    assert onward.status_code == 200, onward.text


def test_retry_with_matching_proposal_is_idempotent_after_the_window(client):
    # The page was closed while the request was in flight and reopened much
    # later. The client stored its proposed successor before sending, so it
    # resends the identical request; that proves it already holds the
    # successor, so the replay is safe at any age.
    first = register(client, "refresh-proposal-retry@example.com")
    user_id = decode_token(first["access_token"])
    proposed = proposal()
    body = {"refresh_token": first["refresh_token"], "next_refresh_token": proposed}
    rotated = client.post("/auth/refresh", json=body)
    assert rotated.status_code == 200, rotated.text
    age_rotation(first["refresh_token"], 3 * 24 * 3600)

    retried = client.post("/auth/refresh", json=body)
    assert retried.status_code == 200, retried.text
    assert retried.json()["refresh_token"] == proposed
    assert live_token_count(user_id) == 1


def test_retry_with_wrong_proposal_after_the_window_revokes(client):
    first = register(client, "refresh-proposal-wrong@example.com")
    user_id = decode_token(first["access_token"])
    rotated = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"], "next_refresh_token": proposal()},
    )
    assert rotated.status_code == 200, rotated.text
    age_rotation(first["refresh_token"], outside_grace())

    replayed = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"], "next_refresh_token": proposal()},
    )
    assert replayed.status_code == 401
    assert replayed.json()["error"]["code"] == "refresh_token_reused"
    assert live_token_count(user_id) == 0


def test_matching_proposal_does_not_revive_a_rotated_successor(client):
    first = register(client, "refresh-proposal-stale@example.com")
    user_id = decode_token(first["access_token"])
    proposed = proposal()
    body = {"refresh_token": first["refresh_token"], "next_refresh_token": proposed}
    assert client.post("/auth/refresh", json=body).status_code == 200
    onward = client.post("/auth/refresh", json={"refresh_token": proposed})
    assert onward.status_code == 200, onward.text

    replayed = client.post("/auth/refresh", json=body)
    assert replayed.status_code == 401
    assert replayed.json()["error"]["code"] == "refresh_token_reused"
    assert live_token_count(user_id) == 0


def test_proposal_that_already_exists_is_ignored(client):
    first = register(client, "refresh-proposal-taken@example.com")
    other = register(client, "refresh-proposal-other@example.com")
    rotated = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"], "next_refresh_token": other["refresh_token"]},
    )
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["refresh_token"] != other["refresh_token"]
    # The other user's session is untouched.
    still = client.post("/auth/refresh", json={"refresh_token": other["refresh_token"]})
    assert still.status_code == 200, still.text


@pytest.mark.parametrize(
    "bad",
    ["short", "x" * 42, "has spaces " * 5, "y" * 129, "A" * 43, "abcdefghij" * 6, "0123456789abcde" * 3],
)
def test_malformed_proposal_is_rejected(client, bad):
    first = register(client, f"refresh-proposal-bad-{len(bad)}-{bad[:3].strip()}@example.com")
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"], "next_refresh_token": bad},
    )
    assert response.status_code == 422


def test_successor_is_not_stored_in_the_clear(client):
    first = register(client, "refresh-sealed@example.com")
    rotated = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200, rotated.text
    successor = rotated.json()["refresh_token"]
    with SessionLocal() as db:
        old = db.scalar(select(RefreshToken).where(RefreshToken.token_sha256 == digest(first["refresh_token"])))
        assert old.replaced_by_id is not None
        assert old.successor_sealed
        assert successor not in old.successor_sealed


def test_grace_window_answers_a_bounded_number_of_replays(client):
    first = register(client, "refresh-grace-cap@example.com")
    user_id = decode_token(first["access_token"])
    rotated = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200, rotated.text
    successor = rotated.json()["refresh_token"]

    for _ in range(get_settings().refresh_reuse_grace_max_replays):
        retried = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
        assert retried.status_code == 200, retried.text
        assert retried.json()["refresh_token"] == successor

    # Past the cap the window stops minting access tokens: it is reuse.
    over = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert over.status_code == 401
    assert over.json()["error"]["code"] == "refresh_token_reused"
    assert live_token_count(user_id) == 0


def test_sealed_successor_is_dropped_once_the_successor_rotates(client):
    first = register(client, "refresh-sealed-dropped@example.com")
    rotated = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200, rotated.text
    onward = client.post("/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]})
    assert onward.status_code == 200, onward.text
    with SessionLocal() as db:
        old = db.scalar(select(RefreshToken).where(RefreshToken.token_sha256 == digest(first["refresh_token"])))
        assert old.replaced_by_id is not None
        assert old.successor_sealed is None


def test_revoke_all_waits_for_a_concurrent_rotation_and_revokes_its_successor(client):
    # The live head T2 is being rotated (T3 inserted, not yet committed)
    # while an older T0 is presented. Reuse detection's revoke-all must not
    # miss T3.
    first = register(client, "refresh-revoke-race@example.com")
    user_id = decode_token(first["access_token"])
    t0 = first["refresh_token"]
    t1 = client.post("/auth/refresh", json={"refresh_token": t0}).json()["refresh_token"]
    t2 = client.post("/auth/refresh", json={"refresh_token": t1}).json()["refresh_token"]

    result = {}
    with SessionLocal() as rotation:
        lock_user_sessions(rotation, user_id)
        head = find_refresh_token(rotation, t2, for_update=True)
        t3 = rotate_refresh_token(rotation, head, t2, None, utc_now())

        def present_stale():
            result["response"] = client.post("/auth/refresh", json={"refresh_token": t0})

        thief_detected = threading.Thread(target=present_stale)
        thief_detected.start()
        time.sleep(1.0)
        # The reuse request must be waiting on the user lock, not done.
        assert "response" not in result
        rotation.commit()
    thief_detected.join(timeout=30)

    assert result["response"].status_code == 401
    assert result["response"].json()["error"]["code"] == "refresh_token_reused"
    assert live_token_count(user_id) == 0
    survivor = client.post("/auth/refresh", json={"refresh_token": t3})
    assert survivor.status_code == 401


def test_concurrent_identical_proposals_do_not_500(client):
    # Two different users' rotations propose the same value at once: the
    # second insert hits the unique index after the existence check passed.
    first = register(client, "refresh-same-proposal-a@example.com")
    other = register(client, "refresh-same-proposal-b@example.com")
    first_user = decode_token(first["access_token"])
    shared = proposal()

    result = {}
    with SessionLocal() as rotation:
        lock_user_sessions(rotation, first_user)
        head = find_refresh_token(rotation, first["refresh_token"], for_update=True)
        assert rotate_refresh_token(rotation, head, first["refresh_token"], shared, utc_now()) == shared

        def rotate_other():
            result["response"] = client.post(
                "/auth/refresh",
                json={"refresh_token": other["refresh_token"], "next_refresh_token": shared},
            )

        racer = threading.Thread(target=rotate_other)
        racer.start()
        time.sleep(1.0)
        rotation.commit()
    racer.join(timeout=30)

    response = result["response"]
    assert response.status_code == 200, response.text
    assert response.json()["refresh_token"] != shared
    onward = client.post("/auth/refresh", json={"refresh_token": response.json()["refresh_token"]})
    assert onward.status_code == 200, onward.text


def test_successor_reference_is_indexed():
    indexes = inspect(engine).get_indexes("refresh_tokens")
    assert any(index["column_names"] == ["replaced_by_id"] for index in indexes)
