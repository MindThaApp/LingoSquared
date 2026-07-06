def word_order_payload(title, correct_response):
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
                                        "type": "word_order",
                                        "order": 1,
                                        "prompt": {
                                            "text_blocks": [
                                                {
                                                    "text": "Put the words in order to answer the phone as Omar.",
                                                    "language_code": "en",
                                                    "direction": "ltr",
                                                }
                                            ],
                                            "word_bank": ["Omar", "Hallo", "met"],
                                        },
                                        # Real content authors have historically written
                                        # this as a single space-joined string (matching
                                        # the prompt's spoken phrase) even though the
                                        # frontend (WordOrder.tsx) always submits a list
                                        # built purely from tile-click order. Both shapes
                                        # must grade correctly.
                                        "correct_response": correct_response,
                                        "feedback": "The complete phrase is Hallo, met Omar.",
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


def imported_exercise_id(client, admin, title, correct_response):
    imported = client.post(
        "/admin/content/import",
        headers=admin,
        json=word_order_payload(title, correct_response),
    )
    assert imported.status_code == 200
    assert imported.json()["imported_courses"] == 1

    courses = client.get("/courses?source=en&target=nl").json()
    course = next(item for item in courses if item["title"] == title)
    units = client.get(f"/courses/{course['id']}/units").json()
    lessons = client.get(f"/units/{units[0]['id']}/lessons").json()
    detail = client.get(f"/lessons/{lessons[0]['id']}").json()
    return detail["exercises"][0]["id"]


def test_word_order_grades_correct_against_a_string_shaped_correct_response(
    client, admin, auth
):
    """Real user-reported bug, 2026-07-07: a word_order exercise's correct
    answer was "Hallo, met Omar" - the learner arranged the tiles in exactly
    that order and it was still marked wrong. Root cause: WordOrder.tsx
    always submits `response` as a list built from tile-click order, but
    canonical_response() (scripts/compile_content.py) passes hand-authored
    correct_response/accepted_answers through completely unchanged - and the
    vast majority of hand-authored word_order content (146 of 173 word_order/
    listen_order exercises corpus-wide, confirmed by a full-corpus audit) is
    authored as a single space-joined string like "Hallo met Omar" rather
    than a token list matching word_bank. Before the fix, grade()'s generic
    `normalized(response)==normalized(correct)` compared a list against a
    string, which can never be equal in Python regardless of tile order -
    every one of those exercises was ungradeable-correct no matter what the
    learner picked."""
    exercise_id = imported_exercise_id(
        client, admin, "Word order string regression", "Hallo met Omar"
    )

    response = client.post(
        f"/exercises/{exercise_id}/answer",
        headers=auth,
        json={"response": ["Hallo", "met", "Omar"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body["result"] == "correct"
    assert body["xp_awarded"] == 10


def test_word_order_grades_incorrect_for_a_genuinely_wrong_tile_order(
    client, admin, auth
):
    exercise_id = imported_exercise_id(
        client, admin, "Word order string regression 2", "Hallo met Omar"
    )

    response = client.post(
        f"/exercises/{exercise_id}/answer",
        headers=auth,
        json={"response": ["Omar", "Hallo", "met"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is False
    assert body["xp_awarded"] == 0


def test_word_order_still_grades_correct_against_a_list_shaped_correct_response(
    client, admin, auth
):
    """A minority of hand-authored word_order content (and every Endless
    Practice-generated word_order item, via derive_answer()'s
    "ordered_slot_texts" kind) already authors correct_response as a token
    list matching word_bank order, which graded correctly before this fix -
    guards against a regression in the other direction."""
    exercise_id = imported_exercise_id(
        client, admin, "Word order list regression", ["Hallo", "met", "Omar"]
    )

    response = client.post(
        f"/exercises/{exercise_id}/answer",
        headers=auth,
        json={"response": ["Hallo", "met", "Omar"]},
    )
    assert response.status_code == 200
    assert response.json()["correct"] is True

    wrong = client.post(
        f"/exercises/{exercise_id}/answer",
        headers=auth,
        json={"response": ["met", "Hallo", "Omar"]},
    )
    assert wrong.status_code == 200
    assert wrong.json()["correct"] is False
