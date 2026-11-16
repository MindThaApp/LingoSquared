"""Launch-readiness data safety: deletion coverage, export coverage/limit,
unreviewable_at self-heal.

The structural tests fail when someone adds a table with a user foreign key
without deciding how account deletion and the data export treat it.
"""
import os
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.security import decode_token
from app.db.session import Base, SessionLocal
from app.models import (
    Lexeme,
    PasswordResetToken,
    PushNotificationGuard,
    QuestCompletion,
    ReviewEvent,
    User,
    UserLexemeSRS,
)
import app.models  # noqa: F401
from app.services.unreviewable import UNREVIEWABLE_RETRY_DAYS
from test_phase_a_srs import user_id
from test_unreviewable_srs import _prepare_review_course, _srs_for_token

# Tables whose rows are removed by DELETE /me through ON DELETE CASCADE from
# users (every user-FK table must be CASCADE or be listed in
# EXPLICIT_PRE_DELETE below). Adding a new user-FK table does not require
# touching this list, but it does require the FK to cascade.
# Tables that reference a user-owned table with RESTRICT, so
# delete_user_account must remove them explicitly BEFORE the user row.
EXPLICIT_PRE_DELETE = {"practice_attempts", "content_issue_reports"}

# user-FK table -> export key that carries it, or None with a reason.
EXPORT_COVERAGE = {
    "user_identities": "identities",
    "password_reset_tokens": None,  # security material, not personal data
    "refresh_tokens": None,  # session material, revoked/deleted with account
    "user_lexeme_srs": "lexeme_srs",
    "practice_items": None,  # prompts exported through practice_attempts
    "practice_attempts": "practice_attempts",
    "checkpoint_attempts": "checkpoint_attempts",
    "lesson_progress": "lesson_progress",
    "exercise_attempts": "exercise_attempts",
    "user_stats": "stats",
    "quest_completions": "quest_completions",
    "user_game_state": "game_state",
    "gem_transactions": "gem_transactions",
    "push_notification_guards": None,  # internal send de-dup guard
    "push_subscriptions": "push_subscriptions",
    "review_items": "review_items",
    "review_events": "review_events",
    "user_achievements": "achievements",
    "skill_progress": "skill_progress",
    "vocabulary_progress": "vocabulary_progress",
    "grammar_progress": "grammar_progress",
    "content_issue_reports": "content_issue_reports",
}


def _user_fk_tables():
    found = {}
    for table in Base.metadata.sorted_tables:
        for fk in table.foreign_keys:
            if fk.column.table.name == "users":
                found[table.name] = fk
    return found


def test_every_user_fk_table_cascades_on_account_delete():
    for name, fk in _user_fk_tables().items():
        assert (fk.ondelete or "").upper() == "CASCADE", (
            f"{name}.{fk.parent.name} references users without ON DELETE "
            "CASCADE: DELETE /me would fail or leave user data behind. Make "
            "it CASCADE or delete it explicitly in delete_user_account."
        )


def test_no_restrict_reference_into_user_owned_tables_is_unhandled():
    owned = set(_user_fk_tables())
    for table in Base.metadata.sorted_tables:
        for fk in table.foreign_keys:
            target = fk.column.table.name
            if target in owned and target != "users":
                if (fk.ondelete or "").upper() in ("", "RESTRICT", "NO ACTION"):
                    assert table.name in EXPLICIT_PRE_DELETE, (
                        f"{table.name}.{fk.parent.name} blocks deletion of "
                        f"{target} rows; delete it in delete_user_account "
                        "and add it to EXPLICIT_PRE_DELETE."
                    )


def test_every_user_fk_table_has_export_decision():
    tables = set(_user_fk_tables())
    assert tables == set(EXPORT_COVERAGE), (
        "user-FK tables changed; decide export coverage. "
        f"missing={tables - set(EXPORT_COVERAGE)} stale={set(EXPORT_COVERAGE) - tables}"
    )


def test_export_includes_every_declared_key(client, auth):
    data = client.get("/me/export", headers=auth).json()
    for table, key in EXPORT_COVERAGE.items():
        if key:
            assert key in data, f"export missing {key} (table {table})"


def test_delete_covers_remaining_user_tables_and_spares_other_users(client, auth):
    uid = user_id(auth)
    other = client.post(
        "/auth/register",
        json={"email": f"other-{os.urandom(4).hex()}@example.com", "password": "password123", "display_name": "Other"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    other_id = user_id(other_headers)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        for owner in (uid, other_id):
            db.add(PasswordResetToken(user_id=owner, token_sha256=os.urandom(32).hex(), expires_at=now + timedelta(hours=1)))
            db.add(PushNotificationGuard(user_id=owner, trigger_code="daily_reminder", local_date=date.today()))
            db.add(QuestCompletion(user_id=owner, quest_code="q", date=date.today()))
            db.add(ReviewEvent(
                user_id=owner, source="review", reviewed_at=now, result="good", quality=4,
                correct=True, previous_interval_days=0, new_interval_days=1,
                previous_ease=2.5, new_ease=2.5, new_due_at=now,
            ))
        db.commit()

    assert client.delete("/me", headers=auth).status_code == 204

    with SessionLocal() as db:
        for model in (PasswordResetToken, PushNotificationGuard, QuestCompletion, ReviewEvent):
            assert db.scalar(select(func.count()).select_from(model).where(model.user_id == uid)) == 0
            assert db.scalar(select(func.count()).select_from(model).where(model.user_id == other_id)) == 1, (
                f"{model.__name__}: other user's rows must survive"
            )
        assert db.get(User, other_id) is not None


def test_export_is_rate_limited_per_user(client, auth):
    codes = [client.get("/me/export", headers=auth).status_code for _ in range(6)]
    assert codes[:5] == [200] * 5
    assert codes[5] == 429
    # A different account is unaffected.
    other = client.post(
        "/auth/register",
        json={"email": f"rl-{os.urandom(4).hex()}@example.com", "password": "password123", "display_name": "RL"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert client.get("/me/export", headers=other_headers).status_code == 200


def test_export_includes_review_events_identities_and_unreviewable(client, auth):
    uid = user_id(auth)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        db.add(ReviewEvent(
            user_id=uid, source="review", reviewed_at=now, result="good", quality=4,
            correct=True, previous_interval_days=0, new_interval_days=1,
            previous_ease=2.5, new_ease=2.5, new_due_at=now,
        ))
        db.commit()
    data = client.get("/me/export", headers=auth).json()
    assert len(data["review_events"]) == 1
    assert data["review_events"][0]["result"] == "good"
    assert data["identities"] == []


def test_stale_unreviewable_flag_self_heals_on_due_count(client, admin, auth):
    course_id, uid = _prepare_review_course(client, admin, auth)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        for row in db.scalars(select(UserLexemeSRS).where(UserLexemeSRS.user_id == uid)):
            row.due_at = now + timedelta(days=30)
        fresh = _srs_for_token(db, uid, course_id, "derecha")
        fresh.due_at = now - timedelta(minutes=1)
        fresh.unreviewable_at = now - timedelta(days=UNREVIEWABLE_RETRY_DAYS - 1)
        db.commit()
    assert client.get("/me/reviews/due", headers=auth).json()["due_count"] == 0
    with SessionLocal() as db:
        assert _srs_for_token(db, uid, course_id, "derecha").unreviewable_at is not None
        stale_due = _srs_for_token(db, uid, course_id, "derecha").due_at
        _srs_for_token(db, uid, course_id, "derecha").unreviewable_at = now - timedelta(days=UNREVIEWABLE_RETRY_DAYS + 1)
        db.commit()
    assert client.get("/me/reviews/due", headers=auth).json()["due_count"] == 1
    with SessionLocal() as db:
        row = _srs_for_token(db, uid, course_id, "derecha")
        assert row.unreviewable_at is None
        assert row.due_at == stale_due  # schedule untouched


def test_stale_flag_is_reflagged_if_still_ungeneratable(client, admin, auth):
    course_id, uid = _prepare_review_course(client, admin, auth)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        for row in db.scalars(select(UserLexemeSRS).where(UserLexemeSRS.user_id == uid)):
            row.due_at = now + timedelta(days=30)
        target = _srs_for_token(db, uid, course_id, "derecha")
        target.due_at = now - timedelta(minutes=1)
        target.unreviewable_at = now - timedelta(days=UNREVIEWABLE_RETRY_DAYS + 1)
        db.commit()
    resp = client.post("/reviews/session", headers=auth, json={"course_id": course_id, "size": 1})
    assert resp.status_code == 200, resp.text
    with SessionLocal() as db:
        flagged = _srs_for_token(db, uid, course_id, "derecha").unreviewable_at
        assert flagged is not None and flagged > now - timedelta(minutes=5)
