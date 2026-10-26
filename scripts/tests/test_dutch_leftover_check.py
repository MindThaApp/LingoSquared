"""Tests for scripts/_dutch_leftover_check.py (Dutch text left in derived non-nl courses)."""
import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "_dutch_leftover_check.py"


@pytest.fixture(scope="module")
def ck():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("dutch_leftover_check_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_markers_flag_dutch_in_english_feedback(ck):
    for s in ("Nina zegt: Comment était le zoo ?", "Wij willen graag twee boules.", "Ik lees graag en ik luister naar muziek.",
              "Het Fahrkarte means the ticket.", "Anna doet dit nooit"):
        assert ck.nl_markers(s, "en+fr+en"), s


def test_markers_ignore_ambiguous_function_words(ck):
    # die / is / in / was / van / de / hier / wie exist in English, German or the Romance targets
    for s in ("The die is cast.", "She was in the van.", "Die Frau ist hier.", "Wie geht es dir?", "Je suis de Paris.",
              "Tienes klein? No."):
        assert not ck.nl_markers(s, "en+de+en"), s
    assert not ck.nl_markers("Das ist klein.", "en+de+en")            # klein is German
    assert not ck.nl_markers("Le train arrive à onze heures.", "en+fr+en")   # onze is French


def test_single_weak_word_in_long_sentence_is_not_flagged(ck):
    assert not ck.nl_markers("The sign said it was a very long and quiet morgen in the old harbour town today again.", "en+es+en")


def test_dutch_slugs_only_for_dutch_words(ck):
    assert ck.dutch_slugs("choose_ontbijten") == ["choose_ontbijten"]
    assert ck.dutch_slugs("choose_hello_world") == []
    assert ck.dutch_slugs("jonas_ist_klein", "en+de+en") == []


def test_key_slugs_are_listed_not_visible(ck):
    node = {"exercises": {"es.a1.unit49.lesson01.exercise01.choose_ontbijten": {"content_key": "x.choose_ontbijten", "feedback": "Fine."}}}
    found = ck.key_slugs(node)
    assert "choose_ontbijten" in found


def _scan(ck, tmp_path, monkeypatch, overlay, source_overlay=None, nl_vocab=("tulpen", "hallo", "zegt")):
    (tmp_path / "overlays/en-es").mkdir(parents=True, exist_ok=True)
    (tmp_path / "overlays/en-nl").mkdir(parents=True, exist_ok=True)
    (tmp_path / "practice/en-nl").mkdir(parents=True, exist_ok=True)
    (tmp_path / "realizations/nl").mkdir(parents=True, exist_ok=True)
    (tmp_path / "overlays/en-es/a1_unit50.yaml").write_text(yaml.safe_dump(overlay, allow_unicode=True))
    (tmp_path / "overlays/en-nl/a1_unit11.yaml").write_text(yaml.safe_dump(source_overlay or {"exercises": {}}, allow_unicode=True))
    monkeypatch.setattr(ck, "CONTENT", tmp_path)
    monkeypatch.setattr(ck, "dutch_vocab", lambda: frozenset(nl_vocab))
    monkeypatch.setattr(ck, "english_words", lambda: frozenset({"says", "means", "hello", "ticket", "the", "is", "and"}))
    monkeypatch.setattr(ck, "target_vocab", lambda t: frozenset({"hola"}))
    ck._strings.cache_clear()
    ck._load.cache_clear()
    hits, _ = ck.scan_file("overlays", "en-es", tmp_path / "overlays/en-es/a1_unit50.yaml", "en", "es")
    return hits


def _overlay(feedback):
    return {
        "overlay_key": "en-es.a1.unit50",
        "review": {"notes": "Derived by scripts/derive_target.py from nl/a1_unit11_plans.yaml (en-nl overlay)"},
        "exercises": {"es.a1.unit50.lesson01.exercise01.choose_ontbijten": {"feedback": feedback}},
    }


def test_scan_flags_dutch_only_word_and_identity_but_not_slug_key(ck, tmp_path, monkeypatch):
    hits = _scan(ck, tmp_path, monkeypatch, _overlay("Tulpen means the ticket."))
    assert len(hits) == 1 and "dutch-only words tulpen" in hits[0]
    assert not _scan(ck, tmp_path, monkeypatch, _overlay("Hola means hello."))      # Spanish and English only; the slug key is ignored


def test_scan_identity_with_source(ck, tmp_path, monkeypatch):
    src = {"exercises": {"a": {"feedback": "Hallo zegt de man."}}}
    hits = _scan(ck, tmp_path, monkeypatch, _overlay("Hallo zegt de man."), src)
    assert hits and ("identical" in hits[0] or "dutch" in hits[0])


def test_repo_has_no_dutch_leftovers_in_a_clean_pair(ck):
    # real corpus smoke test: ar-en has never carried Dutch
    hits, _ = ck.scan_pair("ar-en")
    assert hits == []
