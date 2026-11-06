"""Seeds one extra demo course so the a11y audit reaches exercise types the stock demo courses lack.
Run inside the api container: python - < extra_course.py"""
from app.db.session import SessionLocal
from app.schemas.api import ImportRequest
from app.content.service import import_content


def block(text, code):
    return {"text": text, "language_code": code, "direction": "rtl" if code in {"ar", "fa", "prs"} else "ltr"}


def teach(kind, target, tc, tr, sc):
    return {"kind": kind, "title": None, "text_blocks": [block(target, tc), block(tr, sc)], "note": None}


COURSE = {"courses": [{
    "source_language": "en", "target_language": "ar", "title": "Arabic A11y Fixture", "description": "Fixture for the accessibility audit.", "level": "A1",
    "units": [{"title": "Basics", "order": 1, "section": "reading_writing", "lessons": [{
        "title": "Matching and choosing", "order": 1,
        "teaching": [teach("vocabulary", "مرحبا", "ar", "hello", "en"), teach("vocabulary", "شكرا", "ar", "thank you", "en")],
        "exercises": [
            {"type": "matching_pairs", "order": 1, "prompt": {"text_blocks": [block("Match each word.", "en")], "pairs": [{"left": "مرحبا", "right": "hello"}, {"left": "شكرا", "right": "thank you"}], "answer_language_code": "ar"}, "correct_response": {"مرحبا": "hello", "شكرا": "thank you"}, "xp": 10},
            {"type": "multiple_choice", "order": 2, "prompt": {"text_blocks": [block("Choose the Arabic word for hello.", "en")], "options": ["مرحبا", "شكرا"]}, "correct_response": "مرحبا", "xp": 10},
            {"type": "word_order", "order": 3, "prompt": {"text_blocks": [block("Arrange: thank you hello", "en")], "word_bank": ["مرحبا", "شكرا"]}, "correct_response": ["شكرا", "مرحبا"], "xp": 10},
            {"type": "fill_in_blank", "order": 4, "prompt": {"text_blocks": [block("___ يا صديقي", "ar")]}, "correct_response": "مرحبا", "xp": 10},
        ]}]}],
    "content_items": [],
}]}
with SessionLocal() as db:
    n, errors, _ = import_content(db, ImportRequest.model_validate(COURSE))
    print("extra course created:", n, errors)
