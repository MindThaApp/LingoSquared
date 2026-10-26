"""inject must be additive across levels: manifests and backfill keep earlier levels."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "derive_direction.py"

SIBLING_BACKFILL = '''#!/usr/bin/env python3
"""doc"""
LEVELS = {"a1": "de-en", "a2": "de-en-a2"}
EN_TARGET_TO_DE_GLOSS: dict[str, str] = {
    "hello": "hallo",
}
A2_GLOSSES: dict[str, str] = {
    "train": "Zug",
}
A2_SENSE_FIXES: dict[str, str] = {}
GLOSSES = EN_TARGET_TO_DE_GLOSS
GLOSSES_BY_LEVEL = {"a1": GLOSSES, "a2": {**GLOSSES, **A2_GLOSSES, **A2_SENSE_FIXES}}
'''


@pytest.fixture()
def dd(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("derive_direction_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "CONTENT", tmp_path / "docs/content")
    monkeypatch.setattr(mod, "MANIFEST", tmp_path / "scripts/manifest.d/content")
    monkeypatch.setattr(mod, "PRACTICE_MANIFEST", tmp_path / "scripts/manifest.d/practice")
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / "scripts/backfill_lexemes_de_en.py").write_text(SIBLING_BACKFILL, encoding="utf-8")
    return mod


def _args(level, work):
    return SimpleNamespace(sibling="de-en", new="es-en", levels=[level], allow_missing=False, work=str(work))


def _write_glosses(work, level):
    work.mkdir(parents=True, exist_ok=True)
    if level == "a1":
        items = [["#", "dict EN_TARGET_TO_DE_GLOSS"], ["g1", "hello", "hallo"]]
        tr = {"g1": "hola"}
    else:
        items = [["#", "dict EN_TARGET_TO_DE_GLOSS"], ["g1", "hello", "hallo"],
                 ["#", "dict A2_GLOSSES"], ["g3", "train", "Zug"]]
        tr = {"g1": "HOLA-REGENERATED", "g3": "tren"}
    (work / "glosses.src.json").write_text(json.dumps({"items": items}), encoding="utf-8")
    (work / "glosses.tr.json").write_text(json.dumps(tr), encoding="utf-8")


def _load_backfill(dd, root):
    ns: dict = {}
    exec((root / "scripts/backfill_lexemes_es_en.py").read_text(encoding="utf-8"), ns)
    return ns


def test_practice_manifest_merges_levels_sorted_without_duplicates(dd):
    dd.update_manifests({}, "es-en", ["docs/content/practice/es-en/a1_unit02.yaml", "docs/content/practice/es-en/a1_unit01.yaml"])
    dd.update_manifests({}, "es-en", ["docs/content/practice/es-en/a2_unit25.yaml", "docs/content/practice/es-en/a1_unit01.yaml"])
    line = (dd.PRACTICE_MANIFEST / "es-en.txt").read_text(encoding="utf-8").strip()
    name, paths = line.split("|")
    assert name == "es-en"
    assert paths.split() == [
        "docs/content/practice/es-en/a1_unit01.yaml",
        "docs/content/practice/es-en/a1_unit02.yaml",
        "docs/content/practice/es-en/a2_unit25.yaml",
    ]


def test_backfill_keeps_a1_after_injecting_a2(dd, tmp_path):
    work = tmp_path / "work"
    _write_glosses(work, "a1")
    dd.write_backfill(_args("a1", work), work, [])
    dest = tmp_path / "scripts/backfill_lexemes_es_en.py"
    # hand edit to an existing level
    dest.write_text(dest.read_text(encoding="utf-8").replace('"hola"', '"hola (hand edit)"'), encoding="utf-8")

    _write_glosses(work, "a2")
    dd.write_backfill(_args("a2", work), work, [])
    ns = _load_backfill(dd, tmp_path)
    assert list(ns["LEVELS"]) == ["a1", "a2"]
    assert ns["LEVELS"]["a1"] == "es-en" and ns["LEVELS"]["a2"] == "es-en-a2"
    assert ns["GLOSSES_BY_LEVEL"]["a1"]["hello"] == "hola (hand edit)"
    assert ns["GLOSSES_BY_LEVEL"]["a2"]["train"] == "tren"
    assert ns["A2_GLOSSES"] == {"train": "tren"}


def test_reinjecting_a_level_replaces_only_that_level(dd, tmp_path):
    work = tmp_path / "work"
    _write_glosses(work, "a1")
    dd.write_backfill(_args("a1", work), work, [])
    _write_glosses(work, "a2")
    dd.write_backfill(_args("a2", work), work, [])
    (work / "glosses.tr.json").write_text(json.dumps({"g1": "x", "g3": "tren2"}), encoding="utf-8")
    dd.write_backfill(_args("a2", work), work, [])
    ns = _load_backfill(dd, tmp_path)
    assert list(ns["LEVELS"]) == ["a1", "a2"]
    assert ns["GLOSSES_BY_LEVEL"]["a1"]["hello"] == "hola"
    assert ns["A2_GLOSSES"] == {"train": "tren2"}


def test_content_manifests_seeded_from_sibling(dd):
    dd.MANIFEST.mkdir(parents=True)
    (dd.MANIFEST / "de-en.txt").write_text("de-en|r1.yaml|o1.yaml\n", encoding="utf-8")
    (dd.MANIFEST / "de-en-a2.txt").write_text("de-en-a2|r2.yaml|o2.yaml\n", encoding="utf-8")
    (dd.MANIFEST / "es-en.txt").write_text("es-en|r1.yaml|mine.yaml\n", encoding="utf-8")
    created = dd.seed_content_manifests("de-en", "es-en", ["a1", "a2"])
    assert created == ["es-en-a2"]
    assert (dd.MANIFEST / "es-en-a2.txt").read_text(encoding="utf-8") == "es-en-a2|r2.yaml|o2.yaml\n"
    # existing files are never overwritten
    assert (dd.MANIFEST / "es-en.txt").read_text(encoding="utf-8") == "es-en|r1.yaml|mine.yaml\n"


def test_update_manifests_merges_units_incrementally(dd):
    """A second inject with --units must add its units to the group file, not replace it."""
    r = "docs/content/realizations/en/a1_unit%02d_x.yaml"
    o = "docs/content/overlays/es-en/a1_unit%02d.yaml"
    dd.update_manifests({"es-en": ([r % 1, r % 2], [o % 1, o % 2])}, "es-en", [])
    dd.update_manifests({"es-en": ([r % 15, r % 3], [o % 15, o % 3])}, "es-en", [])
    dd.update_manifests({"es-en": ([r % 15], [o % 15])}, "es-en", [])  # re-inject is idempotent
    line = (dd.MANIFEST / "es-en.txt").read_text(encoding="utf-8").strip()
    group, reals, ovs = line.split("|")
    assert group == "es-en"
    assert [p.split("/")[-1] for p in reals.split()] == [
        "a1_unit01_x.yaml", "a1_unit02_x.yaml", "a1_unit03_x.yaml", "a1_unit15_x.yaml"]
    assert [p.split("/")[-1] for p in ovs.split()] == [
        "a1_unit01.yaml", "a1_unit02.yaml", "a1_unit03.yaml", "a1_unit15.yaml"]
