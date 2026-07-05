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
