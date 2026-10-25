"""Units query count, startup validation, /health/ready, maintenance jobs."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event, select

from app.db.session import SessionLocal, engine
from app.main import validate_startup_settings
from app.maintenance import prune_practice_items, prune_social_nonces
from app.models import PracticeItem, SocialLoginNonce


class _Settings:
    app_env = "production"
    jwt_secret = "x" * 40
    database_url = "postgresql+psycopg://u:strong-pw@db:5432/x"


def _settings(**kw):
    ns = type("S", (), {**vars(_Settings), **kw})
    return ns


def test_startup_accepts_strong_production_settings():
    validate_startup_settings(_settings())


@pytest.mark.parametrize(
    "kw",
    [
        {"jwt_secret": "short"},
        {"jwt_secret": "x" * 31},
        {"jwt_secret": "replace-with-a-long-random-secret"},
        {"database_url": "postgresql+psycopg://u:change-me@db:5432/x"},
        {"app_env": "staging", "jwt_secret": "short"},
    ],
)
def test_startup_rejects_weak_production_settings(kw):
    with pytest.raises(RuntimeError, match="Refusing to start"):
        validate_startup_settings(_settings(**kw))


@pytest.mark.parametrize("env", ["dev", "development", "test", "TEST"])
def test_startup_allows_weak_settings_in_dev_and_test(env):
    validate_startup_settings(
        _settings(app_env=env, jwt_secret="s", database_url="postgresql+psycopg://u:change-me@db/x")
    )


def test_health_is_static_and_ready_checks_db(client):
    assert client.get("/health").json() == {"status": "ok"}
    r = client.get("/health/ready")
    assert r.status_code == 200 and r.json()["database"] == "ok"


def test_health_ready_503_when_db_down(client, monkeypatch):
    import app.main as main

    class Broken:
        def connect(self):
            raise RuntimeError("down")

    monkeypatch.setattr(main, "engine", Broken())
    r = client.get("/health/ready")
    assert r.status_code == 503
    assert client.get("/health").status_code == 200


def test_units_query_count_is_flat(client, auth):
    courses = client.get("/courses").json()
    course = max(courses, key=lambda c: c.get("unit_count", 0) if isinstance(c, dict) else 0)
    statements = []

    def count(conn, cursor, statement, *a):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        r = client.get(f"/courses/{course['id']}/units", headers=auth)
    finally:
        event.remove(engine, "before_cursor_execute", count)
    assert r.status_code == 200
    units = r.json()
    assert len(units) >= 2, "need a multi-unit course to prove the query count is flat"
    # course lookup + units + lesson counts + completed counts + passed
    # checkpoints + auth/user lookup; independent of the number of units.
    assert len(statements) <= 8, f"{len(statements)} queries for {len(units)} units"


def test_prune_practice_items_and_nonces():
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        template = db.scalar(select(PracticeItem.template_id).limit(1))
        # Existing rows may be absent in a fresh DB; just verify the call
        # runs and leaves unexpired rows alone.
        before = db.scalar(select(PracticeItem.id).where(PracticeItem.expires_at > now).limit(1))
        prune_practice_items(db, now)
        if before:
            assert db.get(PracticeItem, before) is not None
        db.add(SocialLoginNonce(nonce_sha256="a" * 64, expires_at=now - timedelta(minutes=1)))
        db.add(SocialLoginNonce(nonce_sha256="b" * 64, expires_at=now + timedelta(minutes=5)))
        db.commit()
        assert prune_social_nonces(db, now) >= 1
        assert db.get(SocialLoginNonce, "a" * 64) is None
        assert db.get(SocialLoginNonce, "b" * 64) is not None
        db.delete(db.get(SocialLoginNonce, "b" * 64))
        db.commit()


def test_units_locked_matches_speaking_unlocked(client, auth):
    """The grouped-query rewrite must agree with the reference rule, both for
    a fresh learner and after completing the first reading units."""
    from app.api.router import speaking_unlocked
    from app.models import Lesson, LessonProgress, Unit, User
    from app.models.entities import UnitSection

    from app.core.security import decode_token

    me = {"id": decode_token(auth["Authorization"].split()[1])}
    with SessionLocal() as db:
        for course in client.get("/courses").json():
            core = list(db.scalars(select(Unit).where(Unit.course_id == course["id"], Unit.track == "core").order_by(Unit.order)))
            if not any(u.section == UnitSection.speaking for u in core):
                continue
            for stage in range(2):
                body = client.get(f"/courses/{course['id']}/units", headers=auth).json()
                for u in body:
                    unit = db.get(Unit, u["id"])
                    if unit.track == "core" and unit.section == UnitSection.speaking:
                        assert u["locked"] == (not speaking_unlocked(db, course["id"], me["id"], unit.order))
                if stage == 0:
                    for unit in core:
                        if unit.section == UnitSection.reading_writing:
                            for lesson_id in db.scalars(select(Lesson.id).where(Lesson.unit_id == unit.id)):
                                db.add(LessonProgress(user_id=me["id"], lesson_id=lesson_id, completed_at=datetime.now(timezone.utc)))
                    db.commit()
                    after = client.get(f"/courses/{course['id']}/units", headers=auth).json()
                    assert any(not u["locked"] for u in after if u["section"] == "speaking" and u["track"] == "core")
            return
    pytest.skip("no course with a core speaking unit")
