import re
from pathlib import Path

import pytest

from app.models.entities import ExerciseType


def test_frontend_exercise_renderer_handles_all_backend_types():
    # The standard `docker compose run api pytest` container only mounts
    # backend/ (see CLAUDE.md's backfill_lexemes.py footgun for the same
    # class of issue) -- frontend/ is invisible there, so this test can
    # only run when the full repo is mounted (e.g. the coordinator running
    # pytest directly on the host, or a container started with the
    # backfill_lexemes.py-style `-v "$(cd .. && pwd):/repo"` full-repo
    # mount). Skip rather than fail so the standard container-only test
    # run isn't permanently red for an environment constraint, not a
    # real regression.
    repo_root = Path(__file__).resolve().parents[2]
    renderer_path = (
        repo_root
        / "frontend"
        / "src"
        / "components"
        / "exercises"
        / "ExerciseRenderer.tsx"
    )
    if not renderer_path.exists():
        pytest.skip(
            f"{renderer_path} not visible in this container -- run with the "
            "full repo mounted (see backfill_lexemes.py's docstring for the "
            "exact -v flag) to actually exercise this check."
        )
    renderer = renderer_path.read_text(encoding="utf-8")
    registered_types = set(re.findall(r'case\s+"([^"]+)":', renderer))
    backend_types = {exercise_type.value for exercise_type in ExerciseType}

    assert backend_types <= registered_types, (
        "ExerciseRenderer is missing backend exercise type cases: "
        f"{sorted(backend_types - registered_types)}"
    )
