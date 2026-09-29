from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import Course, PushNotificationGuard, User, UserStats
from app.services.push_scheduler import claim_notification, in_local_window
from app.services.quests import selected_quest_definitions
from app.content.service import import_content
from app.schemas.api import ImportRequest
from test_seed_idempotency import course_payload


def _register(client):
    response = client.post("/auth/register", json={
        "email": f"retention-{uuid4()}@example.com",
        "password": "password123",
    })
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return decode_token(token), {"Authorization": f"Bearer {token}"}


def test_daily_goal_is_per_user_and_validated(client):
    user_id, auth = _register(client)
    assert client.get("/me/daily-goal", headers=auth).json() == {"daily_goal_xp": 20}
    changed = client.put("/me/daily-goal", headers=auth, json={"daily_goal_xp": 30})
    assert changed.status_code == 200
    assert changed.json() == {"daily_goal_xp": 30}
    assert client.get("/me/xp", headers=auth).json()["daily_goal"] == 30
    invalid = client.put("/me/daily-goal", headers=auth, json={"daily_goal_xp": 25})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"

    _, second_auth = _register(client)
    assert client.get("/me/daily-goal", headers=second_auth).json() == {"daily_goal_xp": 20}


def test_course_list_returns_importable_recommended_flag(client):
    title = f"Recommended import {uuid4()}"
    imported = course_payload(title)
    imported["recommended"] = True
    with SessionLocal() as db:
        count, errors, _ = import_content(
            db, ImportRequest.model_validate({"courses": [imported]})
        )
        assert count == 1, errors
        course = db.scalar(select(Course).where(Course.title == title))
        assert course.recommended is True
        course_id = course.id
        source, target = course.source_language, course.target_language
    listed = client.get(f"/courses?source={source}&target={target}")
    assert listed.status_code == 200
    item = next(course for course in listed.json() if course["id"] == course_id)
    assert item["recommended"] is True

    # Old compiled payloads omit the field; omission must leave the flag as-is.
    legacy_payload = course_payload(title)
    with SessionLocal() as db:
        _, errors, _ = import_content(
            db, ImportRequest.model_validate({"courses": [legacy_payload]})
        )
        assert errors == []
        assert db.get(Course, course_id).recommended is True


def test_quest_selection_is_stable_and_varies_by_user_or_date():
    today = date(2026, 9, 29)
    selection = selected_quest_definitions("user-one", today)
    assert len(selection) == 3
    assert selection == selected_quest_definitions("user-one", today)
    other_user = selected_quest_definitions("user-two", today)
    other_day = selected_quest_definitions("user-one", date(2026, 9, 30))
    assert selection != other_user or selection != other_day


def test_get_quests_without_learning_does_not_award_xp(client):
    user_id, auth = _register(client)
    with SessionLocal() as db:
        before = db.get(UserStats, user_id).total_xp
    response = client.get("/me/quests", headers=auth)
    assert response.status_code == 200
    assert len(response.json()["quests"]) == 3
    with SessionLocal() as db:
        assert db.get(UserStats, user_id).total_xp == before


def test_daily_goal_controls_goal_quest_target(client, monkeypatch):
    _, auth = _register(client)
    client.put("/me/daily-goal", headers=auth, json={"daily_goal_xp": 30})
    from app.services import quests as quest_service
    selected = tuple(
        definition for definition in quest_service.QUEST_DEFINITIONS
        if definition["code"] in {"earn_daily_goal", "complete_lesson", "practice_correct_5"}
    )
    monkeypatch.setattr(quest_service, "selected_quest_definitions", lambda _uid, _date: selected)
    response = client.get("/me/quests", headers=auth)
    goal_quest = next(q for q in response.json()["quests"] if q["code"] == "earn_daily_goal")
    assert goal_quest["target"] == 30


def test_push_windows_use_each_users_local_timezone():
    instant = datetime(2026, 9, 29, 18, 15, tzinfo=timezone.utc)
    assert in_local_window("Europe/London", instant, 19, 20) is True
    assert in_local_window("Pacific/Kiritimati", instant, 19, 20) is False
    assert in_local_window("America/Los_Angeles", instant, 11, 12) is True
    assert in_local_window("America/Los_Angeles", instant, 12, 13) is False


def test_push_guard_claims_user_trigger_date_once():
    user_id = str(uuid4())
    with SessionLocal() as db:
        db.add(User(id=user_id, email=f"push-guard-{user_id}@example.com", display_name="", is_admin=False))
        db.commit()
    try:
        with SessionLocal() as db:
            assert claim_notification(db, user_id, "daily_reminder", date(2026, 9, 29)) is True
            assert claim_notification(db, user_id, "daily_reminder", date(2026, 9, 29)) is False
            assert claim_notification(db, user_id, "streak_at_risk", date(2026, 9, 29)) is True
            count = db.scalar(select(func.count(PushNotificationGuard.id)).where(
                PushNotificationGuard.user_id == user_id,
            ))
            assert count == 2
    finally:
        with SessionLocal() as db:
            user = db.get(User, user_id)
            if user:
                db.delete(user)
                db.commit()
