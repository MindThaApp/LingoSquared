"""Tests for scripts/_hindi_name_check.py (one Devanagari spelling per person name)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _hindi_name_check as hn  # noqa: E402


def test_skeleton_ignores_length_nukta_and_chandrabindu():
    assert hn.skeleton("नीना") == hn.skeleton("निना")
    assert hn.skeleton("फ़ेना") == hn.skeleton("फेना")
    assert hn.skeleton("लोटे") == hn.skeleton("लॉटे")


def test_table_is_consistent():
    std, rej = hn.load()
    assert "नीना" in std and rej["निना"] == "नीना"
    assert not set(std) & set(rej)            # a spelling is never both standard and rejected
    assert all(g in std for g in rej.values())


def test_content_has_one_spelling_per_name(capsys):
    assert hn.main() == 0, capsys.readouterr().out


NAMES = {"Mihai", "Anna", "Noor", "Omar", "Priya", "Arjun"}


def spans(line, **kw):
    return [w for _a, _b, w in hn.latin_names(line, NAMES, **kw)]


def test_latin_name_inside_hindi_is_flagged():
    assert spans("Mihai कहता है") == ["Mihai"]
    assert spans("मेरा नाम Noor है।") == ["Noor"]
    assert spans("Omar, Noor से पूछता है") == ["Omar", "Noor"]
    assert spans("Lotte: हाय, मैं Noor हूँ।") == ["Noor"]


def test_target_language_text_is_left_alone():
    assert spans("Ik heet Noor सीधे बोलने वाले का नाम बताता है।") == []
    assert spans("*Ich heiße Anna* से आप अपना नाम बताते हैं।") == []
    assert spans("Hallo, Mihai! मेरा नाम") == []
    assert spans("Anna sagt: मेरा साइज़ एम है।") == []


def test_sentence_end_separates_target_sentence_from_hindi_name():
    assert spans("Wann haben Sie Geburtstag? Anna के रूप में जवाब दीजिए।") == ["Anna"]


def test_hindi_as_target_only_checks_mostly_devanagari_lines():
    assert spans("lesson exercise 10 uses अर्जुन, तुम क्या काम (करते, Arjun", target=True) == []
    assert spans("Priya: मेरे विचार से स्वतंत्रता सबसे ज़रूरी है।", target=True) == ["Priya"]
    assert spans("अर्जुन: Arjun", target=True) == []  # Hindi word glossed by its Latin form


def test_mapping_key_lines_and_marker_are_skipped():
    assert hn.latin_names("Omar: 31 साल की", NAMES, key_line_skip=True) == []
    assert hn.latin_names("Omar कहता है  # hindi-latin-name-ok", NAMES) == []


def test_fix_converts_and_is_idempotent():
    import _hindi_latin_names_fix as fx
    std = fx.standard_by_latin()
    names = hn.latin_name_set()
    out = fx.fix_text("Mihai कहता है: Ewa, Marek से पूछती है।", names, std, [], "overlays/hi-nl/x.yaml", target=False, key_skip=False)
    assert out == f"{std['Mihai']} कहता है: {std['Ewa']}, {std['Marek']} से पूछती है।"
    assert fx.fix_text(out, names, std, [], "overlays/hi-nl/x.yaml", target=False, key_skip=False) == out
