from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import PracticeItem, PracticeTemplate
from test_endless_practice import (
    artifact,
    complete_via_api,
    create_course_with_lexemes,
    import_templates,
)


def matching_pairs_payload(title):
    return {
        "courses": [
            {
                "source_language": "en",
                "target_language": "nl",
                "title": title,
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
                                        "type": "matching_pairs",
                                        "order": 1,
                                        "prompt": {
                                            "text_blocks": [
                                                {
                                                    "text": "Match each Dutch form with its register.",
                                                    "language_code": "en",
                                                    "direction": "ltr",
                                                }
                                            ],
                                            "pairs": [
                                                {"left": "jij / je", "right": "informeel"},
                                                {"left": "u", "right": "formeel"},
                                            ],
                                        },
                                        # Real content authors have historically written
                                        # this as a list of {left,right} objects (matching
                                        # the prompt's `pairs` display shape) even though
                                        # the frontend submits - and CONTRACT.md documents
                                        # - a flat {left: right} pair-mapping. Both shapes
                                        # must grade correctly.
                                        "correct_response": [
                                            {"left": "jij / je", "right": "informeel"},
                                            {"left": "u", "right": "formeel"},
                                        ],
                                        "feedback": "Jij/je is informal; u is formal.",
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


def imported_exercise_id(client, admin, title):
    imported = client.post(
        "/admin/content/import",
        headers=admin,
        json=matching_pairs_payload(title),
    )
    assert imported.status_code == 200
    assert imported.json()["imported_courses"] == 1

    courses = client.get("/courses?source=en&target=nl").json()
    course = next(item for item in courses if item["title"] == title)
    units = client.get(f"/courses/{course['id']}/units").json()
    lessons = client.get(f"/units/{units[0]['id']}/lessons").json()
    detail = client.get(f"/lessons/{lessons[0]['id']}").json()
    return detail["exercises"][0]["id"]


def test_matching_pairs_grades_correct_from_flat_dict_submission(client, admin, auth):
    """Regression test: MatchingPairs.tsx submits a flat {left: right} dict
    (per CONTRACT.md's documented pair-mapping shape), but content authors
    write correct_response as a list of {left,right} objects. Before the
    fix, grade()'s generic dict-vs-list comparison always returned
    incorrect regardless of what the learner picked."""
    exercise_id = imported_exercise_id(client, admin, "Matching pairs regression 1")

    response = client.post(
        f"/exercises/{exercise_id}/answer",
        headers=auth,
        json={"response": {"jij / je": "informeel", "u": "formeel"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body["result"] == "correct"
    assert body["xp_awarded"] == 10


def test_matching_pairs_grades_incorrect_for_wrong_pairing(client, admin, auth):
    exercise_id = imported_exercise_id(client, admin, "Matching pairs regression 2")

    response = client.post(
        f"/exercises/{exercise_id}/answer",
        headers=auth,
        json={"response": {"jij / je": "formeel", "u": "informeel"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is False
    assert body["xp_awarded"] == 0


def test_matching_pairs_grades_correct_regardless_of_pair_order(client, admin, auth):
    exercise_id = imported_exercise_id(client, admin, "Matching pairs regression 3")

    response = client.post(
        f"/exercises/{exercise_id}/answer",
        headers=auth,
        json={"response": {"u": "formeel", "jij / je": "informeel"}},
    )
    assert response.status_code == 200
    assert response.json()["correct"] is True


def test_matching_pairs_grades_correct_from_list_of_pairs_submission(
    client, admin, auth
):
    """MatchingPairs.tsx submits pairs.map(p => ({left, right})) - a list of
    pair objects, matching how compiled lesson content authors correct_response
    (see the two tests above). But the Endless Practice engine's
    derive_answer() for matching_pairs (app/practice/service.py) produces a
    FLAT {token: gloss} dict as correct_response instead. Since both paths
    render through the same MatchingPairs.tsx component and grade through the
    same shared grade() function, canonical_pairs() must accept a
    list-of-pairs submission against a flat-dict correct_response too, or
    every Endless Practice matching_pairs item would always grade incorrect
    the mirror-image way."""
    course_id, lesson_id = create_course_with_lexemes(target="es")
    import_templates(client, admin, course_id, artifact(target="es"))
    complete_via_api(client, auth, lesson_id)

    # The sampler's due/mastery ladder doesn't guarantee matching_pairs shows
    # up in an arbitrary batch - isolate it by deactivating every other
    # template, same technique as
    # test_practice_import_is_idempotent_and_all_prompt_contracts_generate.
    with SessionLocal() as db:
        for template in db.scalars(
            select(PracticeTemplate).where(PracticeTemplate.course_id == course_id)
        ):
            template.active = template.type == "matching_pairs"
        db.commit()

    batch = client.post(
        f"/practice/{course_id}/batch", headers=auth, json={"size": 1}
    )
    assert batch.status_code == 200, batch.text
    assert batch.json()["items"], batch.text
    item = batch.json()["items"][0]
    assert item["type"] == "matching_pairs"
    pairs = item["prompt"]["pairs"]

    with SessionLocal() as db:
        stored = db.get(PracticeItem, item["id"])
        correct_response = stored.correct_response  # flat {token: gloss} dict

    list_submission = [
        {"left": pair["left"], "right": correct_response[pair["left"]]}
        for pair in pairs
    ]

    response = client.post(
        f"/practice/items/{item['id']}/answer",
        headers=auth,
        json={"response": list_submission},
    )
    assert response.status_code == 200, response.text
    assert response.json()["correct"] is True
