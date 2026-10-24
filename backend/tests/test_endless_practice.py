from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete, func, select

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import (
    Course,
    Exercise,
    Lesson,
    LessonProgress,
    Lexeme,
    PracticeAttempt,
    PracticeItem,
    PracticeTemplate,
    ReviewItem,
    Unit,
    UserLexemeSRS,
)
from app.schemas.api import ImportRequest
from app.content.service import import_content


LESSON_KEY = "test.practice.lesson.001"


def user_id(auth):
    return decode_token(auth["Authorization"].split()[1])


def create_course_with_lexemes(source="en", target="es"):
    title = f"Practice test {uuid4()}"
    payload = {
        "courses": [
            {
                "source_language": source,
                "target_language": target,
                "title": title,
                "units": [
                    {
                        "title": "Unit",
                        "order": 1,
                        "lessons": [
                            {
                                "title": "Lesson",
                                "order": 1,
                                "exercises": [
                                    {
                                        "type": "translation",
                                        "order": 1,
                                        "prompt": {
                                            "text_blocks": [
                                                {
                                                    "text": "test",
                                                    "language_code": source,
                                                    "direction": (
                                                        "rtl"
                                                        if source in {"fa", "prs"}
                                                        else "ltr"
                                                    ),
                                                }
                                            ]
                                        },
                                        "correct_response": "test",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }
    with SessionLocal() as db:
        count, errors, counters = import_content(db, ImportRequest.model_validate(payload))
        assert count == 1 and not errors
        course = db.scalar(select(Course).where(Course.title == title))
        lesson = db.scalar(
            select(Lesson).join(Unit).where(Unit.course_id == course.id)
        )
        tokens = (
            [("uno", "one"), ("dos", "two"), ("tres", "three"), ("cuatro", "four")]
            if target == "es"
            else [("یک", "one"), ("دو", "two"), ("سه", "three"), ("چهار", "four")]
        )
        for index, (token, gloss) in enumerate(tokens):
            db.add(
                Lexeme(
                    course_id=course.id,
                    token=token,
                    language_code=target,
                    part_of_speech="noun",
                    english_gloss=gloss,
                    agreement_tags={"semantic": "word"},
                    provenance_lesson_id=lesson.id,
                    provenance_lesson_content_key=LESSON_KEY,
                    provenance_content_key=f"test.lexeme.{index}",
                )
            )
        db.add(
            Lexeme(
                course_id=course.id,
                token="derecha" if target == "es" else "راست",
                language_code=target,
                part_of_speech="adverb",
                english_gloss="right",
                agreement_tags={"semantic": "direction"},
                provenance_lesson_id=lesson.id,
                provenance_lesson_content_key=LESSON_KEY,
                provenance_content_key="test.lexeme.unrelated",
            )
        )
        for index, (token, gloss) in enumerate(
            [
                ("buenos días", "good morning"),
                ("buenas tardes", "good afternoon"),
                ("buenas noches", "good evening"),
            ]
        ):
            if target != "es":
                break
            db.add(
                Lexeme(
                    course_id=course.id,
                    token=token,
                    language_code=target,
                    part_of_speech="phrase",
                    english_gloss=gloss,
                    agreement_tags={"semantic": "good_wish"},
                    provenance_lesson_id=lesson.id,
                    provenance_lesson_content_key=LESSON_KEY,
                    provenance_content_key=f"test.lexeme.good_wish.{index}",
                )
            )
        db.commit()
        return course.id, lesson.id


def add_extra_word_lexemes(course_id, lesson_id, target="es", count=12):
    with SessionLocal() as db:
        existing = db.scalar(
            select(func.count(Lexeme.id)).where(
                Lexeme.course_id == course_id,
                Lexeme.language_code == target,
                Lexeme.part_of_speech == "noun",
            )
        )
        for offset in range(count):
            index = existing + offset
            db.add(
                Lexeme(
                    course_id=course_id,
                    token=f"palabra{index}",
                    language_code=target,
                    part_of_speech="noun",
                    english_gloss=f"word {index}",
                    agreement_tags={"semantic": "word"},
                    provenance_lesson_id=lesson_id,
                    provenance_lesson_content_key=LESSON_KEY,
                    provenance_content_key=f"test.lexeme.extra.{index}",
                )
            )
        db.commit()


def artifact(target="es", include_listen=True):
    direction = "rtl" if target in {"fa", "prs"} else "ltr"
    slot = {
        "language_code": target,
        "part_of_speech": "noun",
        "agreement_tags": {"semantic": "word"},
    }
    templates = [
        {
            "content_key": "test.practice.multiple_choice",
            "lesson_content_key": LESSON_KEY,
            "type": "multiple_choice",
            "frame": {"text": "{word}", "language_code": target, "direction": direction},
            "slots": {"word": slot},
            "answer_derivation": {"kind": "slot_gloss", "slot": "word"},
            "feedback_frame": {"text": "Correct.", "language_code": "en", "direction": "ltr"},
        },
        {
            "content_key": "test.practice.fill_in_blank",
            "lesson_content_key": LESSON_KEY,
            "type": "fill_in_blank",
            # Deliberately NOT just "{word}" alone (see
            # blank_only_fill_in_blank_artifact() below for that shape) -
            # a frame whose entire visible text is the one slot being
            # blanked out renders as a bare "___" with zero context, the
            # real live bug found 2026-07-05. Real templates always have
            # surrounding literal text; this fixture now matches that.
            "frame": {"text": "note: {word}", "language_code": target, "direction": direction},
            "slots": {"word": slot},
            "answer_derivation": {"kind": "slot_text", "slot": "word"},
            "feedback_frame": {"text": "Correct.", "language_code": "en", "direction": "ltr"},
        },
        {
            "content_key": "test.practice.translation",
            "lesson_content_key": LESSON_KEY,
            "type": "translation",
            "frame": {"text": "{word}", "language_code": "en", "direction": "ltr", "slot_rendering": {"word": "english_gloss"}},
            "slots": {"word": slot},
            "answer_derivation": {"kind": "slot_text", "slot": "word"},
            "feedback_frame": {"text": "Correct.", "language_code": "en", "direction": "ltr"},
        },
        {
            "content_key": "test.practice.word_order",
            "lesson_content_key": LESSON_KEY,
            "type": "word_order",
            "frame": {"text": "{word} ahora", "language_code": target, "direction": direction},
            "slots": {"word": slot},
            "answer_derivation": {"kind": "render_frame", "frame": {"text": "{word} ahora", "language_code": target, "direction": direction}},
            "feedback_frame": {"text": "Correct.", "language_code": "en", "direction": "ltr"},
        },
        {
            "content_key": "test.practice.matching_pairs",
            "lesson_content_key": LESSON_KEY,
            "type": "matching_pairs",
            "frame": {"text": "{first}, {second}", "language_code": target, "direction": direction},
            "slots": {"first": slot, "second": slot},
            "slot_relations": [{"kind": "distinct", "slots": ["first", "second"]}],
            "answer_derivation": {"kind": "matching_pairs", "slots": ["first", "second"]},
            "feedback_frame": {"text": "Correct.", "language_code": "en", "direction": "ltr"},
        },
    ]
    if include_listen:
        templates.append(
            {
                "content_key": "test.practice.listen_select",
                "lesson_content_key": LESSON_KEY,
                "type": "listen_select",
                "frame": {"text": "{word}", "language_code": target, "direction": direction},
                "slots": {"word": slot},
                "answer_derivation": {"kind": "slot_gloss", "slot": "word"},
                "feedback_frame": {"text": "Correct.", "language_code": "en", "direction": "ltr"},
            }
        )
    return {
        "artifact_type": "lingosquared.practice_templates",
        "artifact_version": 1,
        "source_language": "en",
        "target_language": target,
        "packs": [
            {
                "pack_key": "test.practice.pack",
                "unit_content_key": "test.practice.unit",
                "tag_schema": {},
                "templates": templates,
            }
        ],
    }


def undersized_options_artifact():
    body = artifact()
    templates = body["packs"][0]["templates"]
    selected = [
        template
        for template in templates
        if template["type"] in {"multiple_choice", "listen_select"}
    ]
    for template in selected:
        template["content_key"] += ".undersized"
        template["slots"]["word"] = {
            "language_code": "es",
            "part_of_speech": "adverb",
            "agreement_tags": {"semantic": "direction"},
        }
    body["packs"][0]["templates"] = selected
    return body


def render_frame_options_artifact():
    slot = {
        "language_code": "es",
        "part_of_speech": "phrase",
        "agreement_tags": {"semantic": "good_wish"},
    }
    templates = []
    for exercise_type in ("multiple_choice", "listen_select"):
        templates.append(
            {
                "content_key": f"test.practice.{exercise_type}.render_frame",
                "lesson_content_key": LESSON_KEY,
                "type": exercise_type,
                "frame": {
                    "text": "bienvenido",
                    "language_code": "es",
                    "direction": "ltr",
                },
                "slots": {"good_wish": slot},
                "answer_derivation": {
                    "kind": "render_frame",
                    "frame": {
                        "text": "welcome",
                        "language_code": "en",
                        "direction": "ltr",
                    },
                },
                "feedback_frame": {
                    "text": "Correct.",
                    "language_code": "en",
                    "direction": "ltr",
                },
            }
        )
    return {
        "artifact_type": "lingosquared.practice_templates",
        "artifact_version": 1,
        "source_language": "en",
        "target_language": "es",
        "packs": [
            {
                "pack_key": "test.practice.render_frame.pack",
                "unit_content_key": "test.practice.unit",
                "tag_schema": {},
                "templates": templates,
            }
        ],
    }


def import_templates(client, admin, course_id, body):
    response = client.post(
        f"/admin/courses/{course_id}/practice/import",
        headers=admin,
        json=body,
    )
    assert response.status_code == 200, response.text
    return response.json()


def complete_lesson(auth, lesson_id):
    with SessionLocal() as db:
        db.add(
            LessonProgress(
                user_id=user_id(auth),
                lesson_id=lesson_id,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                correct_count=1,
                answer_count=1,
                xp_earned=0,
            )
        )
        db.commit()


def complete_via_api(client, auth, lesson_id):
    started = client.post(f"/lessons/{lesson_id}/start", headers=auth)
    assert started.status_code == 200
    detail = client.get(f"/lessons/{lesson_id}").json()
    if detail["exercises"]:
        exercise_id = detail["exercises"][0]["id"]
        with SessionLocal() as db:
            response = db.get(Exercise, exercise_id).correct_response
        answered = client.post(
            f"/exercises/{exercise_id}/answer",
            headers=auth,
            json={"response": response},
        )
        assert answered.status_code == 200 and answered.json()["correct"] is True
    completed = client.post(f"/lessons/{lesson_id}/complete", headers=auth)
    assert completed.status_code == 200
    return completed


def test_practice_batch_is_locked_without_completed_lessons(client, admin, auth):
    course_id, _ = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact())
    response = client.post(f"/practice/{course_id}/batch", headers=auth, json={"size": 6})
    assert response.status_code == 200
    assert response.json() == {"locked": True, "items": []}


def test_admin_practice_batch_unlocked_without_completed_lessons(client, admin):
    course_id, _ = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact())

    response = client.post(
        f"/practice/{course_id}/batch",
        headers=admin,
        json={"size": 6},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["locked"] is False
    assert payload["items"]


def test_practice_import_is_idempotent_and_all_prompt_contracts_generate(
    client, admin, auth, monkeypatch
):
    # This test verifies the six prompt SHAPES/contracts, not credential
    # gating -- but listen_select generation is gated on
    # tts_actually_configured() (app/practice/service.py, 2026-07-07 Fable
    # audit fix), which reads the REAL settings.google_cloud_tts_
    # credentials_json / azure_speech_key at request time. Without this
    # monkeypatch the listen_select leg of this test silently depends on
    # whatever TTS credentials happen to be in the test environment's .env:
    # it passed on the shared dev stack (Google credential configured) and
    # failed with 0 generated items on every clean/isolated stack
    # (confirmed by three independent dispatches, 2026-07-10). Pin the gate
    # open so the contract assertions are deterministic everywhere; the
    # gate's own behavior has dedicated tests below (fa excluded without a
    # key / fa included with one / prs always excluded).
    import app.practice.service as practice_service

    monkeypatch.setattr(
        practice_service, "tts_actually_configured", lambda language_code: True
    )
    course_id, lesson_id = create_course_with_lexemes()
    first = import_templates(client, admin, course_id, artifact())
    second = import_templates(client, admin, course_id, artifact())
    assert first == {"imported_templates": 6, "updated_templates": 0}
    assert second == {"imported_templates": 0, "updated_templates": 6}
    complete_via_api(client, auth, lesson_id)

    # generate_batch() applies the same due/mastery-based adaptive ladder
    # as reviews. First-try-correct lesson completion now seeds mastery
    # at 0.5; a single small batch is no longer
    # guaranteed to surface all 6 template types at once, and that's
    # correct, intended behavior, not a bug. To still verify every prompt
    # shape/contract deterministically, isolate one template type at a
    # time by deactivating the rest, so whichever lexeme the sampler picks
    # can only ever produce that type.
    with SessionLocal() as db:
        all_templates = list(
            db.scalars(
                select(PracticeTemplate).where(
                    PracticeTemplate.course_id == course_id
                )
            )
        )
        template_ids_by_type = {t.type: t.id for t in all_templates}

    by_type = {}
    for target_type, template_id in template_ids_by_type.items():
        with SessionLocal() as db:
            for template in db.scalars(
                select(PracticeTemplate).where(
                    PracticeTemplate.course_id == course_id
                )
            ):
                template.active = template.id == template_id
            db.commit()

        response = client.post(
            f"/practice/{course_id}/batch", headers=auth, json={"size": 1}
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["locked"] is False
        assert len(payload["items"]) == 1
        item = payload["items"][0]
        assert item["type"] == target_type
        by_type[target_type] = item

    assert set(by_type) == {
        "multiple_choice",
        "fill_in_blank",
        "word_order",
        "translation",
        "matching_pairs",
        "listen_select",
    }
    for item in by_type.values():
        assert isinstance(item["prompt"]["text_blocks"], list)
        assert all(
            set(block) == {"text", "language_code", "direction"}
            for block in item["prompt"]["text_blocks"]
        )
        assert "correct_response" not in item
    assert by_type["multiple_choice"]["prompt"]["options"]
    assert set(by_type["multiple_choice"]["prompt"]["options"]) <= {
        "one",
        "two",
        "three",
        "four",
    }
    assert "right" not in by_type["multiple_choice"]["prompt"]["options"]
    assert by_type["word_order"]["prompt"]["word_bank"]
    assert by_type["matching_pairs"]["prompt"]["pairs"]
    assert set(by_type["matching_pairs"]["prompt"]["pairs"][0]) == {"left", "right"}
    assert by_type["listen_select"]["prompt"]["audio_text"]
    assert by_type["listen_select"]["prompt"]["audio_language_code"] == "es"
    for kind in ("translation", "fill_in_blank"):
        assert by_type[kind]["prompt"]["answer_language_code"] == "es"
        assert len(by_type[kind]["prompt"]["text_blocks"]) >= 2
    fill_blocks = by_type["fill_in_blank"]["prompt"]["text_blocks"]
    assert fill_blocks[0]["text"] == "Fill in the missing word."
    assert fill_blocks[1]["text"] == "note: ___"
    # The content block itself (not just the instruction header) must
    # retain real visible text once the blank is masked out - a frame
    # whose ENTIRE text is the blanked slot (e.g. "{word}" alone -> "___")
    # is the exact live bug found 2026-07-05 (a generated fa practice item
    # rendered with nothing answerable at all). Checking fill_blocks[1]
    # specifically, not "any block", since the instruction header always
    # has text and would make a weaker assertion pass even with this bug.
    assert fill_blocks[1]["text"].replace("___", "").strip()


def test_low_mastery_practice_batch_interleaves_broad_mc_with_buildable_formats(
    client, admin, auth
):
    course_id, lesson_id = create_course_with_lexemes()
    add_extra_word_lexemes(course_id, lesson_id, count=12)
    import_templates(client, admin, course_id, artifact(include_listen=False))
    started = client.post(f"/lessons/{lesson_id}/start", headers=auth)
    assert started.status_code == 200
    detail = client.get(f"/lessons/{lesson_id}").json()
    for exercise in detail["exercises"]:
        wrong = client.post(
            f"/exercises/{exercise['id']}/answer",
            headers=auth,
            json={"response": "__wrong__"},
        )
        assert wrong.status_code == 200 and wrong.json()["correct"] is False
    completed = client.post(f"/lessons/{lesson_id}/complete", headers=auth)
    assert completed.status_code == 200

    response = client.post(
        f"/practice/{course_id}/batch",
        headers=auth,
        json={"size": 12},
    )

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 12
    counts = Counter(item["type"] for item in items)
    assert counts["multiple_choice"] > 0
    assert len(counts) > 1
    assert max(counts.values()) <= len(items) / 2


def test_selectable_practice_requires_two_constrained_distractors(
    client, admin, auth
):
    course_id, lesson_id = create_course_with_lexemes()
    imported = import_templates(
        client,
        admin,
        course_id,
        undersized_options_artifact(),
    )
    assert imported == {"imported_templates": 2, "updated_templates": 0}
    complete_lesson(auth, lesson_id)

    response = client.post(
        f"/practice/{course_id}/batch",
        headers=auth,
        json={"size": 20},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"locked": False, "items": []}


def test_render_frame_options_use_declared_slot_constraints(client, admin, auth):
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, render_frame_options_artifact())
    complete_lesson(auth, lesson_id)

    response = client.post(
        f"/practice/{course_id}/batch",
        headers=auth,
        json={"size": 2},
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    # Since Phase A, per-lexeme generation shuffles same-tier templates and
    # returns the first that succeeds, so with two same-tier templates
    # (multiple_choice, listen_select) sharing this lexeme pool, getting
    # both types in one small batch is possible but not guaranteed - the
    # actual thing this test checks is the options constraint below, not
    # type diversity.
    assert items
    assert {item["type"] for item in items} <= {
        "multiple_choice",
        "listen_select",
    }
    allowed = {"welcome", "good morning", "good afternoon", "good evening"}
    for item in items:
        options = item["prompt"]["options"]
        assert len(options) >= 3
        assert set(options) <= allowed
        assert "right" not in options


def test_practice_diminishing_xp_no_review_and_single_answer_enforced(
    client, admin, auth
):
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_lesson(auth, lesson_id)
    uid = user_id(auth)
    with SessionLocal() as db:
        template = db.scalar(
            select(PracticeTemplate).where(PracticeTemplate.course_id == course_id)
        )
        items = []
        for _ in range(21):
            item = PracticeItem(
                user_id=uid,
                course_id=course_id,
                template_id=template.id,
                filled_slots={"word": "uno"},
                prompt={"text_blocks": []},
                correct_response="one",
                xp_value=5,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            )
            db.add(item)
            items.append(item)
        db.commit()
        item_ids = [item.id for item in items]
        reviews_before = db.scalar(select(func.count(ReviewItem.id)))

    awards = []
    for item_id in item_ids:
        response = client.post(
            f"/practice/items/{item_id}/answer",
            headers=auth,
            json={"response": "one"},
        )
        assert response.status_code == 200, response.text
        awards.append(response.json()["xp_awarded"])
    assert awards[0] == 5
    assert awards[19] == 5
    assert awards[20] == 1

    duplicate = client.post(
        f"/practice/items/{item_ids[0]}/answer",
        headers=auth,
        json={"response": "one"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "practice_item_answered"
    with SessionLocal() as db:
        assert db.scalar(select(func.count(PracticeAttempt.id)).where(PracticeAttempt.user_id == uid)) == 21
        assert db.scalar(select(func.count(ReviewItem.id))) == reviews_before


def test_expired_practice_item_fails_cleanly(client, admin, auth):
    course_id, _ = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    with SessionLocal() as db:
        template = db.scalar(
            select(PracticeTemplate).where(PracticeTemplate.course_id == course_id)
        )
        item = PracticeItem(
            user_id=user_id(auth),
            course_id=course_id,
            template_id=template.id,
            filled_slots={"word": "uno"},
            prompt={"text_blocks": []},
            correct_response="one",
            xp_value=5,
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        db.add(item)
        db.commit()
        item_id = item.id
    response = client.post(
        f"/practice/items/{item_id}/answer",
        headers=auth,
        json={"response": "one"},
    )
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "practice_item_expired"


def test_farsi_sampler_excludes_listen_select_without_a_configured_azure_key(
    client, admin, auth, monkeypatch
):
    # 2026-07-07 (Fable audit finding): fa was added to
    # TTS_SUPPORTED_LANGUAGES the day Azure integration code shipped, but
    # that's static language membership, not proof a real Azure key is
    # configured on this deploy target. app/practice/service.py's gate now
    # checks tts_actually_configured() (app/services/tts.py), which
    # inspects real settings.azure_speech_key/_region -- both empty by
    # default (app/core/config.py) until Ramin actually provisions one.
    # This is the REAL current default state and must stay excluded, or
    # the app generates unanswerable audio-only items with no real voice.
    #
    # 2026-07-10: pin the gate CLOSED rather than relying on the test
    # environment's .env actually having no Azure key -- the mirror image
    # of the env-dependence that made the prompt-contracts test above fail
    # on credential-less stacks. What this test verifies is the WIRING
    # (generate_batch consults the gate and drops listen_select when it
    # says no), which stays meaningful regardless of what credentials the
    # host running pytest happens to have configured.
    import app.practice.service as practice_service

    monkeypatch.setattr(
        practice_service, "tts_actually_configured", lambda language_code: False
    )
    course_id, lesson_id = create_course_with_lexemes(target="fa")
    import_templates(client, admin, course_id, artifact(target="fa"))
    complete_lesson(auth, lesson_id)
    response = client.post(
        f"/practice/{course_id}/batch", headers=auth, json={"size": 20}
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"]
    assert all(item["type"] != "listen_select" for item in response.json()["items"])


def test_farsi_sampler_includes_listen_select_once_azure_is_actually_configured(
    client, admin, auth, monkeypatch
):
    # The other half of the finding above: fa SHOULD generate
    # listen_select once a real Azure key is actually present, same as
    # any Google-covered language. Mocks a real-looking credential rather
    # than asserting on language membership alone.
    import app.practice.service as practice_service

    monkeypatch.setattr(
        practice_service,
        "tts_actually_configured",
        lambda language_code: language_code == "fa",
    )
    course_id, lesson_id = create_course_with_lexemes(target="fa")
    import_templates(client, admin, course_id, artifact(target="fa"))
    complete_lesson(auth, lesson_id)
    response = client.post(
        f"/practice/{course_id}/batch", headers=auth, json={"size": 20}
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"]
    assert any(item["type"] == "listen_select" for item in response.json()["items"])


def test_dari_sampler_excludes_listen_select(client, admin, auth):
    # Dari (prs) has zero TTS coverage from either Google or Azure --
    # unlike fa above, this exclusion is correct regardless of credentials.
    course_id, lesson_id = create_course_with_lexemes(target="prs")
    import_templates(client, admin, course_id, artifact(target="prs"))
    complete_lesson(auth, lesson_id)
    response = client.post(
        f"/practice/{course_id}/batch", headers=auth, json={"size": 20}
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"]
    assert all(item["type"] != "listen_select" for item in response.json()["items"])


def blank_only_fill_in_blank_artifact(target="fa"):
    # Reproduces the exact real-content shape found live 2026-07-05:
    # docs/content/practice/en-fa/a1_unit01.yaml's letter_fill.002 template
    # has frame.text == "{letter}" - nothing but the one slot that
    # fill_in_blank then blanks out, leaving a prompt with zero visible
    # context (just "___" and a speak button that, for fa, has no voice
    # either - the "no audio" detail that was actually a red herring, not
    # the root cause). The same single-slot-frame shape was also found in
    # en-prs/fa-en/nl-en/prs-en/en-nl practice packs, so this isn't fa- or
    # audio-specific - it's a generic fill_in_blank generation guard.
    direction = "rtl" if target in {"fa", "prs"} else "ltr"
    slot = {
        "language_code": target,
        "part_of_speech": "noun",
        "agreement_tags": {"semantic": "word"},
    }
    return {
        "artifact_type": "lingosquared.practice_templates",
        "artifact_version": 1,
        "source_language": "en",
        "target_language": target,
        "packs": [
            {
                "pack_key": "test.practice.blank_only.pack",
                "unit_content_key": "test.practice.unit",
                "tag_schema": {},
                "templates": [
                    {
                        "content_key": "test.practice.fill_in_blank.blank_only",
                        "lesson_content_key": LESSON_KEY,
                        "type": "fill_in_blank",
                        "frame": {
                            "text": "{word}",
                            "language_code": target,
                            "direction": direction,
                        },
                        "slots": {"word": slot},
                        "answer_derivation": {"kind": "slot_text", "slot": "word"},
                        "feedback_frame": {
                            "text": "Correct.",
                            "language_code": "en",
                            "direction": "ltr",
                        },
                    }
                ],
            }
        ],
    }


def test_fill_in_blank_never_generates_a_blank_only_prompt(client, admin, auth):
    course_id, lesson_id = create_course_with_lexemes(target="fa")
    import_templates(client, admin, course_id, blank_only_fill_in_blank_artifact())
    complete_lesson(auth, lesson_id)
    response = client.post(
        f"/practice/{course_id}/batch", headers=auth, json={"size": 20}
    )
    assert response.status_code == 200, response.text
    # The only imported template is the blank-only shape - with the fix,
    # build_prompt() must reject every attempt to generate from it, so no
    # unanswerable item is ever served rather than degrading gracefully in
    # some other way.
    assert response.json() == {"locked": False, "items": []}


def interchangeable_fill_in_blank_artifact(target="es"):
    # Reproduces the real live bug found 2026-07-06 (en-nl Endless Practice,
    # docs/content/practice/en-nl/a1_unit01.yaml's je/jij informal_address
    # slot): real surrounding text survives masking ("nota: ___" here, "Ben
    # ___ nieuw hier?" for real), so §13's bare-slot guard doesn't fire, but
    # the slot's own candidate pool (uno/dos/tres/cuatro, all tagged
    # semantic=word by create_course_with_lexemes()) has no other frame
    # content able to prefer one over another - every candidate is equally
    # correct Spanish here, yet only the one the sampler filled used to be
    # accepted. AUTHORING_GUIDE.md#17's `interchangeable: true` flag opts
    # this template into accepting any of the slot's own matches.
    direction = "rtl" if target in {"fa", "prs"} else "ltr"
    slot = {
        "language_code": target,
        "part_of_speech": "noun",
        "agreement_tags": {"semantic": "word"},
    }
    return {
        "artifact_type": "lingosquared.practice_templates",
        "artifact_version": 1,
        "source_language": "en",
        "target_language": target,
        "packs": [
            {
                "pack_key": "test.practice.interchangeable.pack",
                "unit_content_key": "test.practice.unit",
                "tag_schema": {},
                "templates": [
                    {
                        "content_key": "test.practice.fill_in_blank.interchangeable",
                        "lesson_content_key": LESSON_KEY,
                        "type": "fill_in_blank",
                        "frame": {
                            "text": "nota: {word}",
                            "language_code": target,
                            "direction": direction,
                        },
                        "slots": {"word": slot},
                        "answer_derivation": {
                            "kind": "slot_text",
                            "slot": "word",
                            "interchangeable": True,
                        },
                        "feedback_frame": {
                            "text": "Correct.",
                            "language_code": "en",
                            "direction": "ltr",
                        },
                    }
                ],
            }
        ],
    }


def test_fill_in_blank_interchangeable_accepts_any_matching_candidate(
    client, admin, auth
):
    course_id, lesson_id = create_course_with_lexemes(target="es")
    import_templates(client, admin, course_id, interchangeable_fill_in_blank_artifact())
    complete_lesson(auth, lesson_id)

    response = client.post(
        f"/practice/{course_id}/batch", headers=auth, json={"size": 1}
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 1
    item_id = items[0]["id"]

    with SessionLocal() as db:
        stored = db.get(PracticeItem, item_id)
        correct = stored.correct_response
        # The multi-answer shape grade() (app/api/router.py) already
        # generically supports for hand-authored content - build_prompt()
        # now produces it too when interchangeable: true is set.
        assert set(correct) == {"canonical", "accepted"}
        assert correct["canonical"] in {"uno", "dos", "tres", "cuatro"}
        assert set(correct["accepted"]) == {"uno", "dos", "tres", "cuatro"}
        # A pool member that is NOT the one the sampler happened to fill
        # must still grade correct - this is the actual bug being fixed.
        other = next(t for t in correct["accepted"] if t != correct["canonical"])

    response = client.post(
        f"/practice/items/{item_id}/answer",
        headers=auth,
        json={"response": other},
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"] == "correct"


def word_order_hint_artifact(target="es"):
    direction = "rtl" if target in {"fa", "prs"} else "ltr"
    slot = {
        "language_code": target,
        "part_of_speech": "noun",
        "agreement_tags": {"semantic": "word"},
    }
    return {
        "artifact_type": "lingosquared.practice_templates",
        "artifact_version": 1,
        "source_language": "en",
        "target_language": target,
        "packs": [
            {
                "pack_key": "test.practice.word_order_hint.pack",
                "unit_content_key": "test.practice.unit",
                "tag_schema": {},
                "templates": [
                    {
                        "content_key": "test.practice.word_order.hint",
                        "lesson_content_key": LESSON_KEY,
                        "type": "word_order",
                        "frame": {
                            "text": "{word} ahora",
                            "language_code": target,
                            "direction": direction,
                        },
                        "slots": {"word": slot},
                        "answer_derivation": {
                            "kind": "render_frame",
                            "frame": {
                                "text": "{word} ahora",
                                "language_code": target,
                                "direction": direction,
                            },
                        },
                        "feedback_frame": {
                            "text": "Correct.",
                            "language_code": "en",
                            "direction": "ltr",
                        },
                    }
                ],
            }
        ],
    }


def test_word_order_prompt_includes_a_gloss_hint_not_just_the_instruction(
    client, admin, auth
):
    # Real bug found 2026-07-05 (QA pass): the generated word_order prompt
    # only ever showed the generic "Put the words in the correct order."
    # instruction plus the shuffled word bank - zero indication anywhere
    # of what phrase the words should form, making any slotted phrase the
    # learner hasn't already memorized verbatim unguessable. A compiled
    # lesson's hand-authored word_order card bakes the target phrase
    # directly into its instruction text instead; the generated engine had
    # no equivalent. Fixed by rendering the same frame with each slot's
    # `english_gloss` substituted for its `token` as a second text block.
    course_id, lesson_id = create_course_with_lexemes(target="es")
    import_templates(client, admin, course_id, word_order_hint_artifact())
    complete_lesson(auth, lesson_id)
    response = client.post(
        f"/practice/{course_id}/batch", headers=auth, json={"size": 20}
    )
    assert response.status_code == 200, response.text
    word_order_items = [
        item for item in response.json()["items"] if item["type"] == "word_order"
    ]
    assert word_order_items, "expected at least one generated word_order item"
    for item in word_order_items:
        blocks = item["prompt"]["text_blocks"]
        assert len(blocks) == 2
        instruction, hint = blocks
        assert instruction["text"] == "Put the words in the correct order."
        # The hint substitutes the slotted word's English gloss into the
        # same frame shape ("{word} ahora" -> "<gloss> ahora") - never just
        # the bare instruction alone, and never the literal target-language
        # correct answer (which would trivialize the reordering task).
        # Updated 2026-07-06 (real user report): the substituted gloss is
        # now wrapped in the existing single-asterisk convention
        # (AUTHORING_GUIDE.md #15) so the frontend renders it emphasized,
        # distinguished from the surrounding target-language frame text -
        # previously it spliced in unmarked, producing an unreadable
        # mixed-language run-on (e.g. "Ben you; your (informal) nieuw
        # hier?").
        assert hint["text"].endswith(" ahora")
        assert hint["text"] in {
            "*one* ahora",
            "*two* ahora",
            "*three* ahora",
            "*four* ahora",
        }


def add_uncompleted_lesson_lexeme(course_id, target="es"):
    with SessionLocal() as db:
        unit = db.scalar(select(Unit).where(Unit.course_id == course_id))
        lesson = Lesson(
            unit_id=unit.id,
            title="Uncompleted lesson",
            order=2,
            content_key="test.practice.lesson.untaught",
        )
        db.add(lesson)
        db.flush()
        db.add(
            Lexeme(
                course_id=course_id,
                token="secreto",
                language_code=target,
                part_of_speech="noun",
                english_gloss="secret",
                agreement_tags={"semantic": "word"},
                provenance_lesson_id=lesson.id,
                provenance_lesson_content_key="test.practice.lesson.untaught",
                provenance_content_key="test.lexeme.untaught",
            )
        )
        db.commit()


def practice_item_answers(item_ids):
    with SessionLocal() as db:
        rows = db.execute(
            select(PracticeItem.id, PracticeItem.correct_response)
            .where(PracticeItem.id.in_(item_ids))
            .order_by(PracticeItem.created_at, PracticeItem.id)
        ).all()
    by_id = {item_id: answer for item_id, answer in rows}
    return [by_id[item_id] for item_id in item_ids]


def conversation_prompt_texts(prompt):
    texts = []
    for node in prompt["nodes"]:
        texts.append(node["app_turn"]["text"])
        texts.extend(node["accepted_variants"])
    return texts


def test_speaking_practice_batch_uses_only_completed_lesson_vocabulary(
    client, admin, auth
):
    course_id, lesson_id = create_course_with_lexemes(target="es")
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)
    add_uncompleted_lesson_lexeme(course_id, target="es")

    response = client.post(
        f"/practice/{course_id}/batch",
        headers=auth,
        json={"size": 6, "mode": "speaking"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["locked"] is False
    items = payload["items"]
    assert len(items) == 6
    assert {item["type"] for item in items} == {"speak_repeat", "speak_response"}

    answers = practice_item_answers([item["id"] for item in items])
    assert "secreto" not in answers
    assert set(answers) <= {
        "uno",
        "dos",
        "tres",
        "cuatro",
        "derecha",
        "buenos días",
        "buenas tardes",
        "buenas noches",
    }

    first_answer = answers[0]
    answered = client.post(
        f"/practice/items/{items[0]['id']}/answer",
        headers=auth,
        json={"response": first_answer},
    )
    assert answered.status_code == 200, answered.text
    assert answered.json()["result"] == "correct"


def test_conversation_practice_batch_uses_only_completed_lesson_vocabulary(
    client, admin, auth
):
    course_id, lesson_id = create_course_with_lexemes(target="es")
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)
    add_uncompleted_lesson_lexeme(course_id, target="es")

    response = client.post(
        f"/practice/{course_id}/batch",
        headers=auth,
        json={"size": 4, "mode": "conversation"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["locked"] is False
    items = payload["items"]
    assert len(items) == 4
    assert {item["type"] for item in items} == {"conversation"}
    for item in items:
        texts = conversation_prompt_texts(item["prompt"])
        assert "secreto" not in texts
        assert set(texts) <= {
            "uno",
            "dos",
            "tres",
            "cuatro",
            "derecha",
            "buenos días",
            "buenas tardes",
            "buenas noches",
        }


def test_conversation_practice_branch_selection_picks_matching_next_node(
    client, admin, auth
):
    course_id, lesson_id = create_course_with_lexemes(target="es")
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)

    response = client.post(
        f"/practice/{course_id}/batch",
        headers=auth,
        json={"size": 1, "mode": "conversation"},
    )
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    start = item["prompt"]["current_node"]
    full_start = next(
        node for node in item["prompt"]["nodes"] if node["id"] == start["id"]
    )
    variant = full_start["accepted_variants"][0]
    expected_next = next(
        branch["next_node_id"]
        for branch in full_start["branches"]
        if branch["variant"] == variant
    )

    answered = client.post(
        f"/practice/items/{item['id']}/answer",
        headers=auth,
        json={"response": {"node_id": start["id"], "response": variant}},
    )

    assert answered.status_code == 200, answered.text
    payload = answered.json()
    assert payload["correct"] is True
    assert payload["result"] == "correct"
    assert payload["xp_awarded"] == 0
    assert payload["next_node"]["id"] == expected_next


def test_conversation_practice_unrecognized_reply_does_not_dead_end(
    client, admin, auth
):
    course_id, lesson_id = create_course_with_lexemes(target="es")
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)

    response = client.post(
        f"/practice/{course_id}/batch",
        headers=auth,
        json={"size": 1, "mode": "conversation"},
    )
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    start = item["prompt"]["current_node"]
    full_start = next(
        node for node in item["prompt"]["nodes"] if node["id"] == start["id"]
    )

    answered = client.post(
        f"/practice/items/{item['id']}/answer",
        headers=auth,
        json={"response": {"node_id": start["id"], "response": "not taught"}},
    )

    assert answered.status_code == 200, answered.text
    payload = answered.json()
    assert payload["correct"] is False
    assert payload["result"] == "incorrect"
    assert payload["xp_awarded"] == 0
    assert payload["next_node"]["id"] == full_start["fallback_node_id"]


def test_conversation_practice_batch_is_seed_repeatable_for_same_state(
    client, admin, auth
):
    course_id, lesson_id = create_course_with_lexemes(target="es")
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_lesson(auth, lesson_id)
    uid = user_id(auth)

    first = client.post(
        f"/practice/{course_id}/batch",
        headers=auth,
        json={"size": 3, "mode": "conversation"},
    )
    assert first.status_code == 200, first.text
    first_prompts = [item["prompt"] for item in first.json()["items"]]

    with SessionLocal() as db:
        db.execute(
            delete(PracticeItem).where(
                PracticeItem.user_id == uid,
                PracticeItem.course_id == course_id,
            )
        )
        db.commit()

    second = client.post(
        f"/practice/{course_id}/batch",
        headers=auth,
        json={"size": 3, "mode": "conversation"},
    )
    assert second.status_code == 200, second.text

    assert [item["prompt"] for item in second.json()["items"]] == first_prompts


def test_speaking_practice_prefers_weakest_tracked_lexeme_first(
    client, admin, auth
):
    course_id, lesson_id = create_course_with_lexemes(target="es")
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)
    uid = user_id(auth)
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        rows = list(
            db.execute(
                select(UserLexemeSRS, Lexeme)
                .join(Lexeme, Lexeme.id == UserLexemeSRS.lexeme_id)
                .where(
                    UserLexemeSRS.user_id == uid,
                    UserLexemeSRS.course_id == course_id,
                )
            )
        )
        for srs, lexeme in rows:
            srs.mastery = 0.9
            srs.due_at = now + timedelta(days=10)
            if lexeme.token == "dos":
                srs.mastery = 0.05
                srs.due_at = now + timedelta(days=3)
        db.commit()

    response = client.post(
        f"/practice/{course_id}/batch",
        headers=auth,
        json={"size": 1, "mode": "speaking"},
    )

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["type"] == "speak_repeat"
    assert practice_item_answers([items[0]["id"]]) == ["dos"]


def test_speaking_practice_batch_is_seed_repeatable_for_same_state(
    client, admin, auth
):
    course_id, lesson_id = create_course_with_lexemes(target="es")
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_lesson(auth, lesson_id)
    uid = user_id(auth)

    first = client.post(
        f"/practice/{course_id}/batch",
        headers=auth,
        json={"size": 5, "mode": "speaking"},
    )
    assert first.status_code == 200, first.text
    first_items = first.json()["items"]
    first_answers = practice_item_answers([item["id"] for item in first_items])
    first_types = [item["type"] for item in first_items]

    with SessionLocal() as db:
        db.execute(
            delete(PracticeItem).where(
                PracticeItem.user_id == uid,
                PracticeItem.course_id == course_id,
            )
        )
        db.commit()

    second = client.post(
        f"/practice/{course_id}/batch",
        headers=auth,
        json={"size": 5, "mode": "speaking"},
    )
    assert second.status_code == 200, second.text
    second_items = second.json()["items"]

    assert [item["type"] for item in second_items] == first_types
    assert practice_item_answers([item["id"] for item in second_items]) == first_answers


def test_practice_answer_returns_rendered_template_feedback(client, admin, auth):
    course_id, lesson_id = create_course_with_lexemes()
    body = artifact(include_listen=False)
    templates = body["packs"][0]["templates"]
    by_key = {t["content_key"]: t for t in templates}
    by_key["test.practice.multiple_choice"]["feedback_frame"] = {
        "text": "{word} means {word}.",
        "language_code": "en",
        "direction": "ltr",
        "slot_rendering": {"word": "english_gloss"},
    }
    by_key["test.practice.fill_in_blank"]["feedback_frame"] = {
        "text": "Remember *{word}*.",
        "language_code": "en",
        "direction": "ltr",
    }
    by_key["test.practice.translation"]["feedback_frame"] = {
        "text": "  ",
        "language_code": "en",
        "direction": "ltr",
    }
    import_templates(client, admin, course_id, body)
    complete_lesson(auth, lesson_id)
    uid = user_id(auth)
    with SessionLocal() as db:
        gloss = db.scalar(
            select(Lexeme.english_gloss).where(
                Lexeme.course_id == course_id, Lexeme.token == "uno"
            )
        )
        ids = {}
        for key in (
            "test.practice.multiple_choice",
            "test.practice.fill_in_blank",
            "test.practice.translation",
        ):
            template = db.scalar(
                select(PracticeTemplate).where(
                    PracticeTemplate.course_id == course_id,
                    PracticeTemplate.content_key == key,
                )
            )
            item = PracticeItem(
                user_id=uid,
                course_id=course_id,
                template_id=template.id,
                filled_slots={"word": "uno"},
                prompt={"text_blocks": []},
                correct_response="one",
                xp_value=5,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            )
            db.add(item)
            db.flush()
            ids[key] = item.id
        db.commit()

    def answer(key, response):
        r = client.post(
            f"/practice/items/{ids[key]}/answer",
            headers=auth,
            json={"response": response},
        )
        assert r.status_code == 200, r.text
        return r.json()

    # Rendered for a correct answer, honouring slot_rendering.
    mc = answer("test.practice.multiple_choice", "one")
    assert mc["correct"] is True
    assert mc["feedback"] == f"{gloss} means {gloss}."
    # Rendered for an incorrect answer too, using the stored token.
    fib = answer("test.practice.fill_in_blank", "wrong")
    assert fib["correct"] is False
    assert fib["feedback"] == "Remember *uno*."
    # Blank feedback text is omitted (field stays backwards compatible).
    blank = answer("test.practice.translation", "one")
    assert "feedback" not in blank


def _feedback_template(db, course_id, text, slot_rendering=None, pos=("noun",)):
    from app.practice.service import render_item_feedback  # noqa: F401

    frame = {"text": text, "language_code": "en", "direction": "ltr"}
    if slot_rendering:
        frame["slot_rendering"] = slot_rendering
    template = db.scalar(
        select(PracticeTemplate).where(PracticeTemplate.course_id == course_id)
    )
    template.feedback_frame = frame
    template.slots = {
        "word": {
            "language_code": "es",
            "part_of_speech": list(pos),
            "agreement_tags": {"semantic": "word"},
        }
    }
    return template


def test_render_item_feedback_guards(client, admin, auth):
    from app.practice.service import (
        feedback_suppression_reason,
        render_item_feedback,
    )

    course_id, _ = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    with SessionLocal() as db:
        template = _feedback_template(db, course_id, "Note: {word} is one.")
        # Generated speaking items borrow an unrelated template: no feedback.
        assert (
            render_item_feedback(
                db, template, course_id,
                {"word": "uno", "_generated_type": "speak_repeat"},
            )
            is None
        )
        assert (
            render_item_feedback(db, template, course_id, {"word": "uno"})
            == "Note: uno is one."
        )

        # Same token, two parts of speech with different glosses.
        lex = db.scalar(
            select(Lexeme).where(Lexeme.course_id == course_id, Lexeme.token == "uno")
        )
        other = Lexeme(
            course_id=course_id,
            token="uno",
            language_code="es",
            part_of_speech="adjective",
            english_gloss="single",
            agreement_tags={"semantic": "word"},
            provenance_lesson_id=lex.provenance_lesson_id,
            provenance_lesson_content_key=LESSON_KEY,
            provenance_content_key="test.lexeme.uno.adj",
        )
        db.add(other)
        db.flush()
        template = _feedback_template(
            db, course_id, "Meaning: {word}.", {"word": "english_gloss"},
            pos=("noun", "adjective"),
        )
        slots = {"word": "uno"}
        assert render_item_feedback(db, template, course_id, slots) is None
        assert (
            render_item_feedback(db, template, course_id, slots, other.id)
            == "Meaning: single."
        )
        assert (
            render_item_feedback(db, template, course_id, slots, lex.id)
            == f"Meaning: {lex.english_gloss}."
        )

        # Render errors never propagate.
        template.feedback_frame = {"text": "{word}!", "slot_rendering": {"word": "nope"}}
        assert render_item_feedback(db, template, course_id, slots, lex.id) is None
        db.rollback()

    assert feedback_suppression_reason("{item}") == "bare_slot"
    assert feedback_suppression_reason("Match each word with its meaning.") == "instruction"
    assert feedback_suppression_reason("The correct answer is {item}.") == "restates_answer"
    assert feedback_suppression_reason("The Dutch word is {item}.") is None
