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


# ---------------------------------------------------------------------------
# --codex translation backend (the codex call is mocked)
# ---------------------------------------------------------------------------
import json  # noqa: E402
import types  # noqa: E402


def _work(tmp_path, items_by_file):
    w = tmp_path / "fr-es"
    w.mkdir()
    (w / "GUIDE.md").write_text("guide", encoding="utf-8")
    for name, items in items_by_file.items():
        (w / f"{name}.src.json").write_text(json.dumps({"items": items}), encoding="utf-8")
    return w


def _args(tmp_path, **kw):
    base = dict(work=str(tmp_path), new="fr-es", batch=2, workers=2, retries=3, codex_model=None)
    return types.SimpleNamespace(**{**base, **kw})


def _echo(prompt, model=None):
    """Fake codex: translate every item to 'ES:<text>' (keeps *spans* and placeholders)."""
    items = [json.loads(l) for l in prompt.split("Items:\n", 1)[1].splitlines() if l.startswith("[")]
    out = [{"id": it[0], "t": it[2].replace("Hello", "Hola")} for it in items if it[0] != "#"]
    return json.dumps({"items": out}), {"tokens": 10}


def test_codex_translates_all_files_in_namespaced_chunks_and_is_resumable(tmp_path):
    w = _work(tmp_path, {"a1_unit01": [["#", "exercise"], ["u1", "instruction", "Hello there"], ["u2", "feedback", "Hello again"]],
                         "shared": [["s1", "packtext", "Hello {item}"]]})
    calls = []

    def call(prompt, model=None):
        calls.append(prompt)
        return _echo(prompt)

    assert dc.cmd_translate_codex(_args(tmp_path), call=call, sleep=lambda s: None) == 0
    assert json.loads((w / "a1_unit01.tr.json").read_text())["u1"] == "Hola there"
    assert json.loads((w / "shared.tr.json").read_text())["s1"] == "Hola {item}"
    assert len(calls) == 2                      # 3 items, batch 2
    assert json.loads((w / "codex-stats.json").read_text())["calls"] == 2
    calls.clear()
    assert dc.cmd_translate_codex(_args(tmp_path), call=call, sleep=lambda s: None) == 0
    assert calls == []                          # nothing left to do on a re-run


def test_codex_retries_transient_limits_with_backoff(tmp_path):
    _work(tmp_path, {"shared": [["s1", "packtext", "Hello"]]})
    state, waits = {"n": 0}, []

    def call(prompt, model=None):
        state["n"] += 1
        if state["n"] < 3:
            raise RuntimeError("rate: 429 too many requests")
        return _echo(prompt)

    assert dc.cmd_translate_codex(_args(tmp_path), call=call, sleep=waits.append) == 0
    assert waits == [15, 30]
    st = json.loads((tmp_path / "fr-es" / "codex-stats.json").read_text())
    assert st["rate_limited"] == 2 and st["calls"] == 3


def test_codex_stops_on_hard_usage_limit_and_records_it(tmp_path):
    _work(tmp_path, {"shared": [["s1", "packtext", "Hello"], ["s2", "packtext", "Hello 2"]]})

    def call(prompt, model=None):
        raise dc.CodexQuotaExhausted("You've hit your usage limit")

    assert dc.cmd_translate_codex(_args(tmp_path, batch=1, workers=1), call=call, sleep=lambda s: None) == 2
    st = json.loads((tmp_path / "fr-es" / "codex-stats.json").read_text())
    assert "usage limit" in st["quota"] and st["calls"] == 1      # no further calls after the quota error


def test_codex_lint_failure_is_retried_with_the_problem_in_the_prompt(tmp_path):
    w = _work(tmp_path, {"shared": [["s1", "feedback", "*Poulet* is masculine."]]})
    prompts = []

    def call(prompt, model=None):
        prompts.append(prompt)
        t = "Poulet es masculino." if len(prompts) == 1 else "*Poulet* es masculino."
        return json.dumps({"items": [{"id": "shared/s1", "t": t}]}), {}

    assert dc.cmd_translate_codex(_args(tmp_path), call=call, sleep=lambda s: None) == 0
    assert "asterisk span" in prompts[1] and json.loads((w / "shared.tr.json").read_text())["s1"] == "*Poulet* es masculino."


def test_codex_call_builds_a_sandboxed_command_and_classifies_errors(monkeypatch):
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"], seen["cwd"] = cmd, kw["cwd"]
        ev = '{"type":"turn.failed","error":{"message":"You\'ve hit your usage limit. try again at Nov 17"}}\n'
        return types.SimpleNamespace(returncode=1, stdout=ev, stderr="")

    monkeypatch.setattr(dc.subprocess, "run", fake_run)
    try:
        dc.codex_call("x")
    except dc.CodexQuotaExhausted:
        pass
    else:
        raise AssertionError("usage limit must raise CodexQuotaExhausted")
    c = seen["cmd"]
    assert c[:2] == ["codex", "exec"] and c[c.index("-s") + 1] == "read-only" and "--ephemeral" in c and "--output-schema" in c
    assert seen["cwd"] != str(dc.ROOT)


# ---------------------------------------------------------------------------
# --claude backend (headless `claude -p`, subprocess mocked)
# ---------------------------------------------------------------------------
def test_claude_backend_translates_and_writes_usage_stats(tmp_path):
    w = _work(tmp_path, {"a1_unit01": [["i1", "instruction", "Hello"], ["i2", "feedback", "Hello again"], ["i3", "note", "Hello!"]]})

    def call(prompt, model=None):
        text, _ = _echo(prompt)
        return text, {"tokens": 100, "usage": {"input_tokens": 5, "cache_read_input_tokens": 60, "cache_creation_input_tokens": 20,
                                                "output_tokens": 15}, "cost_usd": 0.01}

    assert dc.cmd_translate_claude(_args(tmp_path, claude_model="sonnet"), call=call, sleep=lambda s: None) == 0
    assert dc.dd.load_tr(w, "a1_unit01")["i1"] == "Hola"
    st = json.loads((w / "claude-stats.json").read_text())
    assert not (w / "codex-stats.json").exists()
    assert st["calls"] == 2 and st["tokens"] == 200 and st["usage"]["cache_read_input_tokens"] == 120 and st["cost_usd"] == 0.02


def test_claude_call_builds_a_toolless_command_and_parses_usage(monkeypatch):
    seen = {}
    ev = {"is_error": False, "structured_output": {"items": [{"id": "a", "t": "hola"}]}, "total_cost_usd": 0.5,
          "usage": {"input_tokens": 2, "cache_creation_input_tokens": 3, "cache_read_input_tokens": 4, "output_tokens": 5}}

    def fake_run(cmd, **kw):
        seen["cmd"], seen["cwd"] = cmd, kw["cwd"]
        return types.SimpleNamespace(returncode=0, stdout=json.dumps(ev), stderr="")

    monkeypatch.setattr(dc.subprocess, "run", fake_run)
    text, info = dc.claude_call("x")
    c = seen["cmd"]
    assert c[:2] == ["claude", "-p"] and c[c.index("--tools") + 1] == "" and c[c.index("--model") + 1] == "sonnet"
    assert "--json-schema" in c and "--no-session-persistence" in c and seen["cwd"] != str(dc.ROOT)
    assert json.loads(text)["items"][0]["t"] == "hola"
    assert info["tokens"] == 14 and info["usage"]["cache_read_input_tokens"] == 4 and info["cost_usd"] == 0.5


def test_claude_call_classifies_errors(monkeypatch):
    def run_with(msg):
        monkeypatch.setattr(dc.subprocess, "run", lambda cmd, **kw: types.SimpleNamespace(
            returncode=1, stdout=json.dumps({"is_error": True, "result": msg}), stderr=""))
        dc.claude_call("x")

    for msg, exc in (("You've hit your usage limit", dc.CodexQuotaExhausted), ("429 rate limit, overloaded", RuntimeError)):
        try:
            run_with(msg)
        except exc as e:
            assert (exc is dc.CodexQuotaExhausted) or str(e).startswith("rate")
        else:
            raise AssertionError(msg)


def test_compiler_localizes_teaching_card_body():
    import compile_content as cc
    card = {"text": "Dates use cardinal numbers.", "language_code": "en", "direction": "ltr"}
    out = cc.localize_teaching_target(card, "Les dates utilisent des nombres cardinaux.", "fr", "es")
    assert out == {"text": "Les dates utilisent des nombres cardinaux.", "language_code": "fr", "direction": "ltr"}
    assert card["language_code"] == "en"  # input untouched
    assert cc.localize_teaching_target(card, None, "fr", "es") == card
    spanish = {"text": "Hola", "language_code": "es", "direction": "ltr"}
    assert cc.localize_teaching_target(spanish, "Salut", "fr", "es") == spanish  # target-language card: field ignored
    item = {"content_key": "k", "kind": "grammar_note", "target": card}
    compiled = cc.compile_teaching_item(item, {"target_text": "Texte"}, "fr", "es")
    assert compiled["text_blocks"][0]["text"] == "Texte" and compiled["text_blocks"][0]["language_code"] == "fr"


def test_teaching_target_validator_flags_unlocalized_cards():
    import compile_content as cc
    real = {"target_language": "es", "units": [{"lessons": [{"teaching": [
        {"content_key": "es.n", "kind": "grammar_note", "target": {"text": "Note", "language_code": "en"}},
        {"content_key": "es.v", "kind": "vocabulary", "target": {"text": "Hola", "language_code": "es"}}]}]}]}
    for source, teaching, errors in (
        ("fr", {}, 1),
        ("fr", {"es.n": {"target_text": "Note fr"}}, 0),
        ("fr", {"es.n": {"target_text": " "}}, 1),
        ("fr", {"es.n": {"target_text": "ok"}, "es.v": {"target_text": "mal"}}, 1),
        ("en", {}, 0),
    ):
        report = cc.Report()
        cc.validate_teaching_target_localization(real, {"source_language": source, "teaching": teaching}, report)
        assert len(report.errors) == errors, (source, teaching)


def test_cross_extract_finds_english_cards_and_cloze_hints(tmp_path):
    real = tmp_path / "r.yaml"
    real.write_text(
        "target_language: es\nunits:\n- lessons:\n  - teaching:\n"
        "    - {content_key: es.n, kind: grammar_note, target: {text: 'Dates use *de*.', language_code: en}}\n"
        "    - {content_key: es.v, kind: vocabulary, target: {text: Hola, language_code: es}}\n"
        "    exercises:\n"
        "    - content_key: es.c\n      prompt: {target_blocks: [{text: 'Instruction', language_code: es}, "
        "{text: 'Las tres y media es ___ del taller. (before, since it starts at four)', language_code: es}]}\n"
        "    - content_key: es.d\n      prompt: {target_blocks: [{text: 'Voy a ___ casa. (to the)', language_code: es}, "
        "{text: 'Me llamo ___.', language_code: es}]}\n", encoding="utf-8")
    cards = dc.foreign_teaching_targets(real, "es")
    assert cards == {"es.n": ("grammar_note", "Dates use *de*.")}
    hints = dc.foreign_prompt_blocks(real, "es")
    assert [h[0] for h in hints["es.c"]] == [1] and [h[0] for h in hints["es.d"]] == [0]
    assert dc.english_hint("El taller ___. (ends)") and dc.english_hint("Quiero ___. (I want)")
    assert not dc.english_hint("Me llamo ___.") and not dc.english_hint("¿Dónde está (el baño)?  ")


def test_unchanged_english_gate_ignores_accent_variants_and_allowlist(tmp_path):
    import json as _json
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    for p in (a, b):
        p.write_text(_json.dumps({"x": ["Soy de Mexico.", "football / yoga", "Which shop is the cheapest one?"]}), encoding="utf-8")
    out = dc.unchanged_english(a, b, "es", "fr")
    assert not any("Mexico" in o or "yoga" in o for o in out)
    assert any("cheapest" in o for o in out)


def test_normalize_spans_strips_only_spans_the_source_does_not_have():
    # extra spans around a quote are stripped, then lint passes
    fixed = dc.normalize_spans("Say it like this: Hoe gaat het?", "Zeg het zo: *Hoe gaat het?*")
    assert fixed == "Zeg het zo: Hoe gaat het?"
    # source spans survive, extras go
    fixed = dc.normalize_spans("*Poulet* is masculine.", "*Poulet* is mannelijk, *het eten*.")
    assert fixed == "*Poulet* is mannelijk, het eten."
    assert dc.lint("feedback", "*Poulet* is masculine.", fixed) == []


def test_normalize_spans_never_masks_a_real_mismatch():
    # a missing span is not repaired
    src, tr = "*Poulet* is masculine.", "Poulet es masculino."
    assert dc.normalize_spans(src, tr) == tr
    assert dc.lint("feedback", src, tr)
    # a replaced span (wrong word) still fails the verbatim check
    tr2 = dc.normalize_spans(src, "*Pollo* es masculino.")
    assert dc.lint("feedback", src, tr2)


def test_english_prose_does_not_flag_dutch_learner_text_but_still_flags_english():
    old = (dc._PROSE_TARGET, dc._PROSE_LEARNER)
    try:
        dc._PROSE_TARGET, dc._PROSE_LEARNER = "de", "nl"
        assert not dc.english_prose("*Hallo* is een informele begroeting die je op elk moment kunt gebruiken.")
        assert not dc.english_prose("Dit is een formele groet en het was er al.")
        assert dc.english_prose("This is an informal greeting you can use at any time.")
        assert dc.english_prose("It is not the formal word for you.")
        dc._PROSE_LEARNER = "es"
        assert dc.english_prose("Hello is an informal greeting.")
    finally:
        dc._PROSE_TARGET, dc._PROSE_LEARNER = old


def test_english_prose_does_not_flag_polish_function_words_but_still_flags_english():
    old = (dc._PROSE_TARGET, dc._PROSE_LEARNER)
    try:
        dc._PROSE_TARGET, dc._PROSE_LEARNER = "de", "pl"
        assert not dc.english_prose("*Was möchten Sie?* to standardowy, formalny sposób, w jaki obsługa pyta.")
        assert not dc.english_prose("*Restiamo* to forma „my” użyta jako propozycja.")
        assert dc.english_prose("This is the formal way to ask what you want.")
    finally:
        dc._PROSE_TARGET, dc._PROSE_LEARNER = old


def test_latin_in_cyrillic_flags_latin_in_ru_blocks_only(tmp_path):
    import json
    course = {"blocks": [
        {"language_code": "ru", "text": "Добрый ___! (guten Tag)"},         # trailing hint is learner text
        {"language_code": "ru", "text": "Я хочу tea."},                      # Latin leftover in target text
        {"language_code": "en", "text": "Say привет to Anna."},             # learner-language block
    ]}
    p = tmp_path / "c.json"
    p.write_text(json.dumps(course), encoding="utf-8")
    hits = dc.latin_in_cyrillic(p, "ru")
    assert len(hits) == 1 and "tea" in hits[0]
    assert dc.latin_in_cyrillic(p, "es") == []


def test_cross_guide_has_no_english_script_note_and_a_dari_rule():
    g = dc.cross_guide("en-es", "hi", "es")
    assert "English words in Latin script" not in g
    assert "words quoted in the text stay in Latin script" in g
    assert "Grammar terms" in g and "Grammar terms" not in dc.cross_guide("en-es", "de", "es")
    assert "Dari (prs) is NOT Iranian Farsi" not in g
    prs = dc.cross_guide("en-de", "prs", "de")
    assert "Dari (prs) is NOT Iranian Farsi" in prs and "check_dari_register.py" in prs
    assert "RTL language" in prs and "RTL language" not in g
    assert "not Dari" in dc.cross_guide("en-es", "fa", "es")
    assert "words quoted in the text" not in dc.cross_guide("en-es", "de", "es")      # Latin learner: no script rule


def test_dari_register_checker_covers_cross_pair_lanes():
    import check_dari_register as cdr
    rels = [r for r, _ in cdr.PRS_LANES]
    assert "overlays/prs-en" in rels
    assert all(r.startswith(("overlays/prs-", "practice/prs-")) or r in rels for r in rels)
    assert [r for r, _ in cdr._cross_prs_lanes() if r.endswith("prs-en")] == []


def test_english_in_nonlatin_flags_short_english_leftovers_but_keeps_target_words():
    f = dc.english_in_nonlatin
    assert f("شكرا you", "es") == ["you"]                      # two tokens: english_prose would miss it
    assert f("समुद्र तट: the beach", "es")
    assert f("اكتب *hola* بالإسبانية", "es") == []             # quoted Spanish word stays Latin
    assert f("اختر الترجمة الصحيحة لـ {item}", "es") == []     # placeholder
    assert f("Good morning", "es") == []                       # pure Latin: other checks decide
    assert f("दिन का नाम *lunes* है", "es") == []


def test_learner_leftovers_catches_english_in_arabic_overlay(tmp_path, monkeypatch):
    import derive_direction as dd
    ov = tmp_path / "overlays"
    (ov / "ar-es").mkdir(parents=True)
    (ov / "en-es").mkdir(parents=True)
    sib = {"exercises": {"k1": {"instruction": "Translate tomorrow."}}}
    mine = {"exercises": {"k1": {"instruction": "ترجم الجملة. tomorrow"}}}
    (ov / "en-es" / "u.yaml").write_text(dd.yaml.safe_dump(sib, allow_unicode=True), encoding="utf-8")
    (ov / "ar-es" / "u.yaml").write_text(dd.yaml.safe_dump(mine, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(dc, "CONTENT", tmp_path)
    assert any("English in ar text" in h for h in dc.learner_leftovers("ar-es"))
    mine["exercises"]["k1"]["instruction"] = "ترجم الجملة."
    (ov / "ar-es" / "u.yaml").write_text(dd.yaml.safe_dump(mine, allow_unicode=True), encoding="utf-8")
    assert dc.learner_leftovers("ar-es") == []


def test_english_in_nonlatin_grammar_terms_names_and_endings():
    f = dc.english_in_nonlatin
    assert f("هذا هو present perfect من الفعل", "es") == ["present", "perfect"]
    assert f("स्पेनिश में बिना article के", "es") == ["article"]
    assert f("فعل منتظم ينتهي بـ -er", "es") == []                      # verb ending
    assert f("*Comer* فعل منتظم ينتهي بـ -er", "es") == []             # ...also after a span
    assert f("सुबह 9 बजे यानी 9 PM", "es") == []
    # source-aware: a Spanish word the translator left without asterisks is not a leftover, an English one is
    assert f("يقول ماتيو: Me has ayudado mucho.", "es", src="Mateo says: Me has ayudado mucho.") == []
    assert f("ترجم tomorrow", "es", src="Translate tomorrow.") == ["tomorrow"]
    assert f("ترجم tomorrow", "es", src="Translate the sentence.") == []   # not in the source: a translator-added word is not judged
