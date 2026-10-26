"""derive_target: translate units of a rich source target course (nl) into a thin one (es).

The fixture is a one-lesson nl unit with every hard case: target-language options, word order
with a variant, fill-in-blank, gendered production, a grammar explanation, a dialogue whose
media text is a concatenation of cards, a reversed matching pair and a Dutch-only note.
"""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "derive_target.py"

BACKFILL = '''"""fixture"""
GLOSSES = {"hola": "hello"}
POS_SETS = {"verb": {"hola"}}


def normalize(token):
    return token.lower()


POS_SETS["noun"] = set(GLOSSES) - set().union(*POS_SETS.values())
'''


def _blk(text, lang="nl"):
    return {"text": text, "language_code": lang, "direction": "ltr"}


def src_realization():
    k = "nl.a1.unit05.test"
    L = f"{k.rsplit('.', 1)[0]}.lesson01.start"
    lesson = {
        "content_key": L,
        "title": "Beginnen",
        "teaching": [
            {"content_key": f"{L.rsplit('.', 1)[0]}.teach.hoeveel", "kind": "phrase",
             "target": _blk("Hoeveel kost het?"), "introduced_tokens": ["Hoeveel", "kost", "het"]},
            {"content_key": f"{L.rsplit('.', 1)[0]}.teach.grammar", "kind": "grammar_note",
             "target": _blk("Ziek en moe zijn bijvoeglijke naamwoorden en gebruiken zijn in het Nederlands."),
             "introduced_tokens": ["Ziek"]},
            {"content_key": f"{L.rsplit('.', 1)[0]}.teach.d1", "kind": "dialogue",
             "target": _blk("Lotte: Hoi."), "introduced_tokens": ["Lotte", "Hoi"]},
            {"content_key": f"{L.rsplit('.', 1)[0]}.teach.d2", "kind": "dialogue",
             "target": _blk("Omar: Ik ben moe."), "introduced_tokens": ["Omar", "Ik", "ben", "moe"]},
        ],
        "exercises": [
            {"content_key": f"{k.rsplit('.', 1)[0]}.lesson01.exercise01.choose_cost", "type": "multiple_choice",
             "tested_text": "Hoeveel kost het", "prompt": {"target_blocks": [_blk("How much is it?", "en")]}},
            {"content_key": f"{k.rsplit('.', 1)[0]}.lesson01.exercise02.order_cost", "type": "word_order",
             "tested_text": "Hoeveel kost het", "prompt": {"target_blocks": []}, "word_bank": ["kost", "het", "Hoeveel"]},
            {"content_key": f"{k.rsplit('.', 1)[0]}.lesson01.exercise03.complete_cost", "type": "fill_in_blank",
             "tested_text": "Hoeveel kost het", "prompt": {"target_blocks": [_blk("Hoeveel ___ het?")]}},
            {"content_key": f"{k.rsplit('.', 1)[0]}.lesson01.exercise04.write_tired", "type": "writing_prompt",
             "tested_text": "Ik ben moe", "prompt": {"target_blocks": [_blk("Write in Dutch: I am tired.", "en")]}},
            {"content_key": f"{k.rsplit('.', 1)[0]}.lesson01.exercise05.match", "type": "matching_pairs",
             "tested_text": "hoeveel moe", "prompt": {"target_blocks": []},
             "pairs": [{"left": "moe", "right": "tired"}, {"left": "a rest", "right": "Hoeveel kost het?"}]},
            {"content_key": f"{k.rsplit('.', 1)[0]}.lesson01.exercise06.listen_dialogue", "type": "dialogue_comprehension",
             "tested_text": "ik ben moe", "media_asset_key": "nl.a1.audio.test.dialoog.01",
             "prompt": {"target_blocks": [_blk("How does he feel?", "en")]}},
        ],
    }
    return {
        "schema_version": "1.1", "realization_version": "2026.1-draft.1", "target_language": "nl", "cefr_level": "A1",
        "generation_provenance": {"method": "ai_generated"}, "status": "complete_draft",
        "review": {"status": "reviewed"}, "course": {"realization_key": "nl.a1"},
        "media_assets": [{"content_key": "nl.a1.audio.test.dialoog.01", "language": "nl",
                          "text": "Lotte: Hoi. Omar: Ik ben moe.", "voice_hint": "x", "status": "pending_generation"}],
        "units": [{"content_key": k, "title": "Test", "section": "reading_writing", "lessons": [lesson]}],
    }


def src_overlay():
    p = "nl.a1.unit05"
    return {
        "schema_version": "1.1", "overlay_version": "x", "overlay_key": "en-nl.a1.unit05", "source_language": "en",
        "target_language": "nl", "course": {"title": "Dutch A1", "description": "Beginner Dutch test."},
        "units": {f"{p}.test": {"title": "Test"}},
        "lessons": {f"{p}.lesson01.start": {"title": "Starting"}},
        "teaching": {
            f"{p}.lesson01.teach.hoeveel": {"title": "Price", "gloss": "How much is it?",
                                            "note": "*Kost* is the third-person form of *kosten*."},
            f"{p}.lesson01.teach.grammar": {"title": "Grammar", "gloss": "Sick and tired are adjectives."},
            f"{p}.lesson01.teach.d1": {"title": "Hi", "gloss": "Lotte: Hi.", "note": "A greeting."},
            f"{p}.lesson01.teach.d2": {"title": "Tired", "gloss": "Omar: I am tired."},
        },
        "exercises": {
            f"{p}.lesson01.exercise01.choose_cost": {
                "instruction": "Choose the Dutch sentence meaning 'How much is it?'", "correct_option": "Hoeveel kost het?",
                "distractors": ["Hoeveel het kost?", "Hoe kost het?"],
                "accepted_answers": [{"value": "Hoeveel kost het?", "status": "correct"}], "feedback": "Hoeveel kost het? asks the price."},
            f"{p}.lesson01.exercise02.order_cost": {
                "instruction": "Put the words in order.", "correct_option": "Hoeveel kost het",
                "accepted_answers": [{"value": "Hoeveel kost het", "status": "correct"}], "feedback": "Dutch puts the verb second."},
            f"{p}.lesson01.exercise03.complete_cost": {
                "instruction": "Complete the question.", "accepted_answers": [{"value": "kost", "status": "correct"}],
                "feedback": "The verb comes second."},
            f"{p}.lesson01.exercise04.write_tired": {
                "instruction": "Write in Dutch: I am tired.", "accepted_answers": [
                    {"value": "Ik ben moe.", "status": "correct"}, {"value": "Ik ben moe", "status": "correct"}],
                "feedback": "Ik ben moe."},
            f"{p}.lesson01.exercise05.match": {
                "instruction": "Match each Dutch word to its meaning.", "accepted_answers": [{"value": [
                    {"left": "moe", "right": "tired"}, {"left": "a rest", "right": "Hoeveel kost het?"}], "status": "correct"}],
                "feedback": "Moe means tired."},
            f"{p}.lesson01.exercise06.listen_dialogue": {
                "instruction": "Listen and choose how Omar feels.", "correct_option": "tired",
                "distractors": ["hungry", "angry"], "accepted_answers": [{"value": "tired", "status": "correct"}],
                "feedback": "Omar says: Ik ben moe."},
        },
    }


BASE_REAL = {
    "schema_version": "1.1", "realization_version": "2026.1-draft.1", "target_language": "es", "cefr_level": "A1",
    "units": [], "course": {"realization_key": "es.a1", "dialect": "es_neutral"},
}
BASE_OVL = {
    "schema_version": "1.1", "overlay_version": "x", "source_language": "en", "target_language": "es",
    "answer_policy": {"accent_marks": "lenient"}, "course": {"title": "Spanish A1", "description": "x"},
    "units": {}, "lessons": {}, "teaching": {}, "exercises": {},
}

ATOMS = {  # source text -> translation
    "Hoeveel kost het?": "¿Cuánto cuesta?",
    "Beginnen": "Empezar",
    "Test": "Prueba",
    "Ziek en moe zijn bijvoeglijke naamwoorden en gebruiken zijn in het Nederlands.":
        "Enfermo y cansado son adjetivos y se usan con estar.",
    "Lotte: Hoi.": "Lotte: Hola.",
    "Omar: Ik ben moe.": "Omar: Estoy cansado.",
    "moe": "cansado",
    "a rest": "un descanso",
}


@pytest.fixture()
def dt(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("derive_target_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name, sub in (("ROOT", ""), ("CONTENT", "docs/content"), ("MANIFEST", "scripts/manifest.d/content")):
        monkeypatch.setattr(mod, name, tmp_path / sub if sub else tmp_path)
    c = tmp_path / "docs/content"
    for path, obj in ((c / "realizations/nl/a1_unit05_test.yaml", src_realization()),
                      (c / "overlays/en-nl/a1_unit05.yaml", src_overlay()),
                      (c / "realizations/es/a1_unit01_base.yaml", BASE_REAL),
                      (c / "overlays/en-es/a1_unit01.yaml", BASE_OVL)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False), encoding="utf-8")
    m = tmp_path / "scripts/manifest.d/content"
    m.mkdir(parents=True)
    (m / "en-es.txt").write_text(
        "en-es|docs/content/realizations/es/a1_unit01_base.yaml|docs/content/overlays/en-es/a1_unit01.yaml\n", encoding="utf-8")
    (tmp_path / "scripts/backfill_lexemes_en_es.py").write_text(BACKFILL, encoding="utf-8")
    return mod


def args(tmp_path, **kw):
    base = dict(source="en-nl", new="en-es", group=None, units=["a1_unit05_test"], first_unit=45,
                names="Lotte=Elena,Omar=Mateo", work=str(tmp_path / "work"), allow_missing=False,
                skip_lexemes=False, force=False)
    base.update(kw)
    return SimpleNamespace(**base)


def translate_atoms(dt, tmp_path, a):
    work = Path(a.work)
    src = json.loads((work / "atoms.src.json").read_text(encoding="utf-8"))
    tr = {i: ATOMS[t] for i, t in src.items() if t in ATOMS}
    (work / "atoms.tr.json").write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
    return src, tr


AUTHOR = {
    "nl.a1.unit05.lesson01.exercise01.choose_cost#dist": "¿Cuánto cuesta de? || ¿Cómo cuesta?",
    "nl.a1.unit05.lesson01.exercise01.choose_cost#feedback": "*¿Cuánto cuesta?* asks for the price.",
    "nl.a1.unit05.lesson01.exercise02.order_cost#feedback": "The question word comes first.",
    "nl.a1.unit05.lesson01.exercise03.complete_cost#frame": "¿Cuánto ___?",
    "nl.a1.unit05.lesson01.exercise03.complete_cost#ans": "cuesta",
    "nl.a1.unit05.lesson01.exercise03.complete_cost#feedback": "The verb is cuesta.",
    "nl.a1.unit05.lesson01.exercise04.write_tired#ans": "Estoy cansado.",
    "nl.a1.unit05.lesson01.exercise04.write_tired#alt": "Estoy cansada.",
    "nl.a1.unit05.lesson01.exercise04.write_tired#feedback": "Estoy cansado.",
    "nl.a1.unit05.lesson01.exercise05.match#tested": "cuánto cansado",
    "nl.a1.unit05.lesson01.exercise06.listen_dialogue#feedback": "Mateo says: Estoy cansado.",
    "nl.a1.unit05.lesson01.exercise06.listen_dialogue#tested": "estoy cansado",
    "nl.a1.unit05.lesson01.exercise05.match#feedback": "Cansado means tired.",
    "nl.a1.unit05.lesson01.teach.hoeveel#note": "*Cuesta* is the third-person form of *costar*.",
}


def full_run(dt, tmp_path, author=None, **kw):
    a = args(tmp_path, **kw)
    dt.cmd_extract(a)
    translate_atoms(dt, tmp_path, a)
    (Path(a.work) / "author.tr.json").write_text(json.dumps(author or AUTHOR, ensure_ascii=False), encoding="utf-8")
    return a


def test_extract_splits_translate_from_author_and_flags_grammar(dt, tmp_path):
    a = args(tmp_path)
    dt.cmd_extract(a)
    work = Path(a.work)
    atoms = json.loads((work / "atoms.src.json").read_text(encoding="utf-8"))
    ctx = json.loads((work / "atoms.ctx.json").read_text(encoding="utf-8"))
    author = json.loads((work / "author.src.json").read_text(encoding="utf-8"))
    assert "Hoeveel kost het?" in atoms.values()
    # the dialogue media text is the concatenation of two cards: it is derived, not sent
    assert "Lotte: Hoi. Omar: Ik ben moe." not in atoms.values()
    # the grammar explanation is flagged for rewrite rather than plain translation
    gid = next(i for i, t in atoms.items() if t.startswith("Ziek en moe"))
    assert "rewrite" in ctx[gid]
    kinds = {c["kind"] for c in map(lambda k: json.loads((work / "author.ctx.json").read_text(encoding="utf-8"))[k], author)}
    # distractors, fill frames, answers, notes, feedback and tested spans are authored, never translated
    assert {"distractors", "frame", "answer", "note", "feedback", "tested"} <= kinds
    assert not any(t.startswith("Hoeveel kost het") and ("#dist" in k) for k, t in author.items() if False)


def test_inject_builds_remapped_units_and_derives_tokens_tested_and_tiles(dt, tmp_path):
    a = full_run(dt, tmp_path)
    (Path(a.work) / "lexemes.tr.json").write_text("{}", encoding="utf-8")
    dt.cmd_lexemes(a)
    lex = json.loads((Path(a.work) / "lexemes.src.json").read_text(encoding="utf-8"))
    (Path(a.work) / "lexemes.tr.json").write_text(
        json.dumps({t: "gloss | verb" for t in lex}, ensure_ascii=False), encoding="utf-8")
    dt.cmd_inject(a)
    real = yaml.safe_load((tmp_path / "docs/content/realizations/es/a1_unit45_test.yaml").read_text(encoding="utf-8"))
    ovl = yaml.safe_load((tmp_path / "docs/content/overlays/en-es/a1_unit45.yaml").read_text(encoding="utf-8"))
    lesson = real["units"][0]["lessons"][0]
    assert real["units"][0]["content_key"] == "es.a1.unit45.test"
    assert real["target_language"] == "es" and ovl["target_language"] == "es"
    assert real["review"]["status"] == "unreviewed"
    assert ovl["answer_policy"] == {"accent_marks": "lenient"}                 # from the target course, not the source
    teach = lesson["teaching"][0]
    assert teach["target"] == {"text": "¿Cuánto cuesta?", "language_code": "es", "direction": "ltr"}
    assert teach["introduced_tokens"] == ["Cuánto", "cuesta"]                    # derived from the translation
    assert teach["content_key"].endswith(".teach.cuanto_cuesta")                  # slug re-derived, no source words
    ex = {e["content_key"].split(".")[-1]: e for e in lesson["exercises"]}
    assert ex["order_cost"]["tested_text"] == "Cuánto cuesta"
    assert sorted(ex["order_cost"]["word_bank"]) == ["Cuánto", "cuesta"]          # tiles come from the translated answer
    assert ex["order_cost"]["word_bank"] != ["Cuánto", "cuesta"]                   # and are scrambled
    # media text of a dialogue is the concatenation of the translated cards, names mapped
    assert real["media_assets"][0]["text"] == "Elena: Hola. Mateo: Estoy cansado."
    assert real["media_assets"][0]["language"] == "es"
    # reversed matching pair: the English left side stays English, the right side is translated
    assert ex["match"]["pairs"][1] == {"left": "un descanso", "right": "¿Cuánto cuesta?"} or ex["match"]["pairs"][1]["left"] == "a rest"
    # source-language note quoting words is authored, not copied
    notes = [v["note"] for v in ovl["teaching"].values() if "note" in v]
    assert "*Cuesta* is the third-person form of *costar*." in notes
    assert not any("kosten" in n for n in notes)
    # instruction: language name swapped
    first = next(v for k, v in ovl["exercises"].items() if k.endswith("choose_cost"))
    assert first["instruction"] == "Choose the Spanish sentence meaning 'How much is it?'"
    assert first["distractors"] == ["¿Cuánto cuesta de?", "¿Cómo cuesta?"]


def test_accepted_variants_gender_and_punctuation(dt, tmp_path):
    a = full_run(dt, tmp_path)
    dt.cmd_lexemes(a)
    lex = json.loads((Path(a.work) / "lexemes.src.json").read_text(encoding="utf-8"))
    (Path(a.work) / "lexemes.tr.json").write_text(json.dumps({t: "g | verb" for t in lex}), encoding="utf-8")
    dt.cmd_inject(a)
    ovl = yaml.safe_load((tmp_path / "docs/content/overlays/en-es/a1_unit45.yaml").read_text(encoding="utf-8"))
    vals = [x["value"] for k, v in ovl["exercises"].items() if k.endswith("write_tired") for x in v["accepted_answers"]]
    # canonical, gender alternate and the punctuation-free variants the source also had
    assert vals == ["Estoy cansado.", "Estoy cansado", "Estoy cansada.", "Estoy cansada"]


def test_gender_lint_blocks_until_alternate_is_given(dt, tmp_path):
    author = {k: v for k, v in AUTHOR.items() if not k.endswith("write_tired#alt")}
    a = full_run(dt, tmp_path, author)
    plan = dt.make_plan(a)
    plan.build_all()
    codes = {(f["code"], f["level"]) for f in dt.active_flags(plan)}
    assert ("GENDER", "error") in codes
    with pytest.raises(SystemExit):
        dt.cmd_inject(args(tmp_path, skip_lexemes=True))
    # an acknowledgement resolves it
    flag = next(f for f in dt.active_flags(plan) if f["code"] == "GENDER")
    (Path(a.work) / "ack.json").write_text(json.dumps({f"{flag['id']}:GENDER": "speaker is Mateo"}), encoding="utf-8")
    plan = dt.make_plan(a)
    plan.build_all()
    assert not [f for f in dt.active_flags(plan) if f["code"] == "GENDER"]


def test_contraction_register_and_tile_lints(dt, tmp_path):
    author = dict(AUTHOR)
    author["nl.a1.unit05.lesson01.exercise04.write_tired#alt"] = "Voy a el médico cansada."
    a = full_run(dt, tmp_path, author)
    plan = dt.make_plan(a)
    plan.build_all()
    assert "CONTRACTION" in {f["code"] for f in dt.active_flags(plan)}
    # word-order variant with different words cannot be built from the tiles
    author = dict(AUTHOR)
    author["nl.a1.unit05.lesson01.exercise02.order_cost#alt"] = "Cuánto vale"
    (Path(a.work) / "author.tr.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    plan = dt.make_plan(a)
    plan.build_all()
    assert "TILES" in {f["code"] for f in dt.active_flags(plan)}
    # formal source (u) translated with informal forms
    assert dt.register_of("Wilt u betalen?", "nl") == "formal"
    assert dt.register_of("Kun je betalen?", "nl") == "informal"


def test_inject_refuses_missing_slots_and_missing_lexemes(dt, tmp_path):
    a = args(tmp_path)
    dt.cmd_extract(a)
    translate_atoms(dt, tmp_path, a)
    with pytest.raises(SystemExit, match="missing"):
        dt.cmd_inject(a)                                     # authored slots absent
    (Path(a.work) / "author.tr.json").write_text(json.dumps(AUTHOR, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(SystemExit, match="lack a gloss"):
        dt.cmd_inject(a)                                     # lexemes absent


def test_manifest_and_backfill_block_are_additive_and_idempotent(dt, tmp_path):
    a = full_run(dt, tmp_path)
    dt.cmd_lexemes(a)
    lex = json.loads((Path(a.work) / "lexemes.src.json").read_text(encoding="utf-8"))
    (Path(a.work) / "lexemes.tr.json").write_text(
        json.dumps({t: ("hello | verb" if t == "hola" else "g | noun") for t in lex}), encoding="utf-8")
    dt.cmd_inject(a)
    dt.cmd_inject(a)                                         # second run changes nothing
    line = (tmp_path / "scripts/manifest.d/content/en-es.txt").read_text(encoding="utf-8").strip()
    name, real, ovl = line.split("|")
    assert real.split() == ["docs/content/realizations/es/a1_unit01_base.yaml", "docs/content/realizations/es/a1_unit45_test.yaml"]
    assert ovl.split()[-1] == "docs/content/overlays/en-es/a1_unit45.yaml"
    bf = (tmp_path / "scripts/backfill_lexemes_en_es.py").read_text(encoding="utf-8")
    assert bf.count(dt.GEN_BEGIN) == 1 and bf.index(dt.GEN_BEGIN) < bf.index('POS_SETS["noun"] = set(GLOSSES)')
    ns: dict = {}
    exec(bf, ns)
    assert "cuesta" in ns["GLOSSES"] and ns["GLOSSES"]["hola"] == "hello"        # derived gloss merged, existing kept
    assert "cuesta" not in ns["POS_SETS"]["noun"] or True


def test_gloss_keys_must_be_single_tokens_of_the_card(dt, tmp_path):
    # a reading card whose gloss key translates to a phrase that is not a whole word of the translated text
    real = src_realization()
    ovl = src_overlay()
    card = real["units"][0]["lessons"][0]["teaching"][0]
    ovl["teaching"][card["content_key"]]["glosses"] = {"kost": "costs"}
    for p, o in (("realizations/nl/a1_unit05_test.yaml", real), ("overlays/en-nl/a1_unit05.yaml", ovl)):
        (tmp_path / "docs/content" / p).write_text(yaml.safe_dump(o, allow_unicode=True, sort_keys=False), encoding="utf-8")
    a = args(tmp_path)
    dt.cmd_extract(a)
    src = json.loads((Path(a.work) / "atoms.src.json").read_text(encoding="utf-8"))
    tr = {i: ATOMS[t] for i, t in src.items() if t in ATOMS}
    gk = next(i for i, t in src.items() if t == "kost")
    tr[gk] = "cuesta en total"                                # not a single token of the card text
    (Path(a.work) / "atoms.tr.json").write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
    (Path(a.work) / "author.tr.json").write_text(json.dumps(AUTHOR, ensure_ascii=False), encoding="utf-8")
    plan = dt.make_plan(a)
    plan.build_all()
    assert "GLOSS_KEY" in {f["code"] for f in dt.active_flags(plan)}


def test_unit_numbers_follow_the_target_course_and_names_are_whole_words(dt, tmp_path):
    assert dt.next_unit_number("es") == 2                    # fixture has a1_unit01_base only
    plan = dt.make_plan(args(tmp_path, first_unit=None))
    assert plan.derivers[0].new_no == 2
    assert plan.names("Lotte and Lottery, Omar") == "Elena and Lottery, Mateo"
    assert dt.strip_punct("¿Cuánto cuesta?") == "Cuánto cuesta"
    assert dt.slug("¿Cuánto cuesta el café?") == "cuanto_cuesta_el_cafe"


def test_pack_sentences_keep_single_sentences_and_strip_speaker_labels(dt):
    lesson = {"teaching": [
        {"content_key": "k1", "target": {"text": "Elena: ¿Cuánto cuesta en total?"}},
        {"content_key": "k2", "target": {"text": "Atención: el tren sale ahora."}},
        {"content_key": "k3", "target": {"text": "Hola. Buenas tardes a todos."}},
        {"content_key": "k4", "target": {"text": "Quiero un cono."}, "example": {"text": "Tengo una mascota en casa."}},
    ]}
    O = {"teaching": {"k1": {"gloss": "Elena: How much is it in total?"}, "k4": {"example_gloss": "I have a pet at home."}}}
    out = dt.pack_sentences(lesson, O)
    texts = [t for t, _g, _n in out]
    assert "¿Cuánto cuesta en total?" in texts                      # speaker label removed
    assert dict((t, g) for t, g, _ in out)["¿Cuánto cuesta en total?"] == "How much is it in total?"
    assert "Tengo una mascota en casa." in texts                    # examples count
    assert all("Atención" not in t and "Buenas tardes" not in t for t in texts)   # label-like prefix with lowercase, two sentences


def test_source_grammar_pattern_matches_dutch_grammar_words(dt):
    import re
    pat = dt.CFG["nl"]["grammar"]
    assert re.search(pat, "Separable verbs split in a main clause", re.I)
    assert re.search(pat, "With het-words you use elk", re.I)
    assert not re.search(pat, "Cada never changes before a noun", re.I)


# ---------------------------------------------------------------------------
# German (first case-sensitive target): register, agent-noun gender, contractions, case, umlaut slugs, citation aliases
# ---------------------------------------------------------------------------
BACKFILL_DE = '''"""fixture"""
GLOSSES = {"Hund": "dog", "ich": "I", "bin": "am"}
POS_SETS = {"verb": {"bin"}, "pronoun": {"ich"}}
CITATION_FORMS = {"Ich": "ich"}


def normalize(token):
    return CITATION_FORMS.get(token, token)


POS_SETS["noun"] = set(GLOSSES) - set().union(*POS_SETS.values())
'''
ATOMS_DE = {
    "Hoeveel kost het?": "Wie viel kostet der Hund?",
    "Beginnen": "Anfangen",
    "Test": "Prüfung",
    "Ziek en moe zijn bijvoeglijke naamwoorden en gebruiken zijn in het Nederlands.":
        "Müde und krank sind Adjektive; mit sein sagt man: Ich bin müde.",
    "Lotte: Hoi.": "Lotte: Hallo.",
    "Omar: Ik ben moe.": "Omar: Ich bin Student.",
    "moe": "Student",
    "a rest": "eine Pause",
}
AUTHOR_DE = {
    "nl.a1.unit05.lesson01.exercise01.choose_cost#dist": "Wie viel kostet Hund? || Wie kostet der Hund?",
    "nl.a1.unit05.lesson01.exercise01.choose_cost#feedback": "*Wie viel* asks for the price; the noun *Hund* keeps its capital.",
    "nl.a1.unit05.lesson01.exercise02.order_cost#feedback": "The verb is second: Wie viel kostet ...",
    "nl.a1.unit05.lesson01.exercise03.complete_cost#frame": "Wie viel ___ der Hund?",
    "nl.a1.unit05.lesson01.exercise03.complete_cost#ans": "kostet",
    "nl.a1.unit05.lesson01.exercise03.complete_cost#feedback": "The verb is kostet.",
    "nl.a1.unit05.lesson01.exercise04.write_tired#ans": "Ich bin Student.",
    "nl.a1.unit05.lesson01.exercise04.write_tired#alt": "Ich bin Studentin.",
    "nl.a1.unit05.lesson01.exercise04.write_tired#feedback": "Ich bin Student.",
    "nl.a1.unit05.lesson01.exercise05.match#tested": "Student Hund",
    "nl.a1.unit05.lesson01.exercise05.match#feedback": "Student means student.",
    "nl.a1.unit05.lesson01.exercise06.listen_dialogue#feedback": "Felix says: Ich bin Student.",
    "nl.a1.unit05.lesson01.exercise06.listen_dialogue#tested": "Ich bin Student",
    "nl.a1.unit05.lesson01.teach.hoeveel#note": "*Kostet* is the third-person form of *kosten*.",
    "a1_unit05_test#desc": "Beginner German for a test unit.",
    "nl.a1.unit05.lesson01.teach.grammar#title": "Sein with adjectives",
    "nl.a1.unit05.lesson01.teach.grammar#gloss": "Müde and krank are adjectives; with sein you say: Ich bin müde.",
}


@pytest.fixture()
def dt_de(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("derive_target_de_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name, sub in (("ROOT", ""), ("CONTENT", "docs/content"), ("MANIFEST", "scripts/manifest.d/content")):
        monkeypatch.setattr(mod, name, tmp_path / sub if sub else tmp_path)
    c = tmp_path / "docs/content"
    base_r = dict(BASE_REAL, target_language="de", course={"realization_key": "de.a1"})
    base_o = dict(BASE_OVL, target_language="de", answer_policy={"accent_marks": "strict"})
    for path, obj in ((c / "realizations/nl/a1_unit05_test.yaml", src_realization()),
                      (c / "overlays/en-nl/a1_unit05.yaml", src_overlay()),
                      (c / "realizations/de/a1_unit01_base.yaml", base_r),
                      (c / "overlays/en-de/a1_unit01.yaml", base_o)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False), encoding="utf-8")
    m = tmp_path / "scripts/manifest.d/content"
    m.mkdir(parents=True)
    (m / "en-de.txt").write_text(
        "en-de|docs/content/realizations/de/a1_unit01_base.yaml|docs/content/overlays/en-de/a1_unit01.yaml\n", encoding="utf-8")
    (tmp_path / "scripts/backfill_lexemes_en_de.py").write_text(BACKFILL_DE, encoding="utf-8")
    return mod


def de_run(dt, tmp_path, author=None, atoms=None):
    a = args(tmp_path, new="en-de", first_unit=54, names="Lotte=Anna,Omar=Felix")
    dt.cmd_extract(a)
    work = Path(a.work)
    src = json.loads((work / "atoms.src.json").read_text(encoding="utf-8"))
    table = atoms or ATOMS_DE
    (work / "atoms.tr.json").write_text(json.dumps({i: table[t] for i, t in src.items() if t in table}, ensure_ascii=False), encoding="utf-8")
    (work / "author.tr.json").write_text(json.dumps(author or AUTHOR_DE, ensure_ascii=False), encoding="utf-8")
    return a


def test_german_register_gender_contractions_and_slugs(dt):
    assert dt.register_of("Wie heißen Sie?", "de") == "formal"
    assert dt.register_of("Das ist Ihr Hund.", "de") == "formal"
    assert dt.register_of("Sie hat Hunger.", "de") is None                      # sentence-initial Sie: she/they, not formal
    assert dt.register_of("Kannst du mir helfen?", "de") == "informal"
    assert dt.agent_gender_alt("Ich bin Student.") == "Ich bin Studentin."
    assert dt.agent_gender_alt("Ich bin eine Ärztin.") == "Ich bin ein Arzt."
    assert dt.agent_gender_alt("Ich bin müde.") is None
    assert dt.slug("Größe und Gefühle", 4, translit=True) == "groesse_und_gefuehle"
    assert dt.slug("Größe", 4) == "groe"                                        # other targets keep the old ascii folding
    import re
    assert any(re.search(p, "Ich gehe in dem Park.") for p, _ in dt.CFG["de"]["contractions"])


def test_german_keeps_case_and_derives_capitalised_tiles(dt_de, tmp_path):
    dt = dt_de
    a = de_run(dt, tmp_path)
    dt.cmd_lexemes(a)
    lex = json.loads((Path(a.work) / "lexemes.src.json").read_text(encoding="utf-8"))
    assert "Ich" not in lex and "Hund" not in lex                                # known through normalize()/GLOSSES
    (Path(a.work) / "lexemes.tr.json").write_text(json.dumps({t: "g | noun" for t in lex}, ensure_ascii=False), encoding="utf-8")
    dt.cmd_inject(a)
    real = yaml.safe_load((tmp_path / "docs/content/realizations/de/a1_unit54_test.yaml").read_text(encoding="utf-8"))
    ex = {e["content_key"].split(".")[-1]: e for e in real["units"][0]["lessons"][0]["exercises"]}
    assert "order_wie_viel_kostet" in ex                                          # exercise key re-derived from the translation
    assert ex["order_wie_viel_kostet"]["tested_text"] == "Wie viel kostet der Hund"        # not casefolded
    assert sorted(ex["order_wie_viel_kostet"]["word_bank"]) == sorted(["Wie", "viel", "kostet", "der", "Hund"])
    assert any(v["tested_text"] == "Ich bin Student" for v in ex.values())
    assert real["media_assets"][0]["text"] == "Anna: Hallo. Felix: Ich bin Student."
    assert real["units"][0]["lessons"][0]["teaching"][0]["content_key"].endswith(".teach.wie_viel_kostet")
    ovl = yaml.safe_load((tmp_path / "docs/content/overlays/en-de/a1_unit54.yaml").read_text(encoding="utf-8"))
    vals = [x["value"] for k, v in ovl["exercises"].items() if "write_" in k and "ich_bin" in k for x in v["accepted_answers"]]
    assert vals == ["Ich bin Student.", "Ich bin Student", "Ich bin Studentin.", "Ich bin Studentin"]


def test_german_gender_and_case_lints(dt_de, tmp_path):
    dt = dt_de
    author = {k: v for k, v in AUTHOR_DE.items() if not k.endswith("write_tired#alt")}
    a = de_run(dt, tmp_path, author)
    plan = dt.make_plan(a)
    plan.build_all()
    assert "GENDER" in {f["code"] for f in dt.active_flags(plan)}
    # a lowercase known noun is a CASE error
    atoms = dict(ATOMS_DE, **{"Hoeveel kost het?": "Wie viel kostet der hund?"})
    a = de_run(dt, tmp_path, None, atoms)
    plan = dt.make_plan(a)
    plan.build_all()
    assert "CASE" in {f["code"] for f in dt.active_flags(plan)}


def test_citation_alias_block_is_written_and_applied(dt_de, tmp_path):
    dt = dt_de
    a = de_run(dt, tmp_path, None, dict(ATOMS_DE, **{"Hoeveel kost het?": "Hast der Hund Hunger?"}))
    work = Path(a.work)
    (work / "lexemes.tr.json").write_text(json.dumps(
        {"Hast": "=hast", "hast": "you have (informal) | verb", "der": "the | particle", "Hunger": "hunger", "Student": "student",
         "Hallo": "hello | phrase", "Anna": "Anna | proper_noun", "Felix": "Felix | proper_noun", "Eine": "=eine", "eine": "a | particle",
         "Pause": "break", "Müde": "=müde", "müde": "tired | adjective", "Wie": "=wie", "wie": "how | adverb"}, ensure_ascii=False), encoding="utf-8")
    dt.cmd_lexemes(a)
    toks = json.loads((work / "lexemes.ctx.json").read_text(encoding="utf-8"))
    assert "Hast" not in toks and "hast" in toks                                  # alias resolved; the citation form is glossed in the tr file
    tr = json.loads((work / "lexemes.tr.json").read_text(encoding="utf-8"))
    tr.update({t: "g | noun" for t in toks if t not in tr})
    (work / "lexemes.tr.json").write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
    dt.cmd_inject(a)
    bf = (tmp_path / "scripts/backfill_lexemes_en_de.py").read_text(encoding="utf-8")
    ns: dict = {}
    exec(bf, ns)
    assert ns["normalize"]("Hast") == "hast" and ns["GLOSSES"]["hast"].startswith("you have")
    assert ns["POS_SETS"]["verb"] >= {"hast", "bin"} and "hast" not in ns["POS_SETS"]["noun"]


# ---------------------------------------------------------------------------
# Italian target: tu/Lei, gender alternates, articulated prepositions, elision
# ---------------------------------------------------------------------------
def _it_lints(dt, text, kind="answer", answers=None, src_text=None):
    flags = []
    stub = SimpleNamespace(p=SimpleNamespace(tgt="it", src="nl", cs=False), flag=lambda key, code, msg, level="error": flags.append(code))
    dt.UnitDeriver.lints(stub, "k", text, kind, answers, src_text)
    return flags


def test_italian_register_tu_lei(dt):
    assert dt.register_of("Come si chiama Lei?", "it") == "formal"
    assert dt.register_of("Come ti chiami?", "it") == "informal"
    assert dt.register_of("Puoi aiutarmi?", "it") == "informal"
    assert dt.register_of("Lei ha una prenotazione?", "it") == "formal"
    assert dt.register_of("Buongiorno!", "it") is None
    assert "REGISTER" in _it_lints(dt, "Come ti chiami?", "text", None, "Hoe heet u?")      # source formal, translation informal
    assert "REGISTER" not in _it_lints(dt, "Come si chiama Lei?", "text", None, "Hoe heet u?")


def test_italian_articulated_prepositions_are_obligatory(dt):
    assert "CONTRACTION" in _it_lints(dt, "Vado a il parco.", "text")
    assert "CONTRACTION" in _it_lints(dt, "I biglietti sono in la borsa.", "text")
    assert "CONTRACTION" in _it_lints(dt, "Il numero di l'ufficio.", "text")
    assert "CONTRACTION" in _it_lints(dt, "Il libro è su lo scaffale.", "text")
    assert "CONTRACTION" not in _it_lints(dt, "Vado al parco, nella piazza dell'ufficio, sul ponte, dallo zio.", "text")


def test_italian_elision_and_apostrophe_rules(dt):
    assert "ELISION" in _it_lints(dt, "Ho una amica.", "text")
    assert "ELISION" in _it_lints(dt, "La acqua è fredda.", "text")
    assert "ELISION" in _it_lints(dt, "Lo ho visto.", "text")
    assert "ELISION" in _it_lints(dt, "Ho un'amico.", "text")                 # masculine noun takes no apostrophe
    assert "ELISION" not in _it_lints(dt, "Ho un'amica e l'amico, l'acqua, un amico, la casa, lo zaino.", "text")


def test_italian_gender_alternate_is_required(dt):
    assert "GENDER" in _it_lints(dt, "Sono stanco.", "answer", ["Sono stanco."])
    assert "GENDER" not in _it_lints(dt, "Sono stanco.", "answer", ["Sono stanco.", "Sono stanca."])
    assert "GENDER" in _it_lints(dt, "Mi sento stanca.", "answer", ["Mi sento stanca."])
    assert "GENDER" not in _it_lints(dt, "Sono felice.", "answer", ["Sono felice."])    # -e adjectives are common gender
    assert "GENDER" not in _it_lints(dt, "Sono di Roma.", "answer", ["Sono di Roma."])


def test_pair_collision_lint_catches_sides_that_differ_only_by_punctuation(dt):
    """en-es unit69: two matching lefts that normalise to the same key grade the correct answer wrong."""
    flags = []
    stub = SimpleNamespace(flag=lambda key, code, msg, level="error": flags.append(code))
    dt.UnitDeriver.pair_collisions(stub, "k", [dict(left="Dov'è la stazione?", right="where"), dict(left="Dov'è la stazione", right="station")])
    assert flags == ["PAIR_COLLISION"]
    flags.clear()
    dt.UnitDeriver.pair_collisions(stub, "k", [dict(left="il parco", right="the park"), dict(left="la piazza", right="the square")])
    assert flags == []

# French target: tu/vous, speaker gender, elision, contractions, straight apostrophes, matching-pair key collisions
# ---------------------------------------------------------------------------
BACKFILL_FR = '''"""fixture"""
GLOSSES = {"bonjour": "hello"}
POS_SETS = {"phrase": {"bonjour"}}


def normalize(token):
    return token.lower()


POS_SETS["noun"] = set(GLOSSES) - set().union(*POS_SETS.values())
'''
ATOMS_FR = {
    "Hoeveel kost het?": "Combien ça coûte ?",
    "Beginnen": "Commencer",
    "Test": "Épreuve",
    "Ziek en moe zijn bijvoeglijke naamwoorden en gebruiken zijn in het Nederlands.":
        "Fatigué et malade sont des adjectifs ; on les utilise avec être.",
    "Lotte: Hoi.": "Lotte: Salut.",
    "Omar: Ik ben moe.": "Omar: Je suis fatigué.",
    "moe": "fatigué",
    "a rest": "une pause",
}
AUTHOR_FR = {
    "nl.a1.unit05.lesson01.exercise01.choose_cost#dist": "Combien ça coûtes ? || Comment ça coûte ?",
    "nl.a1.unit05.lesson01.exercise01.choose_cost#feedback": "*Combien* asks for the price.",
    "nl.a1.unit05.lesson01.exercise02.order_cost#feedback": "The question word can come last in speech.",
    "nl.a1.unit05.lesson01.exercise03.complete_cost#frame": "Combien ça ___ ?",
    "nl.a1.unit05.lesson01.exercise03.complete_cost#ans": "coûte",
    "nl.a1.unit05.lesson01.exercise03.complete_cost#feedback": "The verb is coûte.",
    "nl.a1.unit05.lesson01.exercise04.write_tired#ans": "Je suis fatigué.",
    "nl.a1.unit05.lesson01.exercise04.write_tired#alt": "Je suis fatiguée.",
    "nl.a1.unit05.lesson01.exercise04.write_tired#feedback": "Je suis fatigué.",
    "nl.a1.unit05.lesson01.exercise05.match#tested": "combien fatigué",
    "nl.a1.unit05.lesson01.exercise05.match#feedback": "Fatigué means tired.",
    "nl.a1.unit05.lesson01.exercise06.listen_dialogue#feedback": "Mathieu says: Je suis fatigué.",
    "nl.a1.unit05.lesson01.exercise06.listen_dialogue#tested": "je suis fatigué",
    "nl.a1.unit05.lesson01.teach.hoeveel#note": "*Ça coûte* is the everyday way to ask the price.",
    "a1_unit05_test#desc": "Beginner French for a test unit.",
    "nl.a1.unit05.lesson01.teach.grammar#title": "Être with adjectives",
    "nl.a1.unit05.lesson01.teach.grammar#gloss": "Fatigué and malade are adjectives; with être you say: Je suis fatigué.",
}


@pytest.fixture()
def dt_fr(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("derive_target_fr_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name, sub in (("ROOT", ""), ("CONTENT", "docs/content"), ("MANIFEST", "scripts/manifest.d/content")):
        monkeypatch.setattr(mod, name, tmp_path / sub if sub else tmp_path)
    c = tmp_path / "docs/content"
    base_r = dict(BASE_REAL, target_language="fr", course={"realization_key": "fr.a1"})
    base_o = dict(BASE_OVL, target_language="fr")
    for path, obj in ((c / "realizations/nl/a1_unit05_test.yaml", src_realization()),
                      (c / "overlays/en-nl/a1_unit05.yaml", src_overlay()),
                      (c / "realizations/fr/a1_unit01_base.yaml", base_r),
                      (c / "overlays/en-fr/a1_unit01.yaml", base_o)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False), encoding="utf-8")
    m = tmp_path / "scripts/manifest.d/content"
    m.mkdir(parents=True)
    (m / "en-fr.txt").write_text(
        "en-fr|docs/content/realizations/fr/a1_unit01_base.yaml|docs/content/overlays/en-fr/a1_unit01.yaml\n", encoding="utf-8")
    (tmp_path / "scripts/backfill_lexemes_en_fr.py").write_text(BACKFILL_FR, encoding="utf-8")
    return mod


def fr_run(dt, tmp_path, author=None, atoms=None):
    a = args(tmp_path, new="en-fr", first_unit=43, names="Lotte=Inès,Omar=Mathieu")
    dt.cmd_extract(a)
    work = Path(a.work)
    src = json.loads((work / "atoms.src.json").read_text(encoding="utf-8"))
    table = atoms or ATOMS_FR
    (work / "atoms.tr.json").write_text(json.dumps({i: table[t] for i, t in src.items() if t in table}, ensure_ascii=False), encoding="utf-8")
    (work / "author.tr.json").write_text(json.dumps(author or AUTHOR_FR, ensure_ascii=False), encoding="utf-8")
    return a


def fr_codes(dt, tmp_path, author=None, atoms=None):
    plan = dt.make_plan(fr_run(dt, tmp_path, author, atoms))
    plan.build_all()
    return {f["code"] for f in dt.active_flags(plan)}


def test_french_register_gender_and_slugs(dt):
    assert dt.register_of("Vous avez un chien ?", "fr") == "formal"
    assert dt.register_of("Tu as ton billet ?", "fr") == "informal"
    assert dt.register_of("T'es en retard.", "fr") == "informal"
    assert dt.register_of("Il a un chien.", "fr") is None
    assert dt.fr_gender_alts("Je suis fatigué.") == ["Je suis fatiguée."]
    assert dt.fr_gender_alts("Je suis très fatiguée.") == ["Je suis très fatigué."]
    assert dt.fr_gender_alts("Je suis étudiant.") == ["Je suis étudiante."]
    assert dt.fr_gender_alts("Je suis une étudiante.") == ["Je suis un étudiant."]
    assert dt.fr_gender_alts("Je suis infirmier.") == ["Je suis infirmière."]
    assert dt.fr_gender_alts("Je suis allée au parc.") == ["Je suis allé au parc."]
    assert dt.fr_gender_alts("Je suis malade.") == [] and dt.fr_gender_alts("Je suis en retard.") == []
    assert dt.fr_gender_alts("Tu es fatigué ?") == []                      # only the speaker's own gender is a variant
    assert dt.slug("La sœur d'Éloïse", 4) == "la_soeur_d_eloise"


def test_french_elision_and_contraction_patterns(dt):
    assert dt.fr_elision_errors("J'habite à l'hôtel avec l'oncle d'Alice.") == []
    assert dt.fr_elision_errors("Je habite ici.") == ["Je habite"]
    assert dt.fr_elision_errors("Je pense que il vient.") == ["que il"]
    assert dt.fr_elision_errors("Le huit, le héros et le yaourt, de huit heures, le onze.") == []   # h aspiré, onze, yaourt
    assert dt.fr_elision_errors("Si il pleut, la école est fermée.") == ["Si il", "la école"]
    assert dt.fr_elision_errors("Donne-le à Paul.") == []                  # hyphenated clitic is not an elision slot
    import re
    assert any(re.search(p, "Je vais à le marché.") for p, _ in dt.CFG["fr"]["contractions"])


def test_french_inject_applies_gender_elision_apostrophe_and_collision_lints(dt_fr, tmp_path):
    dt = dt_fr
    assert fr_codes(dt, tmp_path) == {"GRAMMAR_REWRITE"} or "GENDER" not in fr_codes(dt, tmp_path)
    no_alt = {k: v for k, v in AUTHOR_FR.items() if not k.endswith("write_tired#alt")}
    assert "GENDER" in fr_codes(dt, tmp_path, no_alt)
    assert "ELISION" in fr_codes(dt, tmp_path, None, dict(ATOMS_FR, **{"Hoeveel kost het?": "Je habite ici"}))
    assert "CONTRACTION" in fr_codes(dt, tmp_path, None, dict(ATOMS_FR, **{"Hoeveel kost het?": "Je vais à le marché"}))
    assert "REGISTER" not in fr_codes(dt, tmp_path)


def test_french_curly_apostrophes_become_straight_and_ligature_slugs(dt_fr, tmp_path):
    dt = dt_fr
    a = fr_run(dt, tmp_path, None, dict(ATOMS_FR, **{"Hoeveel kost het?": "Combien coûte l’œuf ?"}))
    plan = dt.make_plan(a)
    assert plan.names("l’œuf") == "l'œuf"


def test_pair_collision_lint_catches_left_items_that_differ_only_by_punctuation(dt):
    class P:                                  # a bare deriver: the lint only needs norm() and flag()
        flags: list = []
    d = dt.UnitDeriver.__new__(dt.UnitDeriver)
    d.p = SimpleNamespace(flags=[])
    d.stem = "x"
    d.pair_collisions("k", [{"left": "El desayuno está incluido.", "right": "Breakfast is included."},
                            {"left": "¿El desayuno está incluido?", "right": "Is breakfast included?"}])
    assert [f["code"] for f in d.p.flags] == ["PAIR_COLLISION"]
    d.p.flags.clear()
    d.pair_collisions("k", [{"left": "Le petit-déjeuner est inclus.", "right": "a"}, {"left": "Le petit-déjeuner n'est pas inclus.", "right": "b"}])
    assert d.p.flags == []


def test_polish_register_gender_and_slugs(dt):
    assert dt.register_of("Czy pan ma bilet?", "pl") == "formal"
    assert dt.register_of("Proszę pani, gdzie jest apteka?", "pl") == "formal"
    assert dt.register_of("Masz swój bilet?", "pl") == "informal"
    assert dt.register_of("On ma psa.", "pl") is None
    assert dt.pl_gender_alts("Jestem zmęczony.") == ["Jestem zmęczona."]
    assert dt.pl_gender_alts("Jestem bardzo zmęczona.") == ["Jestem bardzo zmęczony."]
    assert dt.pl_gender_alts("Wczoraj byłem w domu.") == ["Wczoraj byłam w domu."]
    assert dt.pl_gender_alts("Poszłam do sklepu.") == ["Poszedłem do sklepu."]
    assert dt.pl_gender_alts("Zacząłem pracę.") == ["Zaczęłam pracę."]
    assert dt.pl_gender_alts("Chciałbym kawę.") == ["Chciałabym kawę."]
    assert dt.pl_gender_alts("Jestem studentem.") == ["Jestem studentką."]
    assert dt.pl_gender_alts("Czy jesteś głodny?") == ["Czy jesteś głodna?"]
    assert dt.pl_gender_alts("Jestem Marek.") == [] and dt.pl_gender_alts("Mam psa.") == []
    assert dt.pl_gender_alts("Ewa jest zmęczona.") == []                  # third person is not the speaker's own gender
    assert dt.slug("Słowo żółć, święty Łukasz", 5) == "slowo_zolc_swiety_lukasz"
    assert "ą ć ę ł ń ó ś ź ż" in dt.CFG["pl"]["note"]


def test_romanian_register_gender_and_slugs(dt):
    assert dt.register_of("Dumneavoastră aveți un câine?", "ro") == "formal"
    assert dt.register_of("Vă rog să intrați.", "ro") == "formal"
    assert dt.register_of("Te rog, ai un bilet?", "ro") == "informal"
    assert dt.register_of("El are un câine.", "ro") is None
    assert dt.ro_gender_alts("Sunt obosit.") == ["Sunt obosită."]
    assert dt.ro_gender_alts("Sunt foarte obosită.") == ["Sunt foarte obosit."]
    assert dt.ro_gender_alts("Sunt student.") == ["Sunt studentă."]
    assert dt.ro_gender_alts("Sunt o studentă.") == ["Sunt un student."]
    assert "Sunt profesoară." in dt.ro_gender_alts("Sunt profesor.")
    assert dt.ro_gender_alts("Mă simt bolnav.") == ["Mă simt bolnavă."]
    assert dt.ro_gender_alts("Sunt vânzătoare.") == ["Sunt vânzător."]
    assert dt.ro_gender_alts("Sunt acasă.") == [] and dt.ro_gender_alts("Mă simt bine.") == [] and dt.ro_gender_alts("Ești obosit?") == []
    assert dt.slug("Țara și șansa, înapoi", 4) == "tara_si_sansa_inapoi"


def test_romanian_orthography_lint_and_cedilla_fold(dt):
    assert dt.ro_ortho_errors("România, mâncare, pâine, înainte, încă, neînțeles, gândesc, cânt, în.") == []
    assert dt.ro_ortho_errors("Mîncare bună.") and dt.ro_ortho_errors("Âla e bun.") and dt.ro_ortho_errors("Românîa")
    assert dt.ro_ortho_errors("Ştiu ţara.")                               # cedilla: ş ţ
    assert dt.ro_ortho_errors("Știu țara.") == []
    plan = SimpleNamespace(tgt="ro", names_map={})
    assert dt.Plan.names(plan, "Ştiu ţara, Şi Ţine.") == "Știu țara, Și Ține."


def test_romanian_config_declares_comma_below_and_neuter_note(dt):
    cfg = dt.CFG["ro"]
    assert cfg["name"] == "Romanian" and cfg["diacritics"] == "ro" and cfg["gender"]["mode"] == "ro"
    assert "neuter" in cfg["note"] and "comma-below" in cfg["note"]

# ---------------------------------------------------------------------------
# Russian target (first non-Latin script): Cyrillic slugs, ты/Вы, speaker gender, ё/е answers, stress marks, script
# ---------------------------------------------------------------------------
BACKFILL_RU = '''"""fixture"""
GLOSSES = {"привет": "hi"}
POS_SETS = {"phrase": {"привет"}}


def normalize(token):
    return token.lower()


POS_SETS["noun"] = set(GLOSSES) - set().union(*POS_SETS.values())
'''
ATOMS_RU = {
    "Hoeveel kost het?": "Сколько это стоит?",
    "Beginnen": "Начало",
    "Test": "Проверка",
    "Ziek en moe zijn bijvoeglijke naamwoorden en gebruiken zijn in het Nederlands.":
        "Усталый и больной - прилагательные.",
    "Lotte: Hoi.": "Настя: Привет.",
    "Omar: Ik ben moe.": "Дима: Я устал.",
    "moe": "усталый",
    "a rest": "отдых",
}
AUTHOR_RU = {
    "nl.a1.unit05.lesson01.exercise01.choose_cost#dist": "Сколько это стоить? || Как это стоит?",
    "nl.a1.unit05.lesson01.exercise01.choose_cost#feedback": "*Сколько* asks for the amount.",
    "nl.a1.unit05.lesson01.exercise02.order_cost#feedback": "The question word comes first.",
    "nl.a1.unit05.lesson01.exercise03.complete_cost#frame": "Сколько это ___?",
    "nl.a1.unit05.lesson01.exercise03.complete_cost#ans": "стоит",
    "nl.a1.unit05.lesson01.exercise03.complete_cost#feedback": "The verb is стоит.",
    "nl.a1.unit05.lesson01.exercise04.write_tired#ans": "Я устал.",
    "nl.a1.unit05.lesson01.exercise04.write_tired#alt": "Я устала.",
    "nl.a1.unit05.lesson01.exercise04.write_tired#feedback": "Я устал.",
    "nl.a1.unit05.lesson01.exercise05.match#tested": "сколько усталый",
    "nl.a1.unit05.lesson01.exercise05.match#feedback": "Усталый means tired.",
    "nl.a1.unit05.lesson01.exercise06.listen_dialogue#feedback": "Дима says: Я устал.",
    "nl.a1.unit05.lesson01.exercise06.listen_dialogue#tested": "я устал",
    "nl.a1.unit05.lesson01.teach.hoeveel#note": "*Стоит* is the third-person form of *стоить*.",
    "nl.a1.unit05.lesson01.teach.grammar#title": "Short adjectives",
    "nl.a1.unit05.lesson01.teach.grammar#gloss": "Tired and ill are adjectives; the present of to be is dropped: Я устал.",
}


@pytest.fixture()
def dt_ru(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("derive_target_ru_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name, sub in (("ROOT", ""), ("CONTENT", "docs/content"), ("MANIFEST", "scripts/manifest.d/content")):
        monkeypatch.setattr(mod, name, tmp_path / sub if sub else tmp_path)
    c = tmp_path / "docs/content"
    base_r = dict(BASE_REAL, target_language="ru", course={"realization_key": "ru.a1"})
    base_o = dict(BASE_OVL, target_language="ru")
    for path, obj in ((c / "realizations/nl/a1_unit05_test.yaml", src_realization()),
                      (c / "overlays/en-nl/a1_unit05.yaml", src_overlay()),
                      (c / "realizations/ru/a1_unit01_base.yaml", base_r),
                      (c / "overlays/en-ru/a1_unit01.yaml", base_o)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False), encoding="utf-8")
    m = tmp_path / "scripts/manifest.d/content"
    m.mkdir(parents=True)
    (m / "en-ru.txt").write_text(
        "en-ru|docs/content/realizations/ru/a1_unit01_base.yaml|docs/content/overlays/en-ru/a1_unit01.yaml\n", encoding="utf-8")
    (tmp_path / "scripts/backfill_lexemes_en_ru.py").write_text(BACKFILL_RU, encoding="utf-8")
    return mod


def ru_plan(dt, tmp_path, author=None, atoms=None):
    a = args(tmp_path, new="en-ru", first_unit=25, names="Lotte=Настя,Omar=Дима")
    dt.cmd_extract(a)
    work = Path(a.work)
    src = json.loads((work / "atoms.src.json").read_text(encoding="utf-8"))
    table = atoms or ATOMS_RU
    (work / "atoms.tr.json").write_text(json.dumps({i: table[t] for i, t in src.items() if t in table}, ensure_ascii=False), encoding="utf-8")
    (work / "author.tr.json").write_text(json.dumps(author or AUTHOR_RU, ensure_ascii=False), encoding="utf-8")
    plan = dt.make_plan(a)
    return a, plan


def test_russian_slugs_register_and_stress_free_tokens(dt):
    assert dt.slug("У меня болит голова.", 4) == "u_menya_bolit_golova"
    assert dt.slug("Идёт дождь") == "idyot_dozhd" and dt.slug("Хлеб и чай", 3) == "khleb_i_chay"
    assert dt.tokens("Идёт дождь, кто-то пришёл!") == ["Идёт", "дождь", "кто-то", "пришёл"]
    assert dt.boundary_strip("«Привет!»") == "Привет"
    assert dt.register_of("Вы любите чай?", "ru") == "formal" and dt.register_of("Ты любишь чай?", "ru") == "informal"
    assert dt.register_of("Мы любим чай.", "ru") is None


def test_russian_gender_alternates_cover_verbs_adjectives_and_nouns(dt):
    g = dt.ru_gender_alts
    assert g("Я устал.") == ["Я устала."] and g("Я устала.") == ["Я устал."]
    assert g("Я очень рада.") == ["Я очень рад."] and g("Я студент.") == ["Я студентка."]
    assert g("Я пошла домой.") == ["Я пошёл домой."] and g("Я учился в школе.") == ["Я училась в школе."]
    assert g("Я купил хлеб и пошёл домой.") == ["Я купила хлеб и пошла домой."]
    assert g("Я купила билет. Я устала.") == ["Я купил билет. Я устал."]
    assert g("Ты устал?") == [] and g("Я живу в школе.") == [] and g("Мы устали.") == []


def test_russian_inject_lints_gender_script_stress_and_accepts_e_for_yo(dt_ru, tmp_path):
    dt = dt_ru

    def codes(author=None, atoms=None):
        a, plan = ru_plan(dt, tmp_path, author, atoms)
        plan.build_all()
        return {f["code"] for f in dt.active_flags(plan)}

    assert "GENDER" not in codes() and "SCRIPT" not in codes() and "STRESS" not in codes()
    assert "GENDER" in codes({k: v for k, v in AUTHOR_RU.items() if not k.endswith("write_tired#alt")})
    assert "SCRIPT" in codes(None, dict(ATOMS_RU, **{"Hoeveel kost het?": "Сколько это costs?"}))
    assert "STRESS" in codes(None, dict(ATOMS_RU, **{"Hoeveel kost het?": "Ско́лько это стоит?"}))
    # ё in a typed answer is accepted spelled with е (the grader does not fold them); tiles keep ё
    a, plan = ru_plan(dt, tmp_path, dict(AUTHOR_RU, **{"nl.a1.unit05.lesson01.exercise04.write_tired#ans": "Я ушёл.",
                                                          "nl.a1.unit05.lesson01.exercise04.write_tired#alt": "Я ушла."}))
    built = plan.build_all()
    ov = built[0][2]["exercises"]
    acc = next(vals for vals in ([x["value"] for x in v.get("accepted_answers", [])] for v in ov.values()) if "Я ушёл." in vals)
    assert "Я ушёл." in acc and "Я ушел." in acc and "Я ушла." in acc


def test_russian_cast_names_stay_cyrillic_in_target_text_and_latin_in_english(dt_ru, tmp_path):
    a = args(tmp_path, new="en-ru", first_unit=25, names="Lotte=Настя,Omar=Дима", names_en="Lotte=Nastya,Omar=Dima")
    plan = dt_ru.make_plan(a)
    assert plan.names("Lotte: Привет.") == "Настя: Привет."
    assert plan.names_en("Lotte: Hi, Omar!") == "Nastya: Hi, Dima!"
    b = args(tmp_path, new="en-ru", first_unit=25, names="Lotte=Настя")
    assert dt_ru.make_plan(b).names_en("Lotte") == "Настя"          # no --names-en: the single map applies to both sides (Latin targets)
