from app.db.session import SessionLocal
from app.models import Exercise


def multi_answer_payload():
    return {
        "courses": [
            {
                "source_language": "en",
                "target_language": "fa",
                "title": "Multi-answer grading regression",
                "level": "A1",
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
                                                    "text": "سلام",
                                                    "language_code": "fa",
                                                    "direction": "rtl",
                                                }
                                            ]
                                        },
                                        "correct_response": {
                                            "canonical": "salam",
                                            "accepted": [
                                                "salam",
                                                "salâm",
                                                "salām",
                                                "salaam",
                                            ],
                                        },
                                        "feedback": (
                                            "Several common transliterations "
                                            "are accepted."
                                        ),
                                        "xp": 10,
                                    }
                                ],
                            }
                        ],
                    }
                ],
                "content_items": [],
            }
        ]
    }


def imported_exercise_id(client, admin):
    imported = client.post(
        "/admin/content/import",
        headers=admin,
        json=multi_answer_payload(),
    )
    assert imported.status_code == 200
    assert imported.json()["imported_courses"] == 1

    courses = client.get("/courses?source=en&target=fa").json()
    course = next(
        item
        for item in courses
        if item["title"] == "Multi-answer grading regression"
    )
    units = client.get(f"/courses/{course['id']}/units").json()
    lessons = client.get(f"/units/{units[0]['id']}/lessons").json()
    detail = client.get(f"/lessons/{lessons[0]['id']}").json()
    return detail["exercises"][0]["id"]


def test_all_multi_answer_variants_grade_and_api_returns_canonical(
    client,
    admin,
    auth,
):
    exercise_id = imported_exercise_id(client, admin)

    awards = []
    for variant in ("salam", "salâm", "salām", "salaam"):
        response = client.post(
            f"/exercises/{exercise_id}/answer",
            headers=auth,
            json={"response": variant},
        )
        assert response.status_code == 200
        assert response.json()["correct"] is True
        assert response.json()["correct_response"] == "salam"
        awards.append(response.json()["xp_awarded"])

    assert awards == [10, 1, 1, 1]

    wrong = client.post(
        f"/exercises/{exercise_id}/answer",
        headers=auth,
        json={"response": "wrong"},
    )
    assert wrong.status_code == 200
    assert wrong.json()["correct"] is False
    assert wrong.json()["correct_response"] == "salam"
    assert wrong.json()["xp_awarded"] == 0

    with SessionLocal() as db:
        exercise = db.get(Exercise, exercise_id)
        assert exercise.correct_response == {
            "canonical": "salam",
            "accepted": ["salam", "salâm", "salām", "salaam"],
        }
