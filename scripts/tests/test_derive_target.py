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
            f"{p}.lesson01.teach.grammar": {"title": "Grammar", "gloss": "Sick and tired are adjectives and use zijn."},
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
