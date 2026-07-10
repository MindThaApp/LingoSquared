"""GET /me/xp's xp_today field: XP earned within the user's own local
day, summed live from the persisted per-answer rows (ExerciseAttempt +
PracticeAttempt + today's QuestCompletion rewards). daily_goal was a
dead column before this — nothing ever computed "earned today" against
it."""
from datetime import timedelta

from sqlalchemy import select

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import ExerciseAttempt


def _xp(client, auth):
    response = client.get("/me/xp", headers=auth)
    assert response.status_code == 200, response.text
    return response.json()


def test_xp_today_counts_only_todays_awards(client, auth):
    # Fresh account: the goal is present and nothing is earned yet.
    fresh = _xp(client, auth)
    assert fresh["daily_goal"] == 20
    assert fresh["xp_today"] == 0
    assert fresh["total_xp"] == 0

    # Earn real XP through the real answer endpoint (never a DB
    # shortcut — see the standing footgun about faked lesson state).
    course = client.get("/courses?source=en&target=fa").json()[0]
    unit = client.get(f"/courses/{course['id']}/units").json()[0]
    lesson = client.get(f"/units/{unit['id']}/lessons").json()[0]
    detail = client.get(f"/lessons/{lesson['id']}").json()
    assert client.post(f"/lessons/{lesson['id']}/start", headers=auth).status_code == 200
    answer = client.post(
        f"/exercises/{detail['exercises'][0]['id']}/answer",
        headers=auth,
        json={"response": "سلام"},
    ).json()
    assert answer["correct"] and answer["xp_awarded"] == 10

    after_answer = _xp(client, auth)
    assert after_answer["xp_today"] == 10
    assert after_answer["total_xp"] == 10

    # Quest rewards move total_xp today, so they must show up in
    # xp_today too: completing the lesson and then fetching /me/quests
    # awards the complete_lesson quest exactly once.
    assert client.post(f"/lessons/{lesson['id']}/complete", headers=auth).status_code == 200
    quests = {
        quest["code"]: quest
        for quest in client.get("/me/quests", headers=auth).json()["quests"]
    }
    assert quests["complete_lesson"]["completed"] is True
    quest_xp = sum(
        quest["xp_reward"] for quest in quests.values() if quest["completed"]
    )
    assert quest_xp >= 10

    after_quest = _xp(client, auth)
    assert after_quest["xp_today"] == 10 + quest_xp
    assert after_quest["total_xp"] == 10 + quest_xp

    # Backdate the exercise attempt: XP from a previous day must fall
    # out of xp_today while total_xp (a lifetime counter) is untouched.
    # (Backdating a timestamp is the only way to simulate "yesterday" in
    # a test; the XP itself was still earned through the real endpoint.)
    user_id = decode_token(auth["Authorization"].split()[1])
    with SessionLocal() as db:
        attempt = db.scalar(
            select(ExerciseAttempt).where(ExerciseAttempt.user_id == user_id)
        )
        attempt.created_at = attempt.created_at - timedelta(days=3)
        db.commit()

    backdated = _xp(client, auth)
    assert backdated["xp_today"] == quest_xp
    assert backdated["total_xp"] == 10 + quest_xp
