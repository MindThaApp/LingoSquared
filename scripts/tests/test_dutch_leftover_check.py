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


def _scan_side(ck, tmp_path, monkeypatch, pairs, note="Derived by scripts/derive_target.py from nl/a1_unit11_plans.yaml"):
    d = tmp_path / "overlays/en-es"
    d.mkdir(parents=True, exist_ok=True)
    y = {"review": {"notes": note},
         "exercises": {"x.match": {"accepted_answers": [{"value": [{"left": a, "right": b} for a, b in pairs]}]}}}
    (d / "a1_unit50.yaml").write_text(yaml.safe_dump(y, allow_unicode=True))
    monkeypatch.setattr(ck, "CONTENT", tmp_path)
    monkeypatch.setattr(ck, "english_loose", lambda: frozenset({"museum", "the", "stage", "to", "visit", "ticket"}))
    monkeypatch.setattr(ck, "target_vocab_native", lambda t: frozenset({"museo", "visitar", "el", "escenario", "lucía", "nadar"}))
    ck._load.cache_clear()
    return ck.english_side_hits("en-es", d / "a1_unit50.yaml")


def test_english_side_lint_flags_translated_english_side(ck, tmp_path, monkeypatch):
    hits = _scan_side(ck, tmp_path, monkeypatch, [("museo", "museo"), ("visitar", "to visit"), ("el escenario", "visitar")])
    assert len(hits) == 2 and all("no English side" in h for h in hits)


def test_english_side_lint_accepts_good_pairs_and_person_sentence_pairs(ck, tmp_path, monkeypatch):
    assert not _scan_side(ck, tmp_path, monkeypatch, [("museo", "museum"), ("el escenario", "the stage"), ("Lucía", "nadar el museo visitar")])


def test_english_side_lint_skips_hand_authored_units(ck, tmp_path, monkeypatch):
    assert not _scan_side(ck, tmp_path, monkeypatch, [("museo", "museo")], note="Reviewed by a native speaker")


def test_taalcafe_compound_flagged_in_long_string(ck):
    s = "Emergencies: asking for help at the taalcafé in the library when there is a fire today"
    assert ck.nl_markers(s, "en") == ["taalcafé"]
    assert ck.nl_markers("Welcome to the language café, everyone in the library today", "en") == []


# --- s17: leftovers that went undetected because review/provenance notes made Dutch words look English ---

def test_visible_strings_skip_review_and_provenance(ck):
    y = {"review": {"notes": "no longer contains kaartje, zegt de medewerker"}, "generation_provenance": "haar",
         "exercises": {"x": {"feedback": "Hello there", "content_key": "k.afspraak"}}}
    vals = [v for _p, v in ck.visible_strings(y)]
    assert vals == ["Hello there"]


def test_dutch_word_quoted_in_review_notes_does_not_whitelist_it(ck, tmp_path, monkeypatch):
    """Regression: 'Haar means hair', 'Kaartje means ticket', 'Nina zegt: <long French sentence>' passed the check because the
    English realizations' review notes quote those words, which put them into the English vocabulary."""
    d = tmp_path / "realizations/en"
    d.mkdir(parents=True)
    (d / "u.yaml").write_text(yaml.safe_dump({"review": {"notes": "answer word kaartje, Welke zin zegt de man, haar"},
                                              "x": {"text": "Hello, I would like a ticket please"}}))
    monkeypatch.setattr(ck, "CONTENT", tmp_path)
    monkeypatch.setattr(ck.dd, "CONTENT", tmp_path)
    ck._load.cache_clear()
    core = ck._english_core()
    assert "ticket" in core and not ({"kaartje", "zegt", "haar"} & core)


def test_scan_flags_single_dutch_word_in_long_english_feedback(ck, tmp_path, monkeypatch):
    monkeypatch.setattr(ck, "dutch_vocab", lambda: frozenset({"zegt", "haar", "kaartje", "tulpen"}))
    for fb in ("Nina zegt: On va au parc d'attractions ensemble la semaine prochaine ?",
               "Haar means hair; blond/brun/gris/noir are hair colors.",
               "Kaartje means ticket, gare means gare, transport means transport, centre-ville means town centre."):
        hits = _scan_en_fr(ck, tmp_path, monkeypatch, fb)
        assert len(hits) == 1, fb


def test_scan_does_not_flag_good_english_feedback_with_target_words(ck, tmp_path, monkeypatch):
    for fb in ("Cheveux means hair; blond/brun/gris/noir are hair colors.", "Nina says: On va au parc d'attractions ensemble ?",
               "Billet means ticket, gare means station, transport means transport."):
        assert _scan_en_fr(ck, tmp_path, monkeypatch, fb) == [], fb


def _scan_en_fr(ck, tmp_path, monkeypatch, feedback):
    d = tmp_path / "overlays/en-fr"
    d.mkdir(parents=True, exist_ok=True)
    y = {"overlay_key": "en-fr.a1.unit50", "exercises": {"fr.a1.unit50.lesson01.exercise01.match_x": {"feedback": feedback}}}
    (d / "a1_unit50.yaml").write_text(yaml.safe_dump(y, allow_unicode=True))
    monkeypatch.setattr(ck, "CONTENT", tmp_path)
    monkeypatch.setattr(ck, "english_words", lambda: frozenset({"means", "hair", "colors", "are", "ticket", "gare", "transport",
                                                                "centre", "ville", "town", "says", "station", "ensemble", "the"}))
    monkeypatch.setattr(ck, "target_vocab", lambda t: frozenset({"cheveux", "billet", "parc", "attractions", "semaine", "prochaine"}))
    ck._strings.cache_clear()
    ck._load.cache_clear()
    hits, _ = ck.scan_file("overlays", "en-fr", d / "a1_unit50.yaml", "en", "fr")
    return hits
