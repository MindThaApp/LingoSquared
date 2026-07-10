from datetime import datetime

from sqlalchemy import func, select

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import (
    ContentIssueReport,
    Course,
    Exercise,
    Lesson,
    Unit,
)


def seeded_exercise_id():
    with SessionLocal() as db:
        return db.scalar(select(Exercise.id).order_by(Exercise.id))


def create_report(client, auth, exercise_id=None):
    exercise_id=exercise_id or seeded_exercise_id()
    response=client.post(
        f"/exercises/{exercise_id}/report",
        headers={**auth,"User-Agent":"LingoSquared-Test/1.0","Accept-Language":"fa"},
        json={
            "category":"wrong_answer_key",
            "description":"My valid response was rejected.",
            "learner_response":{"response":"learner answer"},
        },
    )
    assert response.status_code==201
    return exercise_id,response.json()


def test_successful_content_issue_report_creation(client,auth):
    exercise_id,result=create_report(client,auth)
    assert result["status"]=="open"
    assert set(result)=={"id","status"}

    with SessionLocal() as db:
        issue=db.get(ContentIssueReport,result["id"])
        assert issue is not None
        assert issue.reporter_user_id==decode_token(auth["Authorization"].split()[1])
        assert issue.exercise_id==exercise_id
        assert issue.practice_item_id is None
        assert issue.page_path is None
        assert issue.category=="wrong_answer_key"
        assert issue.description=="My valid response was rejected."
        assert issue.learner_response=={"response":"learner answer"}
        assert issue.client_context=={
            "user_agent":"LingoSquared-Test/1.0",
            "accept_language":"fa",
        }
        assert issue.content_release_id is None
        assert issue.content_key_id is None
        assert issue.attempt_id is None


def test_anonymous_general_feedback_creates_page_level_report(client):
    response=client.post(
        "/feedback",
        json={
            "category":"app_bug",
            "description":"The next button does nothing.",
            "page_path":"/lessons/abc123",
            "client_context":{"viewport":{"width":390,"height":844}},
        },
    )
    assert response.status_code==201, response.text
    result=response.json()
    assert result["status"]=="open"
    assert set(result)=={"id","status"}

    with SessionLocal() as db:
        issue=db.get(ContentIssueReport,result["id"])
        assert issue is not None
        assert issue.reporter_user_id is None
        assert issue.exercise_id is None
        assert issue.practice_item_id is None
        assert issue.page_path=="/lessons/abc123"
        assert issue.category=="app_bug"
        assert issue.description=="The next button does nothing."
        assert issue.client_context=={"viewport":{"width":390,"height":844}}


def test_general_feedback_with_foreign_or_invalid_token_degrades_to_anonymous(client):
    # A token minted by a DIFFERENT backend's signing key (the exact
    # "many independent local installs all point feedback at one central
    # collector" scenario from docs/CONTRACT.md) must never 401 here --
    # it must silently resolve to an anonymous report, same as no token
    # at all. This is why /feedback uses lenient_current_user, not
    # optional_current_user (which 401s on a present-but-invalid token,
    # correct for its other call site but wrong for this one).
    response=client.post(
        "/feedback",
        headers={"Authorization":"Bearer not-a-real-token"},
        json={
            "category":"app_bug",
            "page_path":"/home",
        },
    )
    assert response.status_code==201, response.text

    with SessionLocal() as db:
        issue=db.get(ContentIssueReport,response.json()["id"])
        assert issue is not None
        assert issue.reporter_user_id is None


def test_authenticated_general_feedback_sets_reporter_user_id(client,auth):
    response=client.post(
        "/feedback",
        headers=auth,
        json={
            "category":"general_feedback",
            "description":"This screen could use clearer wording.",
            "page_path":"/home",
            "client_context":{"locale":"en-GB"},
        },
    )
    assert response.status_code==201, response.text

    with SessionLocal() as db:
        issue=db.get(ContentIssueReport,response.json()["id"])
        assert issue is not None
        assert issue.reporter_user_id==decode_token(auth["Authorization"].split()[1])
        assert issue.exercise_id is None
        assert issue.practice_item_id is None
        assert issue.page_path=="/home"
        assert issue.category=="general_feedback"
        assert issue.client_context=={"locale":"en-GB"}


def test_admin_issue_listing_includes_page_path_for_general_feedback(client,admin):
    response=client.post(
        "/feedback",
        json={
            "category":"app_bug",
            "description":"The settings page is blank.",
            "page_path":"/settings",
            "client_context":{"route_state":"empty"},
        },
    )
    assert response.status_code==201, response.text

    listing=client.get("/admin/content/issues?status=open&limit=200",headers=admin)
    assert listing.status_code==200, listing.text
    by_id={issue["id"]:issue for issue in listing.json()}
    row=by_id[response.json()["id"]]
    assert row["reporter_user_id"] is None
    assert row["exercise_id"] is None
    assert row["practice_item_id"] is None
    assert row["page_path"]=="/settings"


def test_content_admin_routes_reject_non_admin(client,auth):
    _,result=create_report(client,auth)
    responses=[
        client.get("/admin/content/issues",headers=auth),
        client.patch(
            f"/admin/content/issues/{result['id']}",
            headers=auth,
            json={"status":"triaged"},
        ),
        client.get("/admin/content/coverage",headers=auth),
    ]
    assert all(response.status_code==403 for response in responses)
    assert all(response.json()["error"]["code"]=="admin_required" for response in responses)


def test_content_issue_status_transitions_set_server_timestamps(client,auth,admin):
    _,result=create_report(client,auth)

    triaged=client.patch(
        f"/admin/content/issues/{result['id']}",
        headers=admin,
        json={"status":"triaged","triage_notes":"Confirmed by reviewer."},
    )
    assert triaged.status_code==200
    triaged_body=triaged.json()
    assert triaged_body["status"]=="triaged"
    assert triaged_body["triage_notes"]=="Confirmed by reviewer."
    assert triaged_body["triaged_at"] is not None
    assert triaged_body["resolved_at"] is None

    resolved=client.patch(
        f"/admin/content/issues/{result['id']}",
        headers=admin,
        json={"status":"resolved"},
    )
    assert resolved.status_code==200
    resolved_body=resolved.json()
    assert resolved_body["status"]=="resolved"
    assert resolved_body["resolved_at"] is not None
    assert datetime.fromisoformat(resolved_body["resolved_at"])>=datetime.fromisoformat(triaged_body["triaged_at"])

    with SessionLocal() as db:
        issue=db.get(ContentIssueReport,result["id"])
        assert issue.triaged_at is not None
        assert issue.resolved_at is not None


def test_admin_issue_listing_enriches_exercise_context(client,auth,admin):
    # Triage enrichment (docs/CONTRACT.md "Issue-triage enrichment",
    # 2026-07-10): the list endpoint resolves the referenced exercise's
    # prompt + answer key and counts open reports against the same
    # exercise, so an admin never has to psql a raw UUID to understand a
    # report. Two reports against the same exercise -> open_report_count 2
    # on both.
    exercise_id,first=create_report(client,auth)
    _,second=create_report(client,auth,exercise_id=exercise_id)

    with SessionLocal() as db:
        exercise=db.get(Exercise,exercise_id)
        expected_prompt=exercise.prompt
        expected_correct=exercise.correct_response

    listing=client.get("/admin/content/issues?status=open&limit=200",headers=admin)
    assert listing.status_code==200, listing.text
    by_id={issue["id"]:issue for issue in listing.json()}
    for report_id in (first["id"],second["id"]):
        row=by_id[report_id]
        assert row["exercise_prompt"]==expected_prompt
        assert row["exercise_correct_response"]==expected_correct
        assert row["open_report_count"]>=2
        assert row["practice_item_prompt"] is None
        # learner_response was always returned here -- pin it so the field
        # the admin UI now renders can't silently vanish from the payload.
        assert row["learner_response"]=={"response":"learner answer"}

    # Page-level feedback has no content to resolve: all enrichment
    # fields stay null rather than erroring.
    feedback=client.post(
        "/feedback",
        json={"category":"app_bug","page_path":"/enrichment-null-check"},
    )
    assert feedback.status_code==201, feedback.text
    listing=client.get("/admin/content/issues?status=open&limit=200",headers=admin)
    page_row=next(issue for issue in listing.json() if issue["id"]==feedback.json()["id"])
    assert page_row["exercise_prompt"] is None
    assert page_row["exercise_correct_response"] is None
    assert page_row["practice_item_prompt"] is None
    assert page_row["open_report_count"] is None


def test_content_issue_list_filters(client,auth,admin):
    _,result=create_report(client,auth)

    open_issues=client.get(
        "/admin/content/issues?status=open&category=wrong_answer_key&limit=20&offset=0",
        headers=admin,
    )
    assert open_issues.status_code==200
    assert any(issue["id"]==result["id"] for issue in open_issues.json())

    excluded=client.get(
        "/admin/content/issues?status=resolved",
        headers=admin,
    )
    assert excluded.status_code==200
    assert all(issue["id"]!=result["id"] for issue in excluded.json())


def test_content_coverage_returns_seeded_aggregates(client,auth,admin):
    exercise_id,_=create_report(client,auth)

    with SessionLocal() as db:
        course=db.scalar(
            select(Course)
            .join(Unit,Unit.course_id==Course.id)
            .join(Lesson,Lesson.unit_id==Unit.id)
            .join(Exercise,Exercise.lesson_id==Lesson.id)
            .where(Exercise.id==exercise_id)
        )
        pair=(course.source_language,course.target_language)
        expected_courses=db.scalar(
            select(func.count(Course.id)).where(
                Course.source_language==pair[0],
                Course.target_language==pair[1],
            )
        )
        expected_units=db.scalar(
            select(func.count(Unit.id))
            .join(Course,Course.id==Unit.course_id)
            .where(
                Course.source_language==pair[0],
                Course.target_language==pair[1],
            )
        )
        expected_lessons=db.scalar(
            select(func.count(Lesson.id))
            .join(Unit,Unit.id==Lesson.unit_id)
            .join(Course,Course.id==Unit.course_id)
            .where(
                Course.source_language==pair[0],
                Course.target_language==pair[1],
            )
        )
        expected_open_issues=db.scalar(
            select(func.count(ContentIssueReport.id))
            .join(Exercise,Exercise.id==ContentIssueReport.exercise_id)
            .join(Lesson,Lesson.id==Exercise.lesson_id)
            .join(Unit,Unit.id==Lesson.unit_id)
            .join(Course,Course.id==Unit.course_id)
            .where(
                Course.source_language==pair[0],
                Course.target_language==pair[1],
                ContentIssueReport.status=="open",
            )
        )

    response=client.get("/admin/content/coverage",headers=admin)
    assert response.status_code==200
    rows=response.json()
    assert rows
    row=next(
        item for item in rows
        if (item["source_language"],item["target_language"])==pair
    )
    assert row=={
        "source_language":pair[0],
        "target_language":pair[1],
        "course_count":expected_courses,
        "total_unit_count":expected_units,
        "total_lesson_count":expected_lessons,
        "open_issue_count":expected_open_issues,
    }
    assert all(item["course_count"]>=1 for item in rows)
    assert all(item["total_unit_count"]>=1 for item in rows)
    assert all(item["total_lesson_count"]>=1 for item in rows)
