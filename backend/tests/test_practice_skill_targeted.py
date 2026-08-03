from sqlalchemy import select

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import Course, Lexeme, PracticeItem, PracticeTemplate
from app.practice.service import generate_batch
from app.schemas.api import PracticeBatchIn
from test_endless_practice import (
    artifact,
    complete_lesson,
    create_course_with_lexemes,
    import_templates,
)
from test_phase_f_checkpoints import answer_item, start_checkpoint


def user_id(auth):
    return decode_token(auth["Authorization"].split()[1])


def test_practice_batch_in_drops_unknown_types_and_preserves_none():
    payload = PracticeBatchIn(types=["multiple_choice", "BOGUS", "translation"])

    assert payload.types == ["multiple_choice", "translation"]
    assert PracticeBatchIn(types=None).types is None


def test_generate_batch_filters_template_types(client, admin, auth):
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_lesson(auth, lesson_id)

    with SessionLocal() as db:
        course = db.get(Course, course_id)
        locked, items = generate_batch(
            db,
            user_id(auth),
            course,
            size=6,
            types=["translation"],
        )

        assert locked is False
        for item in items:
            template = db.get(PracticeTemplate, item.template_id)
            assert template.type == "translation"


def test_generate_batch_filters_target_lexeme_ids(client, admin, auth):
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_lesson(auth, lesson_id)

    with SessionLocal() as db:
        course = db.get(Course, course_id)
        target_lexeme_id = db.scalar(
            select(Lexeme.id)
            .where(Lexeme.course_id == course_id)
            .order_by(Lexeme.id)
            .limit(1)
        )
        requested_ids = {str(target_lexeme_id)}

        locked, items = generate_batch(
            db,
            user_id(auth),
            course,
            size=6,
            target_lexeme_ids=list(requested_ids),
        )

        assert locked is False
        assert all(str(item.target_lexeme_id) in requested_ids for item in items)


def test_checkpoint_result_reports_weak_lexeme_ids_aligned_with_outcomes(
    client,
    admin,
    auth,
):
    _, _, unit_id, items = start_checkpoint(client, admin, auth)

    with SessionLocal() as db:
        wrong_item = next(
            db.get(PracticeItem, item["id"])
            for item in items
            if db.get(PracticeItem, item["id"]).target_lexeme_id is not None
        )
        wrong_item_id = wrong_item.id
        weak_lexeme_id = str(wrong_item.target_lexeme_id)
        weak_outcome = db.get(Lexeme, wrong_item.target_lexeme_id).english_gloss

    for item in items:
        answer_item(
            client,
            auth,
            item["id"],
            correct=item["id"] != wrong_item_id,
        )

    result = client.get(
        f"/units/{unit_id}/checkpoint/result",
        headers=auth,
    )
    assert result.status_code == 200, result.text
    body = result.json()

    assert body["status"] == "complete"
    assert body["weak_lexeme_ids"]
    assert weak_lexeme_id in body["weak_lexeme_ids"]
    assert weak_outcome in body["weak_outcomes"]
