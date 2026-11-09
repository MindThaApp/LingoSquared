"""Tests for phantom introduced-token detection."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _phantom_introduced_tokens_check as chk  # noqa: E402


def _write_realization(root: Path, exercises: list[dict]) -> None:
    language = root / "nl"
    language.mkdir(parents=True)
    document = {
        "units": [{
            "content_key": "nl.a1.unit01",
            "lessons": [{
                "teaching": [{
                    "content_key": "nl.a1.unit01.teach.phantom",
                    "kind": "vocabulary",
                    "target": "school",
                    "introduced_tokens": ["station"],
                }],
                "exercises": exercises,
            }],
        }]
    }
    (language / "a1.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")


def test_phantom_used_by_production_exercise_is_violation(tmp_path, monkeypatch):
    _write_realization(tmp_path, [{
        "content_key": "nl.a1.unit01.ex.translate",
        "type": "translation",
        "accepted_answers": [{"value": "station", "status": "correct"}],
    }])
    monkeypatch.setattr(chk, "REALIZATIONS_DIR", tmp_path)
    monkeypatch.setattr(chk, "REPO_ROOT", tmp_path)
    violations, notes = chk.find_results()
    assert len(violations) == 1
    assert violations[0].phantom.token == "station"
    assert violations[0].use.field == "accepted_answers"
    assert notes == []


def test_phantom_without_later_use_is_metadata_note(tmp_path, monkeypatch):
    _write_realization(tmp_path, [])
    monkeypatch.setattr(chk, "REALIZATIONS_DIR", tmp_path)
    monkeypatch.setattr(chk, "REPO_ROOT", tmp_path)
    violations, notes = chk.find_results()
    assert violations == []
    assert [item.token for item in notes] == ["station"]


def test_normalization_handles_diacritics_and_arabic_variants():
    assert chk._surface_appears("café", ["CAFE"])
    assert chk._surface_appears("مي‌روم", ["میروم"])

