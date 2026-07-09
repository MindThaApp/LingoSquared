"""Regression coverage for the ContentIssueReport PracticeItem gap.

Found during a 2026-07-07 audit: `POST /exercises/{exercise_id}/report`
only ever recognized real `Exercise` rows, but `ReviewPage.tsx` (lexeme
review sessions) and the Endless Practice feed are both backed entirely
by `PracticeItem` - a separate table with no relationship to `Exercise`
at all. `ReviewPage.tsx` was passing a `PracticeItem.id` into that
endpoint and 404ing every single time; the Endless Practice feed had no
report button wired in at all. Fixed by making `ContentIssueReport.
exercise_id` nullable, adding a nullable `practice_item_id` FK (mirrors
the existing nullable `content_key_id` secondary FK), a DB check
constraint enforcing at most one of the two is set, and a new
`POST /practice/items/{item_id}/report` endpoint.
"""

import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import ContentIssueReport, Exercise, PracticeItem, PracticeTemplate
from test_endless_practice import (
    artifact,
    complete_via_api,
    create_course_with_lexemes,
    import_templates,
)


def user_id(auth):
    return decode_token(auth["Authorization"].split()[1])


def seeded_exercise_id():
    with SessionLocal() as db:
        return db.scalar(select(Exercise.id).order_by(Exercise.id))


def test_report_practice_item_from_endless_practice_batch(client, admin, auth):
    # Realistic path: a real generated PracticeItem from the actual
    # Endless Practice feed (the second gap found - no report button
    # existed here at all), reported through the new endpoint.
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)

    batch = client.post(
        f"/practice/{course_id}/batch", headers=auth, json={"size": 1}
    )
    assert batch.status_code == 200, batch.text
    items = batch.json()["items"]
    assert items, "expected at least one generated practice item"
    item_id = items[0]["id"]

    response = client.post(
        f"/practice/items/{item_id}/report",
        headers={**auth, "User-Agent": "LingoSquared-Test/1.0", "Accept-Language": "en"},
        json={
            "category": "wrong_answer_key",
            "description": "Generated item's answer key looks wrong.",
            "learner_response": {"response": "my answer"},
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "open"
    assert set(body) == {"id", "status"}

    with SessionLocal() as db:
        issue = db.get(ContentIssueReport, body["id"])
        assert issue is not None
        assert issue.reporter_user_id == user_id(auth)
        assert issue.practice_item_id == item_id
        assert issue.exercise_id is None
        assert issue.category == "wrong_answer_key"
        assert issue.learner_response == {"response": "my answer"}


def test_report_practice_item_from_review_session(client, admin, auth):
    # Realistic path: a real generated PracticeItem from /reviews/session
    # (the first gap found - ReviewPage.tsx passed this id straight into
    # /exercises/{id}/report and 404d every time, reproduced live).
    from app.models import UserLexemeSRS

    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)
    uid = user_id(auth)

    with SessionLocal() as db:
        srs = db.scalar(
            select(UserLexemeSRS).where(
                UserLexemeSRS.user_id == uid,
                UserLexemeSRS.course_id == course_id,
            )
        )
        srs.due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    session = client.post(
        "/reviews/session", headers=auth, json={"course_id": course_id, "size": 1}
    )
    assert session.status_code == 200, session.text
    item_id = session.json()["items"][0]["id"]

    # This is exactly the call ReviewPage.tsx's ReportIssueButton makes
    # after the fix - confirm it's a 201, not the pre-fix 404.
    response = client.post(
        f"/practice/items/{item_id}/report",
        headers=auth,
        json={"category": "mistranslation", "description": "Wrong gloss shown."},
    )
    assert response.status_code == 201, response.text

    with SessionLocal() as db:
        issue = db.get(ContentIssueReport, response.json()["id"])
        assert issue.practice_item_id == item_id
        assert issue.exercise_id is None


def test_exercise_report_endpoint_404s_for_a_practice_item_id(client, admin, auth):
    # Precisely reproduces the original bug: passing a PracticeItem id to
    # the Exercise-only endpoint. A PracticeItem id essentially never
    # coincidentally collides with a real Exercise row's id (both are
    # random UUIDs), so this 404s deterministically pre- and post-fix -
    # the fix is the NEW endpoint existing, not this one starting to
    # accept PracticeItem ids too.
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)
    batch = client.post(
        f"/practice/{course_id}/batch", headers=auth, json={"size": 1}
    )
    item_id = batch.json()["items"][0]["id"]

    response = client.post(
        f"/exercises/{item_id}/report",
        headers=auth,
        json={"category": "wrong_answer_key"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "exercise_not_found"


def test_report_practice_item_rejects_foreign_item(client, admin, auth):
    course_id, _ = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))

    other = client.post(
        "/auth/register",
        json={
            "email": f"other-{os.urandom(4).hex()}@example.com",
            "password": "password123",
            "display_name": "Other User",
        },
    )
    assert other.status_code == 201
    other_user_id = decode_token(other.json()["access_token"])

    with SessionLocal() as db:
        template = db.scalar(
            select(PracticeTemplate).where(PracticeTemplate.course_id == course_id)
        )
        # Same construction technique as
        # test_expired_practice_item_fails_cleanly (test_endless_practice.py),
        # just owned by a different real user than `auth`.
        other_item = PracticeItem(
            user_id=other_user_id,
            course_id=course_id,
            template_id=template.id,
            filled_slots={},
            prompt={"text_blocks": []},
            correct_response="whatever",
            xp_value=5,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(other_item)
        db.commit()
        other_item_id = other_item.id

    response = client.post(
        f"/practice/items/{other_item_id}/report",
        headers=auth,
        json={"category": "other"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "practice_item_not_found"


def test_report_practice_item_rejects_nonexistent_item(client, auth):
    response = client.post(
        "/practice/items/does-not-exist/report",
        headers=auth,
        json={"category": "other"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "practice_item_not_found"


def test_content_issue_report_requires_at_most_one_item_target(client, admin, auth):
    # DB-level guard, exercised directly at the ORM layer since no
    # endpoint can construct the invalid "both ids" shape. Both ids used
    # below are real, valid FK targets - this isolates the check
    # constraint specifically, not an incidental FK violation. The new
    # page-feedback shape deliberately allows neither id to be set.
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)
    batch = client.post(
        f"/practice/{course_id}/batch", headers=auth, json={"size": 1}
    )
    real_practice_item_id = batch.json()["items"][0]["id"]

    with SessionLocal() as db:
        both = ContentIssueReport(
            reporter_user_id=user_id(auth),
            exercise_id=seeded_exercise_id(),
            practice_item_id=real_practice_item_id,
            category="other",
        )
        db.add(both)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    with SessionLocal() as db:
        neither = ContentIssueReport(
            reporter_user_id=None,
            page_path="/home",
            category="general_feedback",
        )
        db.add(neither)
        db.commit()
        assert neither.id is not None


def test_admin_issue_listing_shows_both_exercise_and_practice_item_reports(
    client, admin, auth
):
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)
    batch = client.post(
        f"/practice/{course_id}/batch", headers=auth, json={"size": 1}
    )
    practice_item_id = batch.json()["items"][0]["id"]

    exercise_report = client.post(
        f"/exercises/{seeded_exercise_id()}/report",
        headers=auth,
        json={"category": "other"},
    )
    assert exercise_report.status_code == 201
    practice_report = client.post(
        f"/practice/items/{practice_item_id}/report",
        headers=auth,
        json={"category": "other"},
    )
    assert practice_report.status_code == 201

    listing = client.get("/admin/content/issues?status=open&limit=200", headers=admin)
    assert listing.status_code == 200
    by_id = {row["id"]: row for row in listing.json()}

    exercise_row = by_id[exercise_report.json()["id"]]
    assert exercise_row["exercise_id"] is not None
    assert exercise_row["practice_item_id"] is None

    practice_row = by_id[practice_report.json()["id"]]
    assert practice_row["practice_item_id"] == practice_item_id
    assert practice_row["exercise_id"] is None
