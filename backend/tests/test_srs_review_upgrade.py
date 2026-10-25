from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import PracticeItem, ReviewEvent, User, UserLexemeSRS
from app.review.sm2 import (
    LEECH_THRESHOLD,
    due_at_for,
    fuzz_factor,
    fuzzed_days,
    schedule,
    study_day,
)
from test_endless_practice import artifact, create_course_with_lexemes, import_templates
from test_phase_a_srs import complete_via_api, user_id

NOW = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)


def item(**kw):
    base = dict(
        repetitions=3, interval_days=10, ease_factor=2.5, mastery=0.4,
        due_at=None, last_reviewed_at=None, lapses=0, leech=False,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_fuzz_is_deterministic_bounded_and_skips_short_intervals():
    day = date(2026, 3, 10)
    assert fuzz_factor("a", day) == fuzz_factor("a", day)
    assert fuzz_factor("a", day) != fuzz_factor("a", date(2026, 3, 11))
    for k in range(200):
        assert abs(fuzz_factor(f"k{k}", day)) <= 0.05
    assert fuzzed_days(7, "a", day) == 7
    assert fuzzed_days(100, None, day) == 100
    spread = {fuzzed_days(100, f"k{k}", day) for k in range(200)}
    assert min(spread) >= 95 and max(spread) <= 105 and len(spread) > 5


def test_schedule_fuzzes_due_but_keeps_stored_interval_exact():
    a = schedule(item(), "correct", now=NOW, fuzz_key="a")
    b = schedule(item(), "correct", now=NOW, fuzz_key="a")
    assert a.interval_days == 25 and a.due_at == b.due_at
    plain = schedule(item(), "correct", now=NOW)
    assert abs((a.due_at - plain.due_at).days) <= 2


def test_due_aligns_to_0400_local_day():
    tz = "Asia/Tehran"  # UTC+3:30
    due = due_at_for(NOW, 3, tz)
    local = due.astimezone(ZoneInfo(tz))
    assert (local.hour, local.minute) == (4, 0)
    assert local.date() == date(2026, 3, 13)
    utc_due = due_at_for(NOW, 3, None)
    assert utc_due == datetime(2026, 3, 13, 4, 0, tzinfo=timezone.utc)
    assert due_at_for(NOW, 3, "Not/AZone") == utc_due


def test_study_day_rolls_over_at_four_local():
    late = datetime(2026, 3, 10, 22, 30, tzinfo=timezone.utc)  # 01:00 Mar 11 in Tehran
    assert study_day(late, "Asia/Tehran") == date(2026, 3, 10)
    assert study_day(late, None) == date(2026, 3, 10)
    assert study_day(datetime(2026, 3, 11, 5, 0, tzinfo=timezone.utc), None) == date(2026, 3, 11)


def test_schedule_uses_user_timezone():
    it = schedule(item(), "correct", now=NOW, tz="Europe/Amsterdam")
    local = it.due_at.astimezone(ZoneInfo("Europe/Amsterdam"))
    assert (local.hour, local.minute) == (4, 0)


def test_leech_flag_after_threshold_lapses_and_item_kept():
    it = item(lapses=LEECH_THRESHOLD - 2)
    schedule(it, "incorrect", now=NOW)
    assert it.lapses == LEECH_THRESHOLD - 1 and it.leech is False
    schedule(it, "incorrect", now=NOW)
    assert it.lapses == LEECH_THRESHOLD and it.leech is True
    assert it.interval_days >= 1 and it.due_at > NOW
    schedule(it, "correct", now=NOW)
    assert it.leech is True  # sticky until the learner clears it
    assert it.lapses == LEECH_THRESHOLD


def test_success_does_not_count_a_lapse_and_almost_is_success():
    it = item()
    schedule(it, "almost", now=NOW)
    assert it.lapses == 0


def test_self_grade_mapping():
    again = schedule(item(), "correct", now=NOW, self_grade="again")
    assert again.lapses == 1 and again.interval_days == 3  # lapse softening kept
    hard = schedule(item(), "correct", now=NOW, self_grade="hard")
    good = schedule(item(), "correct", now=NOW, self_grade="good")
    easy = schedule(item(), "correct", now=NOW, self_grade="easy")
    assert hard.interval_days == 12
    assert hard.interval_days < good.interval_days < easy.interval_days
    assert hard.ease_factor < good.ease_factor < easy.ease_factor
    assert easy.last_schedule["self_grade"] == "easy"


def _review_item(client, admin, auth):
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)
    uid = user_id(auth)
    with SessionLocal() as db:
        srs = db.scalar(select(UserLexemeSRS).where(
            UserLexemeSRS.user_id == uid, UserLexemeSRS.course_id == course_id))
        srs.due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        lexeme_id = srs.lexeme_id
        db.commit()
    session = client.post("/reviews/session", headers=auth,
                          json={"course_id": course_id, "size": 1})
    assert session.status_code == 200, session.text
    return uid, course_id, lexeme_id, session.json()["items"][0]["id"]


def test_review_answer_writes_event_and_returns_next_due(client, admin, auth):
    uid, course_id, lexeme_id, item_id = _review_item(client, admin, auth)
    with SessionLocal() as db:
        correct = db.get(PracticeItem, item_id).correct_response
    res = client.post(f"/practice/items/{item_id}/answer", headers=auth,
                      json={"response": correct, "latency_ms": 2345})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["next_interval_days"] >= 1 and body["next_due_at"]
    with SessionLocal() as db:
        events = list(db.scalars(select(ReviewEvent).where(ReviewEvent.user_id == uid)))
        assert len(events) == 1
        ev = events[0]
        assert ev.lexeme_id == lexeme_id and ev.course_id == course_id
        assert ev.source == "review" and ev.correct is True
        assert ev.latency_ms == 2345 and ev.new_interval_days == body["next_interval_days"]
        assert ev.previous_due_at is not None


def test_wrong_review_logs_lapse_and_increments_counter(client, admin, auth):
    uid, _, lexeme_id, item_id = _review_item(client, admin, auth)
    client.post(f"/practice/items/{item_id}/answer", headers=auth,
                json={"response": "__wrong__"})
    with SessionLocal() as db:
        ev = db.scalar(select(ReviewEvent).where(ReviewEvent.user_id == uid))
        assert ev.correct is False and ev.result == "incorrect" and ev.quality == 2
        srs = db.scalar(select(UserLexemeSRS).where(
            UserLexemeSRS.user_id == uid, UserLexemeSRS.lexeme_id == lexeme_id))
        assert srs.lapses == 1 and srs.leech is False


def test_forecast_and_leeches_endpoints(client, admin, auth):
    uid, course_id, lexeme_id, _ = _review_item(client, admin, auth)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        total = list(db.scalars(select(UserLexemeSRS).where(UserLexemeSRS.user_id == uid)))
        for s in total:
            s.due_at = now + timedelta(days=30)
        target = next(s for s in total if s.lexeme_id == lexeme_id)
        target.due_at = now - timedelta(hours=1)
        target.lapses = LEECH_THRESHOLD
        target.leech = True
        if len(total) > 1:
            total[1 if total[0] is target else 0].due_at = now + timedelta(days=1, hours=6)
        db.commit()
    f = client.get("/me/reviews/forecast", headers=auth)
    assert f.status_code == 200, f.text
    j = f.json()
    assert j["today"] >= 1 and set(j) == {"today", "tomorrow", "this_week"}
    assert j["tomorrow"] + j["this_week"] <= len(total)
    leeches = client.get("/me/reviews/leeches", headers=auth).json()
    assert leeches["threshold"] == LEECH_THRESHOLD
    assert [x["lexeme_id"] for x in leeches["items"]] == [lexeme_id]
    assert leeches["items"][0]["lapses"] == LEECH_THRESHOLD
    assert client.get("/me/reviews/forecast").status_code == 401


def test_self_grade_on_non_flashcard_is_ignored(client, admin, auth):
    uid, _, _, item_id = _review_item(client, admin, auth)
    res = client.post(f"/practice/items/{item_id}/answer", headers=auth,
                      json={"response": "__wrong__", "self_grade": "easy"})
    assert res.status_code == 200 and res.json()["correct"] is False
