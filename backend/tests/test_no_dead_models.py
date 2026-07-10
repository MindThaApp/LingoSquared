"""Guard against dead ORM scaffolding accumulating again.

This project has now hit the same pattern four times: ORM models that
exist in app/models/entities.py (and therefore as real tables on every
database, because 0001_initial.py runs Base.metadata.create_all()
against the live model set) but are referenced by zero lines of actual
application code. Instances so far, all found by manual archaeology and
removed via guarded migrations:

1. AnswerSpec
2. MediaAsset / Dialogue / DialogueNode / DialogueEdge
3. DailyQuest / UserDailyQuestProgress  (dropped in migration 0019)
4. The 12 Phase 0 models (LearningObjective and friends, ContentRelease
   and friends, NotificationPreference, StreakFreeze*, SyncOperation)
   -- dropped in migration 0021.

This test converts that recurring archaeology into an automatic guard:
every mapped class registered on Base must be mentioned somewhere in
app/ outside its own defining module (and outside pure re-export
modules like app/models/__init__.py), or it must carry an explicit,
justified allowlist entry below.

Pure filesystem/regex scan -- no database needed.
"""

import re
from pathlib import Path

import app.models  # noqa: F401  -- ensures every model is registered
from app.db.session import Base

APP_DIR = Path(__file__).resolve().parents[1] / "app"

# Modules that never count as a "real" reference:
# - the model's own defining module (checked per-class below)
# - app/models/__init__.py, which star-re-exports everything and would
#   otherwise make every model look referenced.
_REEXPORT_ONLY = {APP_DIR / "models" / "__init__.py"}

# Models that legitimately have zero code references outside their
# definition. Every entry needs a real justification -- "we might use
# it later" does not qualify (that is exactly the dead-scaffolding
# pattern this test exists to block).
ALLOWLIST = {
    # learning_paths is FK-referenced by the live Course.learning_path_id
    # column (and by migration 0005), so the table is structurally
    # load-bearing even though no code path reads or writes LearningPath
    # rows today. Removing it means a schema/API change to Course --
    # a deliberate follow-up decision, not silent scaffolding.
    "LearningPath",
}


def _mapped_classes():
    return sorted(
        (mapper.class_ for mapper in Base.registry.mappers),
        key=lambda cls: cls.__name__,
    )


def _reference_counts():
    """Map model class name -> number of referencing files in app/."""
    classes = _mapped_classes()
    patterns = {
        cls.__name__: re.compile(rf"\b{re.escape(cls.__name__)}\b")
        for cls in classes
    }
    defining_files = {
        cls.__name__: Path(__import__(cls.__module__, fromlist=["_"]).__file__)
        for cls in classes
    }

    counts = {name: 0 for name in patterns}
    for path in APP_DIR.rglob("*.py"):
        if path in _REEXPORT_ONLY:
            continue
        text = path.read_text(encoding="utf-8")
        for name, pattern in patterns.items():
            if path == defining_files[name]:
                continue
            if pattern.search(text):
                counts[name] += 1
    return counts


def test_every_model_is_referenced_or_allowlisted():
    counts = _reference_counts()
    dead = sorted(
        name
        for name, count in counts.items()
        if count == 0 and name not in ALLOWLIST
    )
    assert not dead, (
        "ORM models with zero references in app/ outside their own "
        f"definition: {dead}. Either wire them into real code, or remove "
        "the model AND drop its table via a guarded migration (see 0019/"
        "0021 for the pattern -- 0001 runs create_all() against live "
        "models, so an unused model still creates a real table on every "
        "database). If a model genuinely must exist without code "
        "references, add it to ALLOWLIST in this test with a real "
        "justification."
    )


def test_allowlist_entries_are_still_dead():
    """A stale allowlist is scaffolding of its own -- once a model gains
    real references, its allowlist entry (and justification) should go."""
    counts = _reference_counts()
    stale = sorted(
        name
        for name in ALLOWLIST
        if counts.get(name, 0) > 0 or name not in counts
    )
    assert not stale, (
        f"ALLOWLIST entries that are no longer zero-reference models (or "
        f"no longer exist at all): {stale}. Remove them from ALLOWLIST."
    )
