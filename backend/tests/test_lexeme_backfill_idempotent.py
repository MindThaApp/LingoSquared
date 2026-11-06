"""Rerunning a shared-runner lexeme backfill must be a no-op.

Regression: the X-fa backfills (de/es/fr/it/nl/pl/ro/ru-fa) emit specs that
carry language_code 'en' (English tokens inside a Farsi course) while the
existing-row lookup filtered on the TARGET language, so a second run missed
the rows and hit uq_lexemes_course_language_token_pos.

Needs the repo scripts: skipped unless LINGO_REPO_ROOT (or a sibling
scripts/ dir) is available, like test_content_answer_shapes.py.
"""
import importlib.util
import os
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import Course, Language, Lesson, Lexeme, Unit


def _scripts_dir() -> Path:
    root = os.environ.get("LINGO_REPO_ROOT")
    return Path(root) / "scripts" if root else Path(__file__).resolve().parents[2] / "scripts"


def _load_common():
    path = _scripts_dir() / "_target_lexeme_backfill_common.py"
    if not path.exists():
        pytest.skip("repo scripts/ not available (set LINGO_REPO_ROOT)")
    spec = importlib.util.spec_from_file_location("target_lexeme_backfill_common_t", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:  # e.g. PyYAML missing in the image
        pytest.skip(f"backfill runner dependency missing: {exc}")
    return module


def _spec(token, language, pos="noun", unit=1, lesson=1):
    return {
        "level": "a1", "unit_order": unit, "lesson_order": lesson,
        "lesson_content_key": f"t.a1.unit{unit:02d}.lesson{lesson:02d}",
        "content_key": f"t.item.{token}", "token": token, "language_code": language,
        "part_of_speech": pos, "english_gloss": f"gloss {token}",
        "agreement_tags": {"semantic": [f"w_{token}"]},
    }


def test_backfill_twice_is_noop_with_mixed_language_specs(monkeypatch):
    common = _load_common()
    title = "Idempotency Test (de-fa)"
    with SessionLocal() as db:
        for code, script, direction in (("de", "latin", "ltr"), ("fa", "arabic", "rtl")):
            if db.get(Language, code) is None:
                db.add(Language(code=code, name=code, script=script, direction=direction))
        db.flush()
        course = Course(source_language="de", target_language="fa", title=title)
        db.add(course)
        db.flush()
        unit = Unit(course_id=course.id, title="u1", order=1)
        db.add(unit)
        db.flush()
        db.add(Lesson(unit_id=unit.id, title="l1", order=1))
        db.commit()
        course_id = course.id

    monkeypatch.setattr(common, "course_title", lambda group: title)
    specs = [_spec("سلام", "fa"), _spec("persian", "en", "adjective"), _spec("hello", "en")]

    def run():
        return common.run(
            description="t", source_language="de", target_language="fa",
            levels={"a1": "de-fa"}, iter_specs=lambda: [dict(s) for s in specs], argv=[],
        )

    def snapshot():
        with SessionLocal() as db:
            rows = db.scalars(select(Lexeme).where(Lexeme.course_id == course_id)).all()
            dupes = db.execute(
                select(Lexeme.language_code, Lexeme.token, Lexeme.part_of_speech)
                .where(Lexeme.course_id == course_id)
                .group_by(Lexeme.language_code, Lexeme.token, Lexeme.part_of_speech)
                .having(func.count() > 1)
            ).all()
            return sorted((r.id, r.language_code, r.token, r.part_of_speech, r.english_gloss) for r in rows), dupes

    assert run() == 0
    first, dupes = snapshot()
    assert len(first) == 3 and not dupes
    assert run() == 0  # second run must succeed (used to raise UniqueViolation)
    second, dupes = snapshot()
    assert second == first and not dupes  # same rows, same ids, nothing added
