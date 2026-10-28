"""derive_cross: learner/target text classification, lint, pair + prompt-block localization."""
import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("derive_cross_under_test", SCRIPTS / "derive_cross.py")
dc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc)

KEY = frozenset(dc.norm_tokens("Je voudrais un billet pour Lyon aller simple"))


def test_target_text_is_kept_and_english_prose_is_translated():
    assert dc.is_target_text("Je voudrais un billet pour Lyon", KEY)
    assert dc.is_target_text("un billet", KEY)
    assert not dc.is_target_text("I would like a ticket to Lyon.", KEY)
    assert not dc.is_target_text("a one-way ticket", KEY)


def test_lint_requires_placeholders_spans_and_target_words():
    assert dc.lint("feedback", "*Poulet* is masculine.", "*Poulet* es masculino.") == []
    assert dc.lint("feedback", "*Poulet* is masculine.", "Poulet es masculino.")
    assert dc.lint("feedback", "*Poulet* is masculine.", "*Pollo* es masculino.")
    assert dc.lint("packtext", "What does {item} mean?", "¿Qué significa?")


def test_compiler_localizes_learner_language_prompt_blocks():
    import compile_content as cc
    blocks = [{"text": "Write in French: hello", "language_code": "en", "direction": "ltr"},
              {"text": "Bonjour", "language_code": "fr", "direction": "ltr"}]
    out = cc.localize_prompt_blocks(blocks, ["Escribe en francés: hola"], "es", "fr")
    assert out[0] == {"text": "Escribe en francés: hola", "language_code": "es", "direction": "ltr"}
    assert out[1] == blocks[1]
    assert blocks[0]["text"] == "Write in French: hello"  # input untouched
    assert cc.localize_prompt_blocks(blocks, None, "es", "fr") == blocks


def test_prompt_block_validator_flags_unlocalized_blocks():
    import compile_content as cc
    real = {"target_language": "fr", "units": [{"lessons": [{"exercises": [
        {"content_key": "fr.x", "prompt": {"target_blocks": [{"text": "Hello", "language_code": "en"}]}}]}]}]}
    for source, overlay_ex, errors in (
        ("es", {}, 1),
        ("es", {"prompt_blocks": ["Hola"]}, 0),
        ("es", {"prompt_blocks": ["Hola", "otro"]}, 1),
        ("en", {}, 0),
    ):
        report = cc.Report()
        cc.validate_prompt_block_localization(real, {"source_language": source, "exercises": {"fr.x": overlay_ex}}, report)
        assert len(report.errors) == errors, (source, overlay_ex)


def test_translation_memory_keys_skip_contrast_and_target_spans():
    assert dc.tm_key("instruction", "Listen and select.") == "instruction|Listen and select."
    assert dc.tm_key("note CONTRAST", "English keeps it.") is None
    assert dc.tm_key("feedback", "*Poulet* is masculine.") is None
    assert dc.tm_key("course_title", "French A1") is None


def test_group_names_follow_the_sibling_naming(tmp_path, monkeypatch):
    monkeypatch.setattr(dc.dd, "MANIFEST", tmp_path)
    (tmp_path / "en-it-a1.txt").write_text("x", encoding="utf-8")
    assert dc.group_names("es-it", ["a1", "a2"]) == ["es-it-a1", "es-it-a2"]
    assert dc.group_names("es-fr", ["a1", "a2"]) == ["es-fr", "es-fr-a2"]


def test_english_prose_ignores_cognates_and_italian_are():
    assert dc.english_prose("Riordinare es un verbo regular en -are")  is False
    assert dc.english_prose("His or her work") is True
    assert dc.english_prose("Je suis content") is False


def test_pair_clue_side_rule():
    # the learner side accepts weak English evidence, the other side only unmistakable English prose
    assert dc.pair_text_is_learner("the beach", True, "fr")
    assert not dc.pair_text_is_learner("la plage", True, "fr")
    assert not dc.pair_text_is_learner("zero", False, "fr")
    assert dc.pair_text_is_learner("The tea is cheaper.", False, "de")
