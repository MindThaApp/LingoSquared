"""Romanized input is almost-right, NOT correct: the answer endpoints record no correct count,
no XP and no SRS scheduling for it, show the (localizable) nudge with the script answer, and
let the learner retry in script, which then earns normal credit."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import (
    Exercise, ExerciseAttempt, Lesson, PracticeAttempt, PracticeItem, PracticeTemplate,
    ReviewEvent, ReviewItem, UserStats,
)
from app.review.translit_nudge import NUDGE_CODE, NUDGE_MESSAGE
from test_endless_practice import create_course_with_lexemes


def _user_id(auth):
    return decode_token(auth["Authorization"].split()[1])


def _exercise():
    _, lesson_id = create_course_with_lexemes()
    with SessionLocal() as db:
        order = (db.scalar(select(func.max(Exercise.order)).where(Exercise.lesson_id == lesson_id)) or 0) + 1
        e = Exercise(
            lesson_id=lesson_id, type="translation", order=order, xp=10,
            prompt={"answer_language_code": "ru", "text_blocks": []},
            correct_response="Привет",
        )
        db.add(e)
        db.commit()
        return e.id


def test_exercise_answer_romanized_is_almost_but_not_correct_then_script_retry_earns_credit(client, auth):
    ex = _exercise()
    r = client.post(f"/exercises/{ex}/answer", headers=auth, json={"response": "privet"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["result"] == "almost" and body["correct"] is False
    assert body["xp_awarded"] == 0
    assert body["correct_response"] == "Привет"
    assert body["feedback"] == NUDGE_MESSAGE and body["feedback_code"] == NUDGE_CODE
    uid = _user_id(auth)
    with SessionLocal() as db:
        att = db.scalar(select(ExerciseAttempt).where(ExerciseAttempt.user_id == uid))
        assert att.correct is False and att.xp_awarded == 0 and att.outcome == "almost"
    # retry in script: normal correct credit, not treated as a replay of a prior correct answer
    r2 = client.post(f"/exercises/{ex}/answer", headers=auth, json={"response": "Привет"})
    b2 = r2.json()
    assert b2["result"] == "correct" and b2["correct"] is True and b2["xp_awarded"] == 10
    assert b2["feedback_code"] is None


def test_regular_almost_still_counts_correct(client, auth):
    _, lesson_id = create_course_with_lexemes()
    with SessionLocal() as db:
        order = (db.scalar(select(func.max(Exercise.order)).where(Exercise.lesson_id == lesson_id)) or 0) + 1
        e = Exercise(lesson_id=lesson_id, type="translation", order=order, xp=10,
                     prompt={"answer_language_code": "en"}, correct_response="gracias")
        db.add(e)
        db.commit()
        ex = e.id
    body = client.post(f"/exercises/{ex}/answer", headers=auth, json={"response": "gracis"}).json()
    assert body["result"] == "almost" and body["correct"] is True and body["xp_awarded"] == 10
    assert body["feedback_code"] is None


def test_review_answer_romanized_writes_nothing(client, auth):
    ex = _exercise()
    uid = _user_id(auth)
    due = datetime.now(timezone.utc) + timedelta(days=2)
    with SessionLocal() as db:
        item = ReviewItem(user_id=uid, exercise_id=ex, interval_days=0, ease_factor=2.3, repetitions=0, due_at=due)
        db.add(item)
        db.commit()
        rid = item.id
        xp_before = db.get(UserStats, uid).total_xp if db.get(UserStats, uid) else 0
    r = client.post(f"/reviews/{rid}/answer", headers=auth, json={"response": "privet"})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["result"] == "almost" and b["correct"] is False and b["xp_awarded"] == 0
    assert b["feedback_code"] == NUDGE_CODE and b["correct_response"] == "Привет"
    with SessionLocal() as db:
        item = db.get(ReviewItem, rid)
        assert item.repetitions == 0 and item.stability is None and item.due_at == due
        assert db.scalar(select(func.count(ReviewEvent.id)).where(ReviewEvent.user_id == uid)) == 0
        stats = db.get(UserStats, uid)
        assert (stats.total_xp if stats else 0) == xp_before
    # a script answer afterwards is graded and scheduled normally
    b2 = client.post(f"/reviews/{rid}/answer", headers=auth, json={"response": "Привет"}).json()
    assert b2["result"] == "correct" and b2["correct"] is True and b2["xp_awarded"] == 10


def test_practice_answer_romanized_writes_nothing_and_can_retry(client, auth):
    uid = _user_id(auth)
    course_id, lesson_id = create_course_with_lexemes()
    with SessionLocal() as db:
        t = PracticeTemplate(
            course_id=course_id, content_key=f"translit-{uuid4()}", provenance_lesson_id=lesson_id,
            type="translation", frame={}, slots={}, slot_relations=[], answer_derivation={},
            feedback_frame={}, active=True,
        )
        db.add(t)
        db.flush()
        item = PracticeItem(
            user_id=uid, course_id=course_id, template_id=t.id, filled_slots={},
            prompt={"answer_language_code": "ru", "text_blocks": []}, correct_response="Привет",
            xp_value=5, source="practice", expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add(item)
        db.commit()
        iid = item.id
    r = client.post(f"/practice/items/{iid}/answer", headers=auth, json={"response": "privet"})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["result"] == "almost" and b["correct"] is False and b["xp_awarded"] == 0
    assert b["feedback_code"] == NUDGE_CODE and b["correct_response"] == "Привет"
    with SessionLocal() as db:
        assert db.get(PracticeItem, iid).answered_at is None
        assert db.scalar(select(func.count(PracticeAttempt.id)).where(PracticeAttempt.practice_item_id == iid)) == 0
    b2 = client.post(f"/practice/items/{iid}/answer", headers=auth, json={"response": "Привет"}).json()
    assert b2["result"] == "correct" and b2["correct"] is True and b2["xp_awarded"] == 5


def test_attach_prompt_translit_rules(monkeypatch):
    from app.review import translit_nudge as tn

    entries = {"Привет": "privet", "Спасибо": "spasibo", "Пока": "poka"}
    monkeypatch.setattr(tn, "_load", lambda lang: (entries, frozenset({"Пока"})))
    prompt = {
        "text_blocks": [
            {"text": "Say hello", "language_code": "en", "direction": "ltr"},
            {"text": "Привет", "language_code": "ru", "direction": "ltr"},
            {"text": "Спасибо", "language_code": "ru", "direction": "ltr"},
        ],
        "options": ["Привет", "Пока", "Неизвестно"],
    }
    tn.attach_prompt_translit(prompt, "Привет", "ru", "multiple_choice")
    b = prompt["text_blocks"]
    assert "translit" not in b[0]                                   # learner language untouched
    assert "translit" not in b[1]                                   # equals the answer: would leak
    assert b[2]["translit"] == "spasibo" and b[2]["translit_reviewed"] is False
    assert prompt["translit_map"] == {"Привет": "privet", "Пока": "poka"}
    assert prompt["translit_reviewed_list"] == ["Пока"]
    # listening prompts never get block romanization
    listen = {"text_blocks": [{"text": "Спасибо", "language_code": "ru", "direction": "ltr"}]}
    tn.attach_prompt_translit(listen, "Привет", "ru", "listen_type")
    assert "translit" not in listen["text_blocks"][0]
    # languages without a store are untouched
    other = {"text_blocks": [{"text": "Hola", "language_code": "es", "direction": "ltr"}]}
    tn.attach_prompt_translit(other, "Hola", "es", "translation")
    assert "translit" not in other["text_blocks"][0] and "translit_map" not in other


def test_correct_answer_translit_rules(monkeypatch):
    from app.review import translit_nudge as tn

    monkeypatch.setattr(tn, "_load", lambda lang: ({"Привет": "privet"}, frozenset()))
    assert tn.correct_answer_translit("Привет", "ru") == "privet"
    assert tn.correct_answer_translit({"canonical": "Привет", "accepted": ["Привет"]}, "ru") == "privet"
    assert tn.correct_answer_translit("privet", "ru") is None      # Latin answer (romanize_*): nothing to add
    assert tn.correct_answer_translit("Привет", "es") is None
    assert tn.correct_answer_translit("С", "ru") is None           # letter drills


def test_answer_endpoint_returns_correct_answer_translit(client, auth):
    ex = _exercise()
    b = client.post(f"/exercises/{ex}/answer", headers=auth, json={"response": "Пока"}).json()
    assert b["result"] == "incorrect" and b["correct_response_translit"].lower() == "privet"


def test_romanized_lesson_attempt_creates_no_review_item_but_wrong_answer_does(client, auth):
    ex = _exercise()
    uid = _user_id(auth)
    client.post(f"/exercises/{ex}/answer", headers=auth, json={"response": "privet"})
    with SessionLocal() as db:
        assert db.scalar(select(func.count(ReviewItem.id)).where(ReviewItem.user_id == uid)) == 0
    client.post(f"/exercises/{ex}/answer", headers=auth, json={"response": "Пока"})
    with SessionLocal() as db:
        assert db.scalar(select(func.count(ReviewItem.id)).where(ReviewItem.user_id == uid)) == 1


def test_prompt_translit_skips_letter_and_romanize_drills(monkeypatch):
    from app.review import translit_nudge as tn

    monkeypatch.setattr(tn, "_load", lambda lang: ({"Привет": "privet", "А": "a"}, frozenset()))
    p = {"text_blocks": [], "options": ["Привет", "А"]}
    tn.attach_prompt_translit(p, "Пока", "ru", "multiple_choice", "ru.a1.letters.q1")
    assert "translit_map" not in p
    p = {"text_blocks": [], "options": ["Привет", "А"]}
    tn.attach_prompt_translit(p, "Пока", "ru", "multiple_choice", "ru.a1.vocab.q1")
    assert p["translit_map"] == {"Привет": "privet"}  # one-letter option never romanized
