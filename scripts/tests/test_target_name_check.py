"""Tests for scripts/_target_name_check.py (wrong-language names in cross pairs)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _target_name_check as tn  # noqa: E402


def langs(learner, target, text, sib=""):
    return {lang for _, lang, _ in tn.check_text(learner, target, text, sib)}


def test_flags_english_name_of_other_language():
    assert langs("de", "fr", "Sagen Sie es auf Spanisch.") == {"es"}
    assert langs("hi", "nl", "इसे Spanish में कहें।") == {"es"}


def test_flags_name_in_learner_script():
    assert langs("hi", "fr", "इसे स्पेनिश में कहें।") == {"es"}
    assert langs("ar", "de", "قلها بالإسبانية.") == {"es"}
    assert langs("prs", "it", "این را به آلمانی بگو.") == {"de"}
    assert langs("ru", "pl", "Скажите это по-немецки; немецкий язык.") == {"de"}


def test_target_and_learner_language_are_fine():
    assert not langs("de", "es", "Sagen Sie es auf Spanisch.")
    assert not langs("hi", "es", "इसे Spanish में कहें।")
    assert not langs("de", "es", "Wie im Deutschen ist das so.")        # learner language itself
    assert not langs("hi", "fr", "हिंदी में Hindi लिखें।")


def test_country_names_are_not_language_names():
    assert not langs("ar", "de", "أنا من روسيا. إيطاليا. إسبانيا")
    assert not langs("hi", "de", "मैं जर्मनी से आता हूँ। स्पेन")
    assert not langs("prs", "de", "من از روسیه استم.")


def test_sibling_unit_about_language_licenses_name():
    sib = "Jonas studies Spanish.\nHe speaks Spanish.\nA Spanish course."
    assert not langs("de", "fr", "Jonas studiert Spanisch.", sib)
    assert langs("de", "fr", "Jonas studiert Spanisch.", "one Spanish mention")      # a single mention does not count


def test_english_and_verbatim_sibling_lines_are_ignored():
    assert not langs("de", "it", "Sprichst du Englisch?", "Do you speak English?")
    assert not langs("de", "ro", "  register: like Spanish tú", "register: like Spanish tú")
    assert not langs("fr", "it", "it.a1.unit73.teach.montagne_russe:")


def test_tm_entry_guard():
    assert not tn.tm_entry_ok("de", "Put the words in order to say 'We buy a pass.'", "Bringen Sie ... auf Spanisch zu sagen.")
    assert tn.tm_entry_ok("de", "Put the words in order.", "Bringen Sie die Wörter in die richtige Reihenfolge.")
    assert tn.tm_entry_ok("de", "Say it in Spanish.", "Sagen Sie es auf Spanisch.")


def test_scan_respects_allowlist(tmp_path):
    for kind in ("overlays", "practice"):
        for d in ("de-fr", "en-fr"):
            (tmp_path / kind / d).mkdir(parents=True)
    (tmp_path / "overlays/de-fr/u.yaml").write_text("a:\n  instruction: Sagen Sie es auf Spanisch.\n", encoding="utf-8")
    (tmp_path / "overlays/en-fr/u.yaml").write_text("a:\n  instruction: Say it.\n", encoding="utf-8")
    assert len(tn.scan(["de-fr"], allow=[], content=tmp_path)) == 1
    assert not tn.scan(["de-fr"], allow=[("overlays/de-fr/u.yaml", "es", "*")], content=tmp_path)
    assert not tn.scan(["de-fr"], allow=[("overlays/de-fr/u.yaml", "es", "auf Spanisch")], content=tmp_path)
    assert len(tn.scan(["de-fr"], allow=[("overlays/de-fr/u.yaml", "fr", "*")], content=tmp_path)) == 1


def test_repo_is_clean():
    assert tn.scan(tn.cross_pairs()) == []


def test_dari_farsi_arabic_hindi_spellings_of_spanish():
    assert langs("prs", "de", "کلمه‌ها را مرتب کنید به اسپانوی ساخته شود") == {"es"}
    assert langs("prs", "fr", "به اسپانیایی بگویید") == {"es"}
    assert langs("fa", "it", "به اسپانیایی بگویید") == {"es"}
    assert langs("ar", "fr", "قلها بالأسبانية") == {"es"}
    assert langs("hi", "fr", "इसे स्पैनिश में कहें") == {"es"}
