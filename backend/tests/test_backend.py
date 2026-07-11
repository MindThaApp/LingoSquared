import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from sqlalchemy import delete, select
from app.db.session import SessionLocal
from app.models import Exercise, ReviewItem, TTSUsage
from app.schemas.api import ImportRequest
from app.content.service import import_content

def test_auth_register_login_me(client):
    body = {"email": "auth@example.com", "password": "password123", "display_name": "Auth"}
    response = client.post("/auth/register", json=body)
    assert response.status_code == 201 and response.json()["expires_in"] == 1800
    assert response.json()["refresh_token"]
    login = client.post("/auth/login", json={"email": body["email"], "password": body["password"]})
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert login.status_code == 200 and me.json()["email"] == body["email"]

def test_language_seed_and_rtl(client):
    rows = client.get("/languages").json()
    assert len(rows) == 14
    by_code = {item["code"]: item for item in rows}
    assert by_code["ar"]["name"] == "Arabic"
    assert by_code["ar"]["native_name"] == "العربية"
    assert by_code["ar"]["script"] == "arabic" and by_code["ar"]["direction"] == "rtl"
    assert by_code["fa"]["script"] == "arabic" and by_code["fa"]["direction"] == "rtl"
    assert by_code["prs"]["direction"] == "rtl"
    assert by_code["pl"]["script"] == "latin" and by_code["pl"]["direction"] == "ltr"
    assert by_code["ro"]["script"] == "latin" and by_code["ro"]["direction"] == "ltr"
    assert by_code["hi"]["script"] == "devanagari" and by_code["hi"]["direction"] == "ltr"

def payload(source="en", target="es", title="Test course"):
    direction = "rtl" if source in ("ar", "fa", "prs") else "ltr"
    return {"courses": [{"source_language": source, "target_language": target, "title": title, "units": [{"title": "Unit", "order": 1, "lessons": [{"title": "Lesson", "order": 1, "exercises": [{"type": "translation", "order": 1, "prompt": {"text_blocks": [{"text": "hello", "language_code": source, "direction": direction}]}, "correct_response": "answer"}]}]}]}]}

def test_all_core_ordered_pairs_constructible():
    codes = ["en", "nl", "fr", "de", "it", "es", "ru", "zh", "ar", "fa", "prs"]
    with SessionLocal() as db:
        for source in codes:
            for target in codes:
                if source != target:
                    data = ImportRequest.model_validate(payload(source, target, f"Pair {source}-{target}"))
                    count, errors, counters = import_content(db, data)
                    assert count == 1 and not errors
    assert sum(1 for a in codes for b in codes if a != b) == 110

def test_admin_import_course_and_queries(client, admin):
    response = client.post("/admin/content/import", headers=admin, json=payload(title="Imported course"))
    assert response.status_code == 200
    course = next(x for x in client.get("/courses?source=en&target=es").json() if x["title"] == "Imported course")
    units = client.get(f"/courses/{course['id']}/units").json()
    lessons = client.get(f"/units/{units[0]['id']}/lessons").json()
    detail = client.get(f"/lessons/{lessons[0]['id']}").json()
    assert "correct_response" not in detail["exercises"][0]

def test_course_units_include_per_user_completed_lesson_counts(client, admin, auth):
    title = f"Completion count course {os.urandom(4).hex()}"
    body = payload(title=title)
    body["courses"][0]["units"] = [
        {
            "title": "Unit one",
            "order": 1,
            "lessons": [
                {
                    "title": "Unit one lesson one",
                    "order": 1,
                    "exercises": [
                        {
                            "type": "translation",
                            "order": 1,
                            "prompt": {"text_blocks": [{"text": "hello", "language_code": "en", "direction": "ltr"}]},
                            "correct_response": "hola",
                        }
                    ],
                },
                {
                    "title": "Unit one lesson two",
                    "order": 2,
                    "exercises": [
                        {
                            "type": "translation",
                            "order": 1,
                            "prompt": {"text_blocks": [{"text": "goodbye", "language_code": "en", "direction": "ltr"}]},
                            "correct_response": "adios",
                        }
                    ],
                },
            ],
        },
        {
            "title": "Unit two",
            "order": 2,
            "lessons": [
                {
                    "title": "Unit two lesson one",
                    "order": 1,
                    "exercises": [
                        {
                            "type": "translation",
                            "order": 1,
                            "prompt": {"text_blocks": [{"text": "thanks", "language_code": "en", "direction": "ltr"}]},
                            "correct_response": "gracias",
                        }
                    ],
                }
            ],
        },
    ]
    response = client.post("/admin/content/import", headers=admin, json=body)
    assert response.status_code == 200
    course = next(x for x in client.get("/courses?source=en&target=es").json() if x["title"] == title)
    units_response = client.get(f"/courses/{course['id']}/units", headers=auth)
    assert units_response.status_code == 200
    units = units_response.json()
    first_unit, second_unit = units
    first_lessons = client.get(f"/units/{first_unit['id']}/lessons").json()

    assert client.post(f"/lessons/{first_lessons[0]['id']}/start", headers=auth).status_code == 200
    assert client.post(f"/lessons/{first_lessons[0]['id']}/complete", headers=auth).status_code == 200

    authenticated_response = client.get(f"/courses/{course['id']}/units", headers=auth)
    assert authenticated_response.status_code == 200
    authenticated_units = authenticated_response.json()
    assert authenticated_units[0]["lesson_count"] == 2
    assert authenticated_units[0]["completed_lesson_count"] == 1
    assert authenticated_units[1]["lesson_count"] == 1
    assert authenticated_units[1]["completed_lesson_count"] == 0

    anonymous_response = client.get(f"/courses/{course['id']}/units")
    assert anonymous_response.status_code == 200
    anonymous_units = anonymous_response.json()
    assert [unit["completed_lesson_count"] for unit in anonymous_units] == [0, 0]

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

def test_case_sensitive_german_sie_vs_capital_sie(client, admin, auth):
    # Real reported scenario, 2026-07-07: German's formal "Sie" (capital,
    # "you" formal) vs lowercase "sie" ("she"/"they") is a genuine
    # grammatical distinction with no equivalent in nl/en/fa/prs content
    # authored so far - the content lane authoring German deferred
    # teaching this specific contrast because it was ungradeable under
    # the always-casefold comparison. This simulates the minimal exercise
    # that distinction needs and confirms it now grades correctly both
    # ways once case_sensitive is opted in via feedback_meta (compiled
    # the same way scripts/compile_content.py's compile_feedback() now
    # emits it from an overlay's `case_sensitive: true` field).
    # Isolate the exact word-level distinction (not sentence-initial
    # capitalization, which is a separate, unrelated writing convention):
    # prompt asks for the formal "you", correct_response is bare "Sie".
    import json
    body = payload(source="en", target="de", title="German case-sensitive test")
    exercise = body["courses"][0]["units"][0]["lessons"][0]["exercises"][0]
    exercise["type"] = "translation"
    exercise["prompt"] = {
        "text_blocks": [
            {"text": "you (formal)", "language_code": "en", "direction": "ltr"}
        ]
    }
    exercise["correct_response"] = "Sie"
    exercise["feedback"] = json.dumps({"case_sensitive": True})
    assert client.post("/admin/content/import", headers=admin, json=body).status_code == 200

    course = next(
        c for c in client.get("/courses?source=en&target=de").json()
        if c["title"] == "German case-sensitive test"
    )
    unit = client.get(f"/courses/{course['id']}/units").json()[0]
    lesson = client.get(f"/units/{unit['id']}/lessons").json()[0]
    detail = client.get(f"/lessons/{lesson['id']}").json()
    exercise_id = detail["exercises"][0]["id"]

    correct = client.post(f"/exercises/{exercise_id}/answer", headers=auth, json={"response": "Sie"}).json()
    assert correct["result"] == "correct" and correct["correct"] is True

    # "sie" (lowercase - "she"/"they") must NOT be accepted as the formal
    # "Sie", and must not even earn "almost" (a bare distance-1 case
    # substitution) - that's the entire point of case_sensitive.
    wrong_case = client.post(f"/exercises/{exercise_id}/answer", headers=auth, json={"response": "sie"}).json()
    assert wrong_case["result"] == "incorrect" and wrong_case["correct"] is False


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
    monkeypatch.setattr(tts_service,"synthesize",lambda text,language_code,speaking_rate=1.0: calls.append(text) or b"audio")
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
        def provider_error(text,language_code,speaking_rate=1.0):
            with SessionLocal() as db:
                assert db.scalar(select(TTSUsage.characters))==len(text)
            raise RuntimeError("provider unavailable")
        monkeypatch.setattr(tts_service,"synthesize",provider_error)
        response=client.post("/tts",headers=auth,json={"text":"hello","language_code":"en"})
        assert response.json()=={"use_browser_tts":True,"reason":"provider_error"}
        with SessionLocal() as db: assert (db.scalar(select(TTSUsage.characters)) or 0)==0

        monkeypatch.setattr(tts_service,"synthesize",lambda text,language_code,speaking_rate=1.0: b"audio")
        response=client.post("/tts",headers=auth,json={"text":"hello","language_code":"en"})
        assert response.status_code==200 and response.headers["content-type"].startswith("audio/mpeg")
        with SessionLocal() as db: assert db.scalar(select(TTSUsage.characters))==5
    finally:
        settings.tts_monthly_char_budget=original_budget

def test_tts_monthly_reservation_concurrency_does_not_overspend(monkeypatch):
    from app.core.config import get_settings
    from app.services import tts as tts_service

    settings=get_settings(); original_budget=settings.tts_monthly_char_budget
    try:
        with SessionLocal() as db:
            db.execute(delete(TTSUsage))
            db.commit()
        settings.tts_monthly_char_budget=5

        def reserve_once():
            with SessionLocal() as db:
                return tts_service.reserve_characters(db,5)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results=list(executor.map(lambda _: reserve_once(), range(2)))

        assert sorted(results)==[False,True]
        with SessionLocal() as db:
            assert db.scalar(select(TTSUsage.characters))==5
    finally:
        settings.tts_monthly_char_budget=original_budget
        with SessionLocal() as db:
            db.execute(delete(TTSUsage))
            db.commit()

def test_tts_refund_preserves_other_committed_reservations(monkeypatch):
    from app.core.config import get_settings
    from app.services import tts as tts_service

    settings=get_settings(); original_budget=settings.tts_monthly_char_budget
    try:
        with SessionLocal() as db:
            db.execute(delete(TTSUsage))
            db.commit()
        settings.tts_monthly_char_budget=20

        with SessionLocal() as first_db:
            assert tts_service.reserve_characters(first_db,5)
            with SessionLocal() as second_db:
                assert tts_service.reserve_characters(second_db,5)
            tts_service.refund_characters(first_db,5)

        with SessionLocal() as db:
            assert db.scalar(select(TTSUsage.characters))==5
    finally:
        settings.tts_monthly_char_budget=original_budget
        with SessionLocal() as db:
            db.execute(delete(TTSUsage))
            db.commit()

def test_tts_routes_farsi_to_azure_and_covered_languages_to_google(client, auth, monkeypatch):
    from app.services import tts as tts_service
    calls=[]
    monkeypatch.setattr(tts_service,"synthesize_azure",lambda text,language_code,speaking_rate=1.0: calls.append(("azure",language_code)) or b"azure-audio")
    monkeypatch.setattr(tts_service,"synthesize_google",lambda text,language_code,speaking_rate=1.0: calls.append(("google",language_code)) or b"google-audio")

    response=client.post("/tts",headers=auth,json={"text":"سلام","language_code":"fa"})
    assert response.status_code==200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.content==b"azure-audio"

    response=client.post("/tts",headers=auth,json={"text":"hello","language_code":"en"})
    assert response.status_code==200
    assert response.content==b"google-audio"

    response=client.post("/tts",headers=auth,json={"text":"مرحبا","language_code":"ar"})
    assert response.status_code==200
    assert response.content==b"google-audio"

    # prs still has no provider at all (neither Google nor Azure) — must
    # still fall back to the browser, never attempt either provider.
    response=client.post("/tts",headers=auth,json={"text":"سلام","language_code":"prs"})
    assert response.json()=={"use_browser_tts":True,"reason":"unsupported_language"}

    assert calls==[("azure","fa"),("google","en"),("google","ar")]

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

def test_tts_speaking_rate_forwarded_and_defaults_to_normal(client, auth, monkeypatch):
    # Added 2026-07-07 for the per-language TTS speed setting: /tts must
    # forward speaking_rate through to tts_service.synthesize() unchanged
    # when the caller sends one, and default to 1.0 (normal speed) when
    # the field is omitted entirely (old clients / no preference set).
    from app.services import tts as tts_service
    calls=[]
    monkeypatch.setattr(tts_service,"synthesize",lambda text,language_code,speaking_rate=1.0: calls.append(speaking_rate) or b"audio")

    response=client.post("/tts",headers=auth,json={"text":"hallo","language_code":"nl","speaking_rate":0.8})
    assert response.status_code==200 and response.headers["content-type"].startswith("audio/mpeg")

    response=client.post("/tts",headers=auth,json={"text":"hello","language_code":"en"})
    assert response.status_code==200

    assert calls==[0.8,1.0]

def test_tts_speaking_rate_out_of_range_rejected(client, auth):
    # Matches google-cloud-texttospeech's own AudioConfig.speaking_rate
    # bound ([0.25, 2.0]) — validated before ever reaching a provider call.
    response=client.post("/tts",headers=auth,json={"text":"hello","language_code":"en","speaking_rate":3.0})
    assert response.status_code==422 and response.json()["error"]["code"]=="validation_error"

    response=client.post("/tts",headers=auth,json={"text":"hello","language_code":"en","speaking_rate":0.1})
    assert response.status_code==422 and response.json()["error"]["code"]=="validation_error"

def test_synthesize_google_passes_speaking_rate_to_audio_config(monkeypatch):
    from app.services import tts as tts_service
    from app.core.config import get_settings
    settings=get_settings()
    original=settings.google_cloud_tts_credentials_json
    try:
        settings.google_cloud_tts_credentials_json='{"type":"service_account"}'
        monkeypatch.setattr(
            tts_service.service_account.Credentials,"from_service_account_info",
            classmethod(lambda cls,info: object()),
        )
        captured={}
        class FakeResponse:
            audio_content=b"google-mp3"
        class FakeClient:
            def __init__(self,credentials=None): pass
            def synthesize_speech(self,input,voice,audio_config):
                captured["speaking_rate"]=audio_config.speaking_rate
                captured["language_code"]=voice.language_code
                captured["voice_name"]=voice.name
                return FakeResponse()
        monkeypatch.setattr(tts_service.texttospeech,"TextToSpeechClient",FakeClient)

        audio=tts_service.synthesize_google("مرحبا","ar",speaking_rate=0.8)

        assert audio==b"google-mp3"
        assert captured["speaking_rate"]==0.8
        assert captured["language_code"]=="ar-XA"
        assert captured["voice_name"]=="ar-XA-Wavenet-D"
    finally:
        settings.google_cloud_tts_credentials_json=original

def test_synthesize_azure_wraps_text_in_prosody_rate(monkeypatch):
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

        audio=tts_service.synthesize_azure("سلام","fa",speaking_rate=0.8)

        assert audio==b"mp3-bytes"
        ssml=calls[1][1]["content"].decode()
        assert "<prosody rate='-20%'>" in ssml
        assert "سلام" in ssml

        # Default rate (1.0) still wraps in prosody, just a no-op percentage —
        # one code path regardless of whether a custom rate was requested.
        calls.clear()
        tts_service.synthesize_azure("سلام","fa")
        assert "<prosody rate='+0%'>" in calls[1][1]["content"].decode()
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

def test_speaking_lock_cannot_be_bypassed_via_answer_or_complete(client, auth):
    # Phase H1 (2026-07-07 integrity audit): start() always checked
    # speaking_locked, but exercise_answer()/complete() didn't -- a user
    # could skip start() entirely, answer every exercise in a locked
    # speaking lesson directly by id (earning XP), then complete it. This
    # is a FRESH account (unlike test_speaking_units_lock_and_unlock's
    # `auth` fixture user, which may have already unlocked speaking from
    # a prior test in the same module-scoped course/content) to guarantee
    # speaking is genuinely still locked here.
    register = client.post("/auth/register", json={"email": "bypass-check@example.com", "password": "password123"})
    fresh_auth = {"Authorization": f"Bearer {register.json()['access_token']}"}
    course = client.get("/courses?source=en&target=fa").json()[0]
    units = client.get(f"/courses/{course['id']}/units", headers=fresh_auth).json()
    speaking = next(unit for unit in units if unit["section"] == "speaking")
    assert speaking["locked"] is True
    speaking_lesson = client.get(f"/units/{speaking['id']}/lessons").json()[0]
    lesson_detail = client.get(f"/lessons/{speaking_lesson['id']}").json()
    exercise_id = lesson_detail["exercises"][0]["id"]

    answer_bypass = client.post(f"/exercises/{exercise_id}/answer", headers=fresh_auth, json={"response": "anything"})
    assert answer_bypass.status_code == 409 and answer_bypass.json()["error"]["code"] == "speaking_locked"
    # Confirm the fix didn't just move the hole: answer() must not have
    # created a LessonProgress row as a side effect of the blocked attempt
    # either (the pre-fix bug's OWN mechanism was exercise_answer()
    # auto-creating this row with no lock check).
    from app.models import LessonProgress, User
    with SessionLocal() as db:
        user_row = db.scalar(select(User).where(User.email == "bypass-check@example.com"))
        assert db.scalar(select(LessonProgress).where(LessonProgress.user_id == user_row.id, LessonProgress.lesson_id == speaking_lesson["id"])) is None

        # complete() independently checking the lock (not just relying on
        # "no LessonProgress row exists yet") is the other half of H1 --
        # simulate a LessonProgress row existing by whatever means (this
        # is exactly the scenario Fable's audit described: "complete()
        # only requires that a LessonProgress row exists") and confirm
        # complete() itself still blocks on the lock, not just on row
        # presence.
        db.add(LessonProgress(user_id=user_row.id, lesson_id=speaking_lesson["id"], started_at=datetime.now(timezone.utc), completed_at=None, correct_count=0, answer_count=0, xp_earned=0))
        db.commit()
    complete_bypass = client.post(f"/lessons/{speaking_lesson['id']}/complete", headers=fresh_auth)
    assert complete_bypass.status_code == 409 and complete_bypass.json()["error"]["code"] == "speaking_locked"
