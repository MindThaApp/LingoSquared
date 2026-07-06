from datetime import datetime, timezone
from sqlalchemy import delete, select
from app.db.session import SessionLocal
from app.models import Exercise, ReviewItem, TTSUsage
from app.schemas.api import ImportRequest
from app.content.service import import_content

def test_auth_register_login_me(client):
    body = {"email": "auth@example.com", "password": "password123", "display_name": "Auth"}
    response = client.post("/auth/register", json=body)
    assert response.status_code == 201 and response.json()["expires_in"] == 86400
    login = client.post("/auth/login", json={"email": body["email"], "password": body["password"]})
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert login.status_code == 200 and me.json()["email"] == body["email"]

def test_language_seed_and_rtl(client):
    rows = client.get("/languages").json()
    assert len(rows) == 10
    by_code = {item["code"]: item for item in rows}
    assert by_code["fa"]["script"] == "arabic" and by_code["fa"]["direction"] == "rtl"
    assert by_code["prs"]["direction"] == "rtl"

def payload(source="en", target="es", title="Test course"):
    direction = "rtl" if source in ("fa", "prs") else "ltr"
    return {"courses": [{"source_language": source, "target_language": target, "title": title, "units": [{"title": "Unit", "order": 1, "lessons": [{"title": "Lesson", "order": 1, "exercises": [{"type": "translation", "order": 1, "prompt": {"text_blocks": [{"text": "hello", "language_code": source, "direction": direction}]}, "correct_response": "answer"}]}]}]}]}

def test_all_90_ordered_pairs_constructible():
    codes = ["en", "nl", "fr", "de", "it", "es", "ru", "zh", "fa", "prs"]
    with SessionLocal() as db:
        for source in codes:
            for target in codes:
                if source != target:
                    data = ImportRequest.model_validate(payload(source, target, f"Pair {source}-{target}"))
                    count, errors, counters = import_content(db, data)
                    assert count == 1 and not errors
    assert sum(1 for a in codes for b in codes if a != b) == 90

def test_admin_import_course_and_queries(client, admin):
    response = client.post("/admin/content/import", headers=admin, json=payload(title="Imported course"))
    assert response.status_code == 200
    course = next(x for x in client.get("/courses?source=en&target=es").json() if x["title"] == "Imported course")
    units = client.get(f"/courses/{course['id']}/units").json()
    lessons = client.get(f"/units/{units[0]['id']}/lessons").json()
    detail = client.get(f"/lessons/{lessons[0]['id']}").json()
    assert "correct_response" not in detail["exercises"][0]

def test_lesson_answer_xp_streak_review(client, auth):
    course = client.get("/courses?source=en&target=fa").json()[0]
    unit = client.get(f"/courses/{course['id']}/units").json()[0]
    lesson = client.get(f"/units/{unit['id']}/lessons").json()[0]
    detail = client.get(f"/lessons/{lesson['id']}").json()
    assert client.post(f"/lessons/{lesson['id']}/start", headers=auth).status_code == 200
    result = client.post(f"/exercises/{detail['exercises'][0]['id']}/answer", headers=auth, json={"response": "سلام"}).json()
    assert result["correct"] and result["xp_awarded"] == 10
    assert client.get("/me/xp", headers=auth).json()["total_xp"] == 10
    assert client.get("/me/streak", headers=auth).json()["streak_days"] == 1
    done = client.post(f"/lessons/{lesson['id']}/complete", headers=auth).json()
    assert done["accuracy"] == 1
    second_lesson = client.get(f"/units/{unit['id']}/lessons").json()[1]
    second_detail = client.get(f"/lessons/{second_lesson['id']}").json()
    flashcard = next(item for item in second_detail["exercises"] if item["type"] == "flashcard")
    assert flashcard["prompt"]["back_text_blocks"] == [{"text": "goodbye", "language_code": "en", "direction": "ltr"}]
    known = client.post(f"/exercises/{flashcard['id']}/answer", headers=auth, json={"response": "known"})
    unknown = client.post(f"/exercises/{flashcard['id']}/answer", headers=auth, json={"response": "unknown"})
    invalid = client.post(f"/exercises/{flashcard['id']}/answer", headers=auth, json={"response": "goodbye"})
    assert known.json()["correct"] is True and known.json()["xp_awarded"] == 10
    assert unknown.json()["correct"] is False and unknown.json()["xp_awarded"] == 0
    assert invalid.status_code == 422 and invalid.json()["error"]["code"] == "invalid_flashcard_response"

def test_review_schedule_update(client, auth):
    from app.core.security import decode_token
    with SessionLocal() as db:
        user_id = decode_token(auth["Authorization"].split()[1])
        exercise = db.scalar(select(Exercise))
        review = ReviewItem(user_id=user_id, exercise_id=exercise.id, due_at=datetime.now(timezone.utc))
        db.add(review); db.commit(); review_id = review.id
    due = client.get("/me/reviews", headers=auth).json()
    assert any(item["id"] == review_id for item in due["items"])
    result = client.post(f"/reviews/{review_id}/answer", headers=auth, json={"response": "wrong"}).json()
    assert "next_due_at" in result

def test_content_validation(client, admin):
    bad = payload()
    bad["courses"][0]["units"][0]["lessons"][0]["exercises"][0]["prompt"]["text_blocks"][0]["direction"] = "rtl"
    response = client.post("/admin/content/validate", headers=admin, json={"content": bad})
    assert response.status_code == 200 and not response.json()["valid"]
    flashcard = payload(title="Invalid flashcard")
    flashcard["courses"][0]["units"][0]["lessons"][0]["exercises"][0]["type"] = "flashcard"
    response = client.post("/admin/content/validate", headers=admin, json={"content": flashcard})
    assert response.status_code == 200 and not response.json()["valid"]
    assert any("back_text_blocks" in error for error in response.json()["errors"])

def test_farsi_dari_distinct_courses(client, admin):
    assert client.post("/admin/content/import", headers=admin, json=payload("fa", "en", "Farsi to English")).status_code == 200
    assert client.post("/admin/content/import", headers=admin, json=payload("prs", "en", "Dari to English")).status_code == 200
    assert client.get("/courses?source=fa&target=en").json()[0]["id"] != client.get("/courses?source=prs&target=en").json()[0]["id"]

def test_seeded_dari_lessons_include_teaching(client):
    for source,target in (("en","prs"),("prs","en")):
        courses=client.get(f"/courses?source={source}&target={target}").json()
        seeded=next(course for course in courses if "Foundations" in course["title"])
        unit=client.get(f"/courses/{seeded['id']}/units").json()[0]
        lesson=client.get(f"/units/{unit['id']}/lessons").json()[0]
        detail=client.get(f"/lessons/{lesson['id']}").json()
        assert detail["teaching"]
        assert all(card["text_blocks"] for card in detail["teaching"])
        assert {block["language_code"] for block in detail["teaching"][0]["text_blocks"]}=={source,target}

def test_dari_pair_returns_a1_and_a2_courses(client, admin):
    courses=client.get("/courses?source=en&target=prs").json()
    seeded={course["title"]:course["level"] for course in courses if course["title"] in {"Dari Foundations","Dari Elementary"}}
    assert seeded=={"Dari Foundations":"A1","Dari Elementary":"A2"}
    assert [course["level"] for course in courses]==sorted(course["level"] for course in courses)

    invalid=payload("en","prs","Invalid level")
    invalid["courses"][0]["level"]="beginner"
    response=client.post("/admin/content/import",headers=admin,json=invalid)
    assert response.status_code==422 and response.json()["error"]["code"]=="validation_error"

def test_error_shape(client):
    response = client.get("/courses/not-real")
    assert response.status_code == 404 and set(response.json()) == {"error"}

def test_tts_fallbacks(client, auth, monkeypatch):
    from app.core.config import get_settings
    from app.services import tts as tts_service
    calls=[]
    monkeypatch.setattr(tts_service,"synthesize",lambda text,language_code: calls.append(text) or b"audio")
    # prs still has zero coverage from any provider (Google or Azure) and
    # must still hit the unsupported-language fallback. fa is covered now
    # (Azure) — see test_tts_routes_farsi_to_azure_and_covered_languages_to_google
    # for its dedicated routing coverage.
    response=client.post("/tts",headers=auth,json={"text":"سلام","language_code":"prs"})
    assert response.status_code==200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()=={"use_browser_tts":True,"reason":"unsupported_language"}
    assert calls==[]

    settings=get_settings(); original_budget=settings.tts_monthly_char_budget
    try:
        settings.tts_monthly_char_budget=2
        response=client.post("/tts",headers=auth,json={"text":"hello","language_code":"en"})
        assert response.json()=={"use_browser_tts":True,"reason":"quota_exceeded"}
        assert calls==[]

        with SessionLocal() as db: db.execute(delete(TTSUsage)); db.commit()
        settings.tts_monthly_char_budget=100
        def provider_error(text,language_code): raise RuntimeError("provider unavailable")
        monkeypatch.setattr(tts_service,"synthesize",provider_error)
        response=client.post("/tts",headers=auth,json={"text":"hello","language_code":"en"})
        assert response.json()=={"use_browser_tts":True,"reason":"provider_error"}
        with SessionLocal() as db: assert (db.scalar(select(TTSUsage.characters)) or 0)==0

        monkeypatch.setattr(tts_service,"synthesize",lambda text,language_code: b"audio")
        response=client.post("/tts",headers=auth,json={"text":"hello","language_code":"en"})
        assert response.status_code==200 and response.headers["content-type"].startswith("audio/mpeg")
        with SessionLocal() as db: assert db.scalar(select(TTSUsage.characters))==5
    finally:
        settings.tts_monthly_char_budget=original_budget

def test_tts_routes_farsi_to_azure_and_covered_languages_to_google(client, auth, monkeypatch):
    from app.services import tts as tts_service
    calls=[]
    monkeypatch.setattr(tts_service,"synthesize_azure",lambda text,language_code: calls.append(("azure",language_code)) or b"azure-audio")
    monkeypatch.setattr(tts_service,"synthesize_google",lambda text,language_code: calls.append(("google",language_code)) or b"google-audio")

    response=client.post("/tts",headers=auth,json={"text":"سلام","language_code":"fa"})
    assert response.status_code==200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.content==b"azure-audio"

    response=client.post("/tts",headers=auth,json={"text":"hello","language_code":"en"})
    assert response.status_code==200
    assert response.content==b"google-audio"

    # prs still has no provider at all (neither Google nor Azure) — must
    # still fall back to the browser, never attempt either provider.
    response=client.post("/tts",headers=auth,json={"text":"سلام","language_code":"prs"})
    assert response.json()=={"use_browser_tts":True,"reason":"unsupported_language"}

    assert calls==[("azure","fa"),("google","en")]

def test_tts_azure_missing_key_falls_back_to_browser(client, auth):
    # Default settings ship with no Azure credentials configured at all
    # (matching the existing Google-credential-missing convention) —
    # synthesize_azure() must raise, and the /tts route must catch it and
    # degrade to the browser fallback rather than a 500.
    from app.core.config import get_settings
    settings=get_settings()
    assert not settings.azure_speech_key and not settings.azure_speech_region
    response=client.post("/tts",headers=auth,json={"text":"سلام","language_code":"fa"})
    assert response.status_code==200
    assert response.json()=={"use_browser_tts":True,"reason":"provider_error"}

def test_synthesize_azure_builds_expected_request(monkeypatch):
    from app.services import tts as tts_service
    from app.core.config import get_settings
    settings=get_settings()
    original_key,original_region=settings.azure_speech_key,settings.azure_speech_region
    try:
        settings.azure_speech_key="test-key"
        settings.azure_speech_region="eastus"
        calls=[]
        class FakeResponse:
            def __init__(self,content=b"",text=""): self.content=content; self.text=text
            def raise_for_status(self): pass
        def fake_post(url,**kwargs):
            calls.append((url,kwargs))
            if url.endswith("/sts/v1.0/issueToken"): return FakeResponse(text="fake-token")
            return FakeResponse(content=b"mp3-bytes")
        monkeypatch.setattr(tts_service.httpx,"post",fake_post)

        audio=tts_service.synthesize_azure("سلام","fa")

        assert audio==b"mp3-bytes"
        assert calls[0][0]=="https://eastus.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        assert calls[0][1]["headers"]["Ocp-Apim-Subscription-Key"]=="test-key"
        assert calls[1][0]=="https://eastus.tts.speech.microsoft.com/cognitiveservices/v1"
        assert calls[1][1]["headers"]["Authorization"]=="Bearer fake-token"
        assert "fa-IR-DilaraNeural" in calls[1][1]["content"].decode()
        assert "fa-IR" in calls[1][1]["content"].decode()
    finally:
        settings.azure_speech_key=original_key
        settings.azure_speech_region=original_region

def test_synthesize_azure_missing_credentials_raises(monkeypatch):
    from app.services import tts as tts_service
    from app.core.config import get_settings
    settings=get_settings()
    original_key,original_region=settings.azure_speech_key,settings.azure_speech_region
    try:
        settings.azure_speech_key=""
        settings.azure_speech_region=""
        try:
            tts_service.synthesize_azure("hello","fa")
            assert False,"expected RuntimeError"
        except RuntimeError:
            pass
    finally:
        settings.azure_speech_key=original_key
        settings.azure_speech_region=original_region

def test_speaking_units_lock_and_unlock(client, auth):
    course=client.get("/courses?source=en&target=fa").json()[0]
    units=client.get(f"/courses/{course['id']}/units",headers=auth).json()
    reading=[unit for unit in units if unit["section"]=="reading_writing"]
    speaking=next(unit for unit in units if unit["section"]=="speaking")
    assert reading and all(not unit["locked"] for unit in reading) and speaking["locked"]
    speaking_lesson=client.get(f"/units/{speaking['id']}/lessons").json()[0]
    blocked=client.post(f"/lessons/{speaking_lesson['id']}/start",headers=auth)
    assert blocked.status_code==409 and blocked.json()["error"]["code"]=="speaking_locked"

    for unit in reading:
        for lesson in client.get(f"/units/{unit['id']}/lessons").json():
            assert client.post(f"/lessons/{lesson['id']}/start",headers=auth).status_code==200
            assert client.post(f"/lessons/{lesson['id']}/complete",headers=auth).status_code==200
    refreshed=client.get(f"/courses/{course['id']}/units",headers=auth).json()
    assert next(unit for unit in refreshed if unit["section"]=="speaking")["locked"] is False
    assert client.post(f"/lessons/{speaking_lesson['id']}/start",headers=auth).status_code==200
