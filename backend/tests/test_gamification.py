"""Hearts, gems and the weekly leaderboard (each behind its own flag)."""
import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import Exercise, ExerciseAttempt, GemTransaction, PracticeAttempt, PracticeItem, UserGameState, UserStats
from app.services import gamification as g
from test_endless_practice import artifact, create_course_with_lexemes, import_templates

UTC = timezone.utc


@pytest.fixture
def flags(monkeypatch):
    settings = get_settings()
    for name in ("enable_hearts", "enable_gems", "enable_leaderboard"):
        monkeypatch.setattr(settings, name, True)
    return settings


def _first_lesson(client):
    course = client.get("/courses?source=en&target=fa").json()[0]
    unit = client.get(f"/courses/{course['id']}/units").json()[0]
    lesson = client.get(f"/units/{unit['id']}/lessons").json()[0]
    detail = client.get(f"/lessons/{lesson['id']}").json()
    return lesson["id"], detail["exercises"]


def _uid(client, auth):
    return client.get("/auth/me", headers=auth).json()["id"]


def _answer(client, auth, exercise_id, response):
    return client.post(f"/exercises/{exercise_id}/answer", headers=auth, json={"response": response})


def _new_user(client, name):
    email = f"gami-{os.urandom(4).hex()}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": "password123", "display_name": name})
    assert r.status_code == 201
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, decode_token(token)


# ------------------------------------------------------------ pure hearts math


def test_refill_math():
    t0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    h4 = timedelta(hours=4)
    assert g.refill_hearts(5, None, t0) == (5, None)
    # no time passed
    assert g.refill_hearts(2, t0, t0) == (2, t0)
    # just short of one interval
    assert g.refill_hearts(2, t0, t0 + h4 - timedelta(seconds=1)) == (2, t0)
    # exactly one interval, then 2.5 intervals keep the partial progress
    assert g.refill_hearts(2, t0, t0 + h4) == (3, t0 + h4)
    assert g.refill_hearts(2, t0, t0 + h4 * 2.5) == (4, t0 + h4 * 2)
    # capped at max, anchor cleared
    assert g.refill_hearts(0, t0, t0 + h4 * 50) == (5, None)
    # clock skew (anchor in the future) never adds hearts
    assert g.refill_hearts(1, t0 + h4, t0) == (1, t0 + h4)
    assert g.next_heart_at(3, t0) == t0 + h4
    assert g.next_heart_at(5, None) is None


def test_week_bounds_are_monday_utc():
    wed = datetime(2020, 3, 11, 15, 30, tzinfo=UTC)
    start, end = g.week_bounds(wed)
    assert start == datetime(2020, 3, 9, tzinfo=UTC) and end == datetime(2020, 3, 16, tzinfo=UTC)
    assert g.week_bounds(start)[0] == start
    assert g.week_bounds(end - timedelta(microseconds=1))[0] == start
    assert g.week_bounds(end)[0] == end
    # a non-UTC instant is converted first: Sun 23:30 in UTC-5 is Mon 04:30 UTC
    est = timezone(timedelta(hours=-5))
    assert g.week_bounds(datetime(2020, 3, 15, 23, 30, tzinfo=est))[0] == datetime(2020, 3, 9, tzinfo=UTC) + timedelta(days=7)


# --------------------------------------------------------------------- hearts


def test_flags_off_by_default_change_nothing(client, auth):
    lesson_id, exercises = _first_lesson(client)
    client.post(f"/lessons/{lesson_id}/start", headers=auth)
    for _ in range(7):
        r = _answer(client, auth, exercises[0]["id"], "zzzz-wrong")
        assert r.status_code == 200
        assert r.json()["hearts_remaining"] is None
    state = client.get("/me/gamification", headers=auth).json()
    assert state["hearts"]["enabled"] is False and state["hearts"]["hearts"] == 5
    assert client.post("/me/hearts/practice-restore", headers=auth).status_code == 404
    assert client.post("/me/gems/spend", headers=auth, json={"item": "heart_refill", "client_operation_id": "op-12345678"}).status_code == 404
    assert client.get("/leaderboard/weekly", headers=auth).status_code == 404


def test_wrong_answers_cost_hearts_then_block_new_lessons(client, auth, flags):
    lesson_id, exercises = _first_lesson(client)
    client.post(f"/lessons/{lesson_id}/start", headers=auth)
    for expected in (4, 3, 2, 1, 0):
        r = _answer(client, auth, exercises[0]["id"], "zzzz-wrong")
        assert r.status_code == 200, r.text
        assert r.json()["hearts_remaining"] == expected
    blocked = _answer(client, auth, exercises[0]["id"], "سلام")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "no_hearts"
    assert blocked.json()["error"]["next_heart_at"]
    state = client.get("/me/gamification", headers=auth).json()["hearts"]
    assert state["hearts"] == 0 and state["next_heart_at"]
    # still never negative / never blocks review endpoints
    uid = _uid(client, auth)
    with SessionLocal() as db:
        assert db.get(UserGameState, uid).hearts == 0


def test_lazy_refill_and_almost_is_free(client, auth, flags):
    lesson_id, exercises = _first_lesson(client)
    client.post(f"/lessons/{lesson_id}/start", headers=auth)
    uid = _uid(client, auth)
    _answer(client, auth, exercises[0]["id"], "zzzz-wrong")
    with SessionLocal() as db:
        st = db.get(UserGameState, uid)
        assert st.hearts == 4
        st.hearts = 0
        st.hearts_anchor_at = datetime.now(UTC) - timedelta(hours=9)  # 2 intervals + partial
        db.commit()
    state = client.get("/me/gamification", headers=auth).json()["hearts"]
    assert state["hearts"] == 2
    r = _answer(client, auth, exercises[0]["id"], "zzzz-wrong")
    assert r.json()["hearts_remaining"] == 1


def test_replay_of_correct_answer_and_completed_lessons_are_free(client, auth, flags):
    lesson_id, exercises = _first_lesson(client)
    client.post(f"/lessons/{lesson_id}/start", headers=auth)
    assert _answer(client, auth, exercises[0]["id"], "سلام").json()["correct"] is True
    # wrong answer on an already-correct exercise is a replay: free
    assert _answer(client, auth, exercises[0]["id"], "zzzz-wrong").status_code == 200
    assert client.get("/me/gamification", headers=auth).json()["hearts"]["hearts"] == 5
    assert client.post(f"/lessons/{lesson_id}/complete", headers=auth).status_code == 200
    # lesson completed: replaying it never costs hearts
    for _ in range(3):
        assert _answer(client, auth, exercises[1]["id"], "zzzz-wrong").json()["hearts_remaining"] is None
    assert client.get("/me/gamification", headers=auth).json()["hearts"]["hearts"] == 5


def test_practice_restore_needs_real_practice_and_is_not_farmable(client, auth, admin, flags):
    lesson_id, exercises = _first_lesson(client)
    client.post(f"/lessons/{lesson_id}/start", headers=auth)
    _answer(client, auth, exercises[0]["id"], "zzzz-wrong")
    r = client.post("/me/hearts/practice-restore", headers=auth).json()
    assert r["restored"] is False and r["reason"] == "not_enough_practice" and r["hearts"] == 4
    uid = _uid(client, auth)
    course_id, pr_lesson = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    client.post(f"/lessons/{pr_lesson}/start", headers=auth)
    with SessionLocal() as db:
        pe = db.scalar(select(Exercise).where(Exercise.lesson_id == pr_lesson).order_by(Exercise.order))
        pe_id, pe_resp = pe.id, pe.correct_response
    assert _answer(client, auth, pe_id, pe_resp).status_code == 200
    assert client.post(f"/lessons/{pr_lesson}/complete", headers=auth).status_code == 200
    batch = client.post(f"/practice/{course_id}/batch", headers=auth, json={"size": g.PRACTICE_RESTORE_MIN_ANSWERS}).json()
    ids = [i["id"] for i in batch["items"]]
    assert len(ids) >= g.PRACTICE_RESTORE_MIN_ANSWERS
    answers = {}
    with SessionLocal() as db:
        for item_id in ids:
            answers[item_id] = db.get(PracticeItem, item_id).correct_response
    # fewer than a session's worth is not enough
    for item_id in ids[: g.PRACTICE_RESTORE_MIN_ANSWERS - 1]:
        assert client.post(f"/practice/items/{item_id}/answer", headers=auth, json={"response": answers[item_id]}).status_code == 200
    assert client.post("/me/hearts/practice-restore", headers=auth).json()["reason"] == "not_enough_practice"
    last = ids[g.PRACTICE_RESTORE_MIN_ANSWERS - 1]
    assert client.post(f"/practice/items/{last}/answer", headers=auth, json={"response": answers[last]}).status_code == 200
    r = client.post("/me/hearts/practice-restore", headers=auth).json()
    assert r["restored"] is True and r["hearts"] == 5
    # full hearts: nothing consumed
    assert client.post("/me/hearts/practice-restore", headers=auth).json()["reason"] == "full"
    # lose one again; the same attempts cannot be re-used
    _answer(client, auth, exercises[0]["id"], "zzzz-wrong")
    r = client.post("/me/hearts/practice-restore", headers=auth).json()
    assert r["restored"] is False and r["reason"] == "not_enough_practice"


# ------------------------------------------------------------------------ gems


def test_lesson_gems_once_and_perfect_bonus(client, auth, flags):
    lesson_id, exercises = _first_lesson(client)
    client.post(f"/lessons/{lesson_id}/start", headers=auth)
    assert _answer(client, auth, exercises[0]["id"], "سلام").json()["correct"] is True
    first = client.post(f"/lessons/{lesson_id}/complete", headers=auth).json()
    assert first["gems_awarded"] == g.GEMS_LESSON_COMPLETE + g.GEMS_PERFECT_LESSON
    # retries / replays of the completion event cannot farm gems
    for _ in range(3):
        assert client.post(f"/lessons/{lesson_id}/complete", headers=auth).json()["gems_awarded"] == 0
    uid = _uid(client, auth)
    with SessionLocal() as db:
        rows = list(db.scalars(select(GemTransaction).where(GemTransaction.user_id == uid)))
        assert {r.kind for r in rows} == {"lesson_complete", "perfect_lesson"}
        assert db.get(UserGameState, uid).gem_balance == sum(r.amount for r in rows) == 10
    assert client.get("/me/gamification", headers=auth).json()["gems"]["balance"] == 10


def test_gems_flag_off_awards_nothing(client, auth):
    lesson_id, exercises = _first_lesson(client)
    client.post(f"/lessons/{lesson_id}/start", headers=auth)
    _answer(client, auth, exercises[0]["id"], "سلام")
    assert client.post(f"/lessons/{lesson_id}/complete", headers=auth).json()["gems_awarded"] == 0


def test_award_idempotent_per_key(client, auth, flags):
    uid = _uid(client, auth)
    with SessionLocal() as db:
        assert g.award_gems(db, uid, 7, "test", "k1") == 7
        assert g.award_gems(db, uid, 7, "test", "k1") == 0
        assert g.award_gems(db, uid, 3, "test", "k2") == 3
        db.commit()
        assert db.get(UserGameState, uid).gem_balance == 10
        assert db.scalar(select(func.sum(GemTransaction.amount)).where(GemTransaction.user_id == uid)) == 10


def test_streak_milestone_gems_once_per_day(client, auth, flags):
    uid = _uid(client, auth)
    today = datetime.now(UTC).date()
    with SessionLocal() as db:
        assert g.on_streak_advanced(db, uid, 7, today) == 10
        assert g.on_streak_advanced(db, uid, 7, today) == 0
        assert g.on_streak_advanced(db, uid, 8, today) == 0
        assert g.streak_milestone_gems(200) == g.GEMS_STREAK_EVERY_100


def _give_gems(uid, n):
    with SessionLocal() as db:
        g.award_gems(db, uid, n, "test", f"seed-{os.urandom(4).hex()}")
        db.commit()


def test_spend_heart_refill_idempotent_and_validated(client, auth, flags):
    uid = _uid(client, auth)
    lesson_id, exercises = _first_lesson(client)
    client.post(f"/lessons/{lesson_id}/start", headers=auth)
    body = {"item": "heart_refill", "client_operation_id": "op-heart-0001"}
    # full hearts: nothing to refill
    assert client.post("/me/gems/spend", headers=auth, json=body).json()["error"]["code"] == "hearts_full"
    for _ in range(3):
        _answer(client, auth, exercises[0]["id"], "zzzz-wrong")
    # not enough gems
    r = client.post("/me/gems/spend", headers=auth, json=body)
    assert r.status_code == 409 and r.json()["error"]["code"] == "insufficient_gems"
    _give_gems(uid, 25)
    r = client.post("/me/gems/spend", headers=auth, json=body)
    assert r.status_code == 200 and r.json() == {"applied": True, "item": "heart_refill", "cost": 10, "gem_balance": 15}
    assert client.get("/me/gamification", headers=auth).json()["hearts"]["hearts"] == 5
    # same operation id replayed: no second charge
    r = client.post("/me/gems/spend", headers=auth, json=body)
    assert r.json()["applied"] is False and r.json()["gem_balance"] == 15
    # validation
    bad = client.post("/me/gems/spend", headers=auth, json={"item": "money", "client_operation_id": "op-heart-0002"})
    assert bad.status_code == 422
    short = client.post("/me/gems/spend", headers=auth, json={"item": "heart_refill", "client_operation_id": "x"})
    assert short.status_code == 422
    with SessionLocal() as db:
        total = db.scalar(select(func.sum(GemTransaction.amount)).where(GemTransaction.user_id == uid))
        assert total == db.get(UserGameState, uid).gem_balance == 15


def test_spend_streak_freeze_and_cap(client, auth, flags):
    uid = _uid(client, auth)
    _give_gems(uid, 100)
    for n in range(g.MAX_STREAK_FREEZES):
        r = client.post("/me/gems/spend", headers=auth, json={"item": "streak_freeze", "client_operation_id": f"op-freeze-{n:04d}"})
        assert r.status_code == 200, r.text
    r = client.post("/me/gems/spend", headers=auth, json={"item": "streak_freeze", "client_operation_id": "op-freeze-9999"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "freeze_limit"
    with SessionLocal() as db:
        assert db.get(UserStats, uid).streak_freezes_available == g.MAX_STREAK_FREEZES
        assert db.get(UserGameState, uid).gem_balance == 100 - 2 * g.SPEND_COSTS["streak_freeze"]


def test_spend_rate_limited(client, auth, flags):
    codes = []
    for n in range(get_settings().spend_rate_limit_max + 2):
        r = client.post("/me/gems/spend", headers=auth, json={"item": "heart_refill", "client_operation_id": f"op-rate-{n:05d}"})
        codes.append(r.status_code)
    assert codes[-1] == 429


# ----------------------------------------------------------------- leaderboard


def _attempt(db, uid, exercise_id, xp, when):
    db.add(ExerciseAttempt(user_id=uid, exercise_id=exercise_id, response="x", correct=True, xp_awarded=xp, created_at=when))


def test_leaderboard_week_boundary_optout_and_privacy(client, flags):
    ha, ua = _new_user(client, "Alice")
    hb, ub = _new_user(client, "Bob")
    hc, uc = _new_user(client, "Cara")
    now = datetime(2020, 3, 11, 12, 0, tzinfo=UTC)  # Wednesday, week of Mar 9
    with SessionLocal() as db:
        ex = db.scalars(select(Exercise.id).limit(1)).first()
        # Alice: only boundary-straddling rows; counts 10 (Mon 00:00) + 5 (Sun 23:59:59)
        _attempt(db, ua, ex, 99, datetime(2020, 3, 8, 23, 59, 59, tzinfo=UTC))   # previous week
        _attempt(db, ua, ex, 10, datetime(2020, 3, 9, 0, 0, 0, tzinfo=UTC))      # first instant
        _attempt(db, ua, ex, 5, datetime(2020, 3, 15, 23, 59, 59, tzinfo=UTC))   # last instant
        _attempt(db, ua, ex, 99, datetime(2020, 3, 16, 0, 0, 0, tzinfo=UTC))     # next week
        _attempt(db, ub, ex, 40, datetime(2020, 3, 10, 9, 0, tzinfo=UTC))
        _attempt(db, uc, ex, 15, datetime(2020, 3, 12, 9, 0, tzinfo=UTC))
        db.commit()
        board = g.weekly_leaderboard(db, ua, now=now)
    assert [e["xp"] for e in board["entries"]] == [40, 15, 15]
    assert board["week_start"] == datetime(2020, 3, 9, tzinfo=UTC)
    by_name = {e["display_name"]: e for e in board["entries"]}
    assert by_name["Alice"]["xp"] == 15 and by_name["Bob"]["xp"] == 40
    # ties share a rank
    assert by_name["Alice"]["rank"] == by_name["Cara"]["rank"] == 2
    assert board["me"] == {"rank": 2, "xp": 15}
    # no emails or ids leak into entries
    for e in board["entries"]:
        assert set(e) == {"rank", "display_name", "xp", "is_me"}

    # Bob opts out via the endpoint: he disappears for everyone, and sees opted_out
    assert client.put("/me/leaderboard-privacy", headers=hb, json={"opted_out": True}).json() == {"opted_out": True}
    with SessionLocal() as db:
        board = g.weekly_leaderboard(db, ua, now=now)
        assert "Bob" not in [e["display_name"] for e in board["entries"]]
        assert board["me"]["rank"] == 1
        bob_view = g.weekly_leaderboard(db, ub, now=now)
        assert bob_view["opted_out"] is True and bob_view["me"] is None
    assert client.get("/me/gamification", headers=hb).json()["leaderboard"]["opted_out"] is True
    # opting back in restores him
    client.put("/me/leaderboard-privacy", headers=hb, json={"opted_out": False})
    with SessionLocal() as db:
        assert "Bob" in [e["display_name"] for e in g.weekly_leaderboard(db, ua, now=now)["entries"]]
    # live endpoint works (current week, may be empty of these users)
    live = client.get("/leaderboard/weekly", headers=hc)
    assert live.status_code == 200 and "entries" in live.json()
