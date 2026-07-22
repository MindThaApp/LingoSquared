"""Regression locks for the 2026-07-22 seed split (two launch blockers).

BLOCKER 1 — `app/content/seed.py` used to import 4 hardcoded demo courses
on every run, including the REQUIRED `python -m app.content.seed` deploy
step. Live, that put a 3-unit "Farsi Foundations" stub next to the real
~50-unit "Farsi A1", and for prs->en the Latin-titled "English Foundations
for Dari Speakers" sorted BEFORE the real Arabic-titled course (`/courses`
orders by level, title), so CoursePickerPage's index-0 "start here" hint
pointed a Dari speaker at a 2-lesson stub. Fixed by splitting the required
bootstrap (languages + achievements) from the optional demo courses and
flipping the COMMAND-LINE default to off.

BLOCKER 2 — the demo Farsi course carried a `speaking_placeholder`
exercise. Placeholder.tsx's only control calls `onAnswer("")`, `""` grades
incorrect, and LessonRunnerPage's error recycling then re-showed the card
twice more — so a card reading "coming soon" told the learner "Incorrect"
three times and poisoned the completion screen's missedWords. Replaced
with a real, gradeable `speak_repeat`.

Runs against whatever DB `conftest.py` set up; every assertion here is
read-only or idempotent (bootstrap is create-missing-only). Per
backend/CLAUDE.md, run it against a UNIQUELY NAMED isolated test DB, never
the shared dev DB:

    docker compose exec -T db createdb -U lingosquared lingosquared_test_seedsplit
    docker compose run --rm api sh -c \
      'DATABASE_URL=postgresql+psycopg://lingosquared:...@db:5432/lingosquared_test_seedsplit \
       python -m pytest -q tests/test_seed_courses.py'
"""
from sqlalchemy import func, select

from app.content import seed as seed_module
from app.db.session import SessionLocal
from app.models import Achievement, Course, Exercise, Language, Lesson, Unit

DEMO_TITLES = {
    "Farsi Foundations",
    "Dari Foundations",
    "Dari Elementary",
    "English Foundations for Dari Speakers",
}

PLACEHOLDER_TYPES = {"listening_placeholder", "speaking_placeholder"}


def _iter_demo_exercises():
    for course in seed_module.DEMO_COURSES["courses"]:
        for unit in course["units"]:
            for lesson in unit["lessons"]:
                for exercise in lesson["exercises"]:
                    yield course["title"], unit["title"], lesson["title"], exercise


class _Spy:
    """Records calls without touching the database."""

    def __init__(self):
        self.calls = 0

    def __call__(self, db):
        self.calls += 1
        return 0


# ---------------------------------------------------------------------
# BLOCKER 1 — the deploy path must never create demo courses
# ---------------------------------------------------------------------


def test_cli_does_not_seed_demo_courses_by_default(monkeypatch, capsys):
    """`python -m app.content.seed` with no arguments = the deploy step."""
    spy = _Spy()
    monkeypatch.setattr(seed_module, "seed_demo_courses", spy)
    monkeypatch.delenv(seed_module.DEMO_COURSES_ENV_VAR, raising=False)

    assert seed_module.cli([]) == 0

    assert spy.calls == 0, (
        "The bare CLI invocation is the REQUIRED deploy step in "
        "docs/PRE_DEPLOY_RUNBOOK.md — it must never create demo courses."
    )
    assert "SKIPPED" in capsys.readouterr().out


def test_cli_still_bootstraps_languages_and_achievements(monkeypatch):
    """The half the app genuinely cannot run without must still run."""
    monkeypatch.setattr(seed_module, "seed_demo_courses", _Spy())
    monkeypatch.delenv(seed_module.DEMO_COURSES_ENV_VAR, raising=False)

    seed_module.cli([])

    with SessionLocal() as db:
        for code, *_ in seed_module.LANGUAGES:
            assert db.get(Language, code) is not None, f"language {code} missing"
        for code, *_ in seed_module.ACHIEVEMENTS:
            assert db.scalar(
                select(Achievement).where(Achievement.code == code)
            ) is not None, f"achievement {code} missing"


def test_cli_flag_opts_demo_courses_back_in(monkeypatch):
    spy = _Spy()
    monkeypatch.setattr(seed_module, "seed_demo_courses", spy)
    monkeypatch.delenv(seed_module.DEMO_COURSES_ENV_VAR, raising=False)

    seed_module.cli(["--with-demo-courses"])

    assert spy.calls == 1


def test_env_var_opts_demo_courses_back_in(monkeypatch):
    spy = _Spy()
    monkeypatch.setattr(seed_module, "seed_demo_courses", spy)
    monkeypatch.setenv(seed_module.DEMO_COURSES_ENV_VAR, "1")

    seed_module.cli([])

    assert spy.calls == 1


def test_explicit_no_flag_beats_the_env_var(monkeypatch):
    spy = _Spy()
    monkeypatch.setattr(seed_module, "seed_demo_courses", spy)
    monkeypatch.setenv(seed_module.DEMO_COURSES_ENV_VAR, "1")

    seed_module.cli(["--no-demo-courses"])

    assert spy.calls == 0


def test_env_var_only_opts_in_on_truthy_values(monkeypatch):
    for value in ("", "0", "false", "no", "off", " "):
        monkeypatch.setenv(seed_module.DEMO_COURSES_ENV_VAR, value)
        assert seed_module.demo_courses_opted_in() is False, value
    for value in ("1", "true", "TRUE", "yes", "on", " 1 "):
        monkeypatch.setenv(seed_module.DEMO_COURSES_ENV_VAR, value)
        assert seed_module.demo_courses_opted_in() is True, value
    monkeypatch.delenv(seed_module.DEMO_COURSES_ENV_VAR, raising=False)
    assert seed_module.demo_courses_opted_in() is False


def test_in_process_main_still_defaults_to_demo_courses(monkeypatch):
    """Deliberate asymmetry — do not "fix" this without the test lane.

    backend/tests/conftest.py does `from app.content.seed import main as
    seed` and calls `seed()` as its session fixture; test_backend.py's
    `test_dari_pair_returns_a1_and_a2_courses` and the e2e Playwright
    suite then assert those courses exist. Only the CLI default flipped.
    """
    spy = _Spy()
    monkeypatch.setattr(seed_module, "seed_demo_courses", spy)

    seed_module.main()

    assert spy.calls == 1


def test_bootstrap_is_create_missing_only():
    """Re-running the deploy step must not duplicate or wipe anything."""
    with SessionLocal() as db:
        before = (
            db.scalar(select(func.count()).select_from(Language)),
            db.scalar(select(func.count()).select_from(Achievement)),
            db.scalar(select(func.count()).select_from(Course)),
        )
        created = seed_module.bootstrap(db)
        after = (
            db.scalar(select(func.count()).select_from(Language)),
            db.scalar(select(func.count()).select_from(Achievement)),
            db.scalar(select(func.count()).select_from(Course)),
        )

    assert created == (0, 0), "already-seeded stack should create nothing new"
    assert before == after


# ---------------------------------------------------------------------
# BLOCKER 2 — no dead "coming soon" cards in the seed data
# ---------------------------------------------------------------------


def test_seed_data_has_no_placeholder_exercises():
    offenders = [
        f"{course} / {unit} / {lesson}: {exercise['type']}"
        for course, unit, lesson, exercise in _iter_demo_exercises()
        if exercise["type"] in PLACEHOLDER_TYPES
    ]
    assert offenders == [], (
        "listening_placeholder/speaking_placeholder render Placeholder.tsx, "
        "whose only control submits \"\" — which grades INCORRECT and is then "
        "recycled twice by LessonRunnerPage's error recycling. A learner is "
        "told 'Incorrect' three times on a card that says 'coming soon'. "
        f"Offending seed exercises: {offenders}"
    )


def test_every_seed_exercise_has_a_gradeable_answer():
    """The root cause of blocker 2, generalised: an exercise whose correct
    answer is empty can never be answered correctly."""
    for course, unit, lesson, exercise in _iter_demo_exercises():
        answer = exercise["correct_response"]
        where = f"{course} / {unit} / {lesson} / order {exercise['order']}"
        assert answer not in ("", None, []), f"{where} has no correct answer"


def test_seeded_demo_courses_contain_no_placeholder_exercises_in_db():
    """Same check, but against what actually landed in the database."""
    with SessionLocal() as db:
        rows = db.execute(
            select(Course.title, Exercise.type)
            .join(Unit, Unit.course_id == Course.id)
            .join(Lesson, Lesson.unit_id == Unit.id)
            .join(Exercise, Exercise.lesson_id == Lesson.id)
            .where(Course.title.in_(DEMO_TITLES))
        ).all()

    offenders = [
        (title, str(getattr(kind, "value", kind)))
        for title, kind in rows
        if str(getattr(kind, "value", kind)) in PLACEHOLDER_TYPES
    ]
    assert offenders == [], offenders
