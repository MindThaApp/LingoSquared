#!/usr/bin/env python3
"""Derive a new learner-language direction X->T from an existing sibling Y->T.

Every X->T direction shares the same target-language realizations and the same
practice-pack *structure*; only the learner-language strings differ (overlay
titles, glosses, notes, instructions, feedback, option texts, pack frame and
feedback texts, and the per-token lexeme gloss table).  This tool separates
those strings from the structure so the expensive step (writing them in the new
language) is a flat translation job instead of hand-authoring YAML:

    extract   sibling YAML  ->  flat, keyed *.src.json files + translator guide
    (translate: someone writes <name>.tr.json next to each <name>.src.json)
    inject    translations  ->  overlays, practice packs, manifest lines,
                                 backfill_lexemes_<x>_<t>.py
    validate  run the existing gates for the new direction
    status    show which ids still lack a translation

Typical run (derive es->en from de->en, A1):

    python3 scripts/derive_direction.py extract --sibling de-en --new es-en --levels a1
    #   -> .local/derive/es-en/*.src.json  (translate each into *.tr.json)
    python3 scripts/derive_direction.py inject  --sibling de-en --new es-en --levels a1
    python3 scripts/derive_direction.py validate --new es-en --levels a1

Strings that are identical to the same item in another sibling direction with a
different script (or in two or more siblings) are target-language text, numbers
or names and are never sent to the translator (the "witness" rule).  Strings
repeated across units (instructions, feedback, generic pack frames) are sent
once.  See docs/content/DIRECTION_PIPELINE.md for the workflow and its limits.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "docs/content"
MANIFEST = ROOT / "scripts/manifest.d/content"      # one <course_name>.txt per group
PRACTICE_MANIFEST = ROOT / "scripts/manifest.d/practice"  # one <pack_name>.txt per pack
DEFAULT_WORK = ROOT / ".local/derive"

# ---------------------------------------------------------------------------
# Language metadata (translator guide + RTL handling)
# ---------------------------------------------------------------------------
RTL = {"ar", "fa", "prs", "he", "ur"}
NON_LATIN = {"fa", "prs", "ar", "hi", "ru", "zh", "ja", "ko", "he", "ur", "uk", "el"}
LANG = {
    # code: (English name, native name, register / script notes for the translator)
    "en": ("English", "English", ""),
    "nl": ("Dutch", "Nederlands", "Informal jij-register toward the learner."),
    "de": ("German", "Deutsch", "Formal Sie toward the learner in instructions; du inside casual character dialogue."),
    "es": ("Spanish", "Espanol", "Neutral international Spanish. Address the learner as tu (informal) in instructions; use usted only for clerks/doctors/employers inside example dialogues. Inverted ?/! marks required."),
    "fr": ("French", "Francais", "Address the learner as tu in instructions; vous for clerks/doctors/employers inside dialogues. Use proper accents and typographic apostrophes consistently with the sibling."),
    "it": ("Italian", "Italiano", "Address the learner as tu; Lei for formal roles inside dialogues."),
    "ru": ("Russian", "Russkij", "Cyrillic. Address the learner as ty; vy for formal roles inside dialogues. Keep stress marks out."),
    "pl": ("Polish", "Polski", "Address the learner as ty; Pan/Pani for formal roles inside dialogues."),
    "ro": ("Romanian", "Romana", "Address the learner as tu; dumneavoastra for formal roles. Use comma-below s/t (ș ț), not cedilla."),
    "hi": ("Hindi", "Hindi", "Devanagari. Address the learner as aap in instructions; tum only between friends. Keep English words in Latin script."),
    "ar": ("Arabic (MSA)", "Arabic", "RTL, Modern Standard Arabic, no regional dialect. No tashkeel except where it disambiguates. Keep English words in Latin script."),
    "fa": ("Farsi (Iran)", "Farsi", "RTL, colloquial spoken Iranian Persian (mi-shé/mi-kone style), polite shoma toward the learner. Use ZWNJ in compounds and mi-/nemi- prefixes, Persian letters (ی ک), Persian digits not required."),
    "prs": ("Dari (Afghanistan)", "Dari", "RTL, colloquial Afghan Dari (mi-tanin/asta style). Use Afghan vocabulary, never Iranian-only words; must pass scripts/check_dari_register.py with 0 findings. Persian letters (ی ک), ZWNJ in compounds."),
    "zh": ("Chinese (Mandarin, Simplified)", "Zhongwen", "Simplified characters; no pinyin unless the sibling shows one. Use full-width punctuation."),
    "ja": ("Japanese", "Nihongo", "Polite desu/masu form; natural kana/kanji mix, no furigana unless the sibling has it."),
    "ko": ("Korean", "Hangugeo", "Polite haeyo-che (-yo) form."),
}


def lang_name(code: str) -> str:
    return LANG.get(code, (code, code, ""))[0]


# ---------------------------------------------------------------------------
# Manifests
# ---------------------------------------------------------------------------
def read_manifest(path: Path) -> "OrderedDict[str, list[list[str]]]":
    out: "OrderedDict[str, list[list[str]]]" = OrderedDict()
    files = sorted(path.glob("*.txt"), key=lambda p: p.name)
    lines = [l for fp in files for l in fp.read_text(encoding="utf-8").splitlines()]
    for line in lines:
        if not line.strip() or line.startswith("#") or "|" not in line:
            continue
        parts = line.split("|")
        out[parts[0]] = [p.split() for p in parts[1:]]
    return out


def pair_of(group: str) -> str:
    return "-".join(group.split("-")[:2])


def level_of(group: str) -> str:
    parts = group.split("-")
    return parts[2] if len(parts) > 2 else "a1"


def group_names(pair: str, levels: list[str]) -> list[str]:
    return [pair if lv == "a1" else f"{pair}-{lv}" for lv in levels]


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------
def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, width=100000, default_flow_style=False),
        encoding="utf-8",
    )


def realization_index(path: Path) -> dict[str, dict]:
    """content_key -> {type, tested, prompt, example, target} from a realization."""
    idx: dict[str, dict] = {}

    def walk(o):
        if isinstance(o, dict):
            ck = o.get("content_key")
            if isinstance(ck, str):
                info: dict = {}
                if "type" in o:
                    info["type"] = o["type"]
                if "tested_text" in o:
                    info["tested"] = o["tested_text"]
                pr = o.get("prompt")
                if isinstance(pr, dict):
                    blocks = pr.get("target_blocks") or []
                    info["prompt"] = " / ".join(b.get("text", "") for b in blocks if isinstance(b, dict))
                if isinstance(o.get("target"), dict):
                    info["target"] = o["target"].get("text", "")
                if isinstance(o.get("example"), dict):
                    info["example"] = o["example"].get("text", "")
                if "kind" in o:
                    info["kind"] = o["kind"]
                idx.setdefault(ck, {}).update(info)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(load(path))
    return idx


# ---------------------------------------------------------------------------
# Unit discovery
# ---------------------------------------------------------------------------
class Unit:
    def __init__(self, group: str, level: str, realization: Path, overlay: Path, pack: Path | None):
        self.group, self.level = group, level
        self.realization, self.overlay, self.pack = realization, overlay, pack
        self.stem = overlay.stem  # a1_unit01
        self.real_name = realization.name


def find_units(sibling: str, levels: list[str], only: list[str] | None) -> list[Unit]:
    cm = read_manifest(MANIFEST)
    pm = read_manifest(PRACTICE_MANIFEST)
    packs = {Path(p).stem: ROOT / p for p in (pm.get(sibling) or [[]])[0]}
    units: list[Unit] = []
    for g in group_names(sibling, levels):
        if g not in cm:
            sys.exit(f"sibling group {g!r} not in {MANIFEST.name}")
        reals, ovs = cm[g]
        for r, o in zip(reals, ovs):
            u = Unit(g, level_of(g), ROOT / r, ROOT / o, packs.get(Path(o).stem))
            if only and u.stem not in only:
                continue
            units.append(u)
    if not units:
        sys.exit("no units selected")
    return units


def witness_map(target: str, exclude: set[str]) -> dict[str, dict[str, Path]]:
    """realization file name -> {source_lang: overlay path} for other X->target directions."""
    out: dict[str, dict[str, Path]] = defaultdict(dict)
    for g, (reals, ovs) in read_manifest(MANIFEST).items():
        p = pair_of(g)
        s, t = p.split("-")
        if t != target or s in exclude or s == "en":
            continue
        for r, o in zip(reals, ovs):
            out[Path(r).name].setdefault(s, ROOT / o)
    return out


# ---------------------------------------------------------------------------
# Overlay string walking
# ---------------------------------------------------------------------------
SKIP_KEYS = {"status"}
LOCAL_ROLES = {"title", "gloss", "note", "example_gloss", "correct_option", "distractor",
               "accepted", "accepted_note", "accepted_word", "pair_right", "pair_left", "description"}
GLOBAL_ROLES = {"instruction", "feedback", "course_title", "course_description"}
ALWAYS_LEARNER = {"gloss", "note", "example_gloss", "instruction", "feedback", "pair_right", "accepted_note",
                  "course_title", "course_description"}
OPTION_ROLES = {"correct_option", "distractor", "accepted", "pair_right"}
ALWAYS_ENGLISH = {"pair_left", "accepted_word"}
AMBIGUOUS = {"correct_option", "distractor", "accepted"}
_EN_VOCAB: set | None = None
CORE_EN = set("a an the i you he she it we they me my your his her its our their this that these those is are am was were be been do does did have has had will would can could should may might must not no yes and or but if then so to of in on at by for with from as about into up out down over under more most very too also just only here there what which who when where why how all any some one two".split())


def english_vocab() -> set:
    global _EN_VOCAB
    if _EN_VOCAB is None:
        v = set(CORE_EN)
        for p in (CONTENT / "realizations" / "en").glob("*.yaml"):
            for _, t in walk_strings(load(p)):
                v.update(re.findall(r"[a-z]+(?:'[a-z]+)?", t.lower()))
        _EN_VOCAB = v
    return _EN_VOCAB


def english_fraction(s: str) -> float:
    toks = re.findall(r"[^\W\d_]+(?:'[^\W\d_]+)?", s.lower())
    return sum(t in english_vocab() for t in toks) / len(toks) if toks else 0.0


def walk_strings(node, path=()):
    """Yield (path, value) for every string leaf; path elements are keys/indexes."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_strings(v, path + (i,))
    elif isinstance(node, str):
        yield path, node


def overlay_role(path: tuple) -> str | None:
    """Role of a string leaf in an overlay (None = structural, not translatable)."""
    sec = path[0]
    if sec in ("schema_version", "overlay_version", "overlay_key", "source_language", "target_language",
               "status", "generation_provenance", "review"):
        return None
    if path[-1] in SKIP_KEYS:
        return None
    if sec == "course":
        return "course_" + path[1]
    if sec in ("units", "lessons"):
        return "title"
    if sec == "teaching":
        return path[2]
    if sec == "exercises":
        f = path[2]
        if f in ("instruction", "feedback", "correct_option"):
            return f
        if f == "distractors":
            return "distractor"
        if f == "pairs":
            return "pair_right" if path[-1] == "right" else "pair_left"
        if f == "accepted_answers":
            if path[-1] == "note":
                return "accepted_note"
            if len(path) > 4 and path[3] == "value":
                if path[-1] == "right":
                    return "pair_right"
                if path[-1] == "left":
                    return "pair_left"
                return "accepted_word"
            return "accepted"
        return f
    return None


ASTERISK = re.compile(r"\*([^*]+)\*")
PLACEHOLDER = re.compile(r"\{[a-z_0-9]+\}")


def _norm_title(s: str) -> str:
    return re.sub(r"[\W_]+", " ", s.lower()).strip()


def teaching_title_is_english(title: str, target: str = "") -> bool:
    """Is a teaching-card title English target text (keep) or a learner-language description (translate)?

    In the de-en source a card title is EITHER the English target text itself (vocabulary / phrase
    cards: "Hello", "Good morning", grammar labels like "prefer X to Y") OR a German description
    of the card ("Daniel fragt nach dem Namen", "Preisschild", "Sagen, wie oft man etwas einnimmt").
    The source never marks which, so decide on content: it is target text when it equals the
    card's English target text (case/punctuation-insensitive) or is (almost) entirely English
    vocabulary; otherwise it is a learner-language description and must be translated.
    """
    if not has_words(title):
        return True
    if target and _norm_title(title) == _norm_title(target):
        return True
    return english_fraction(title) >= 0.9


def has_words(s: str) -> bool:
    return bool(re.search(r"[^\W\d_]", PLACEHOLDER.sub("", s)))


def contrast_hint(src_code: str, text: str) -> bool:
    names = {"nl": r"Nederland|Dutch|Hollands", "de": r"Deutsch|German|Duits", "fa": r"فارسی", "prs": r"دری",
             "es": r"Espa[nñ]ol|Castellano|spanisch|Spanish", "fr": r"Fran[cç]ais|French", "it": r"Italian[oa]"}.get(src_code)
    return bool(names and re.search(names, text, re.I))


# ---------------------------------------------------------------------------
# Plan: occurrences -> flat items
# ---------------------------------------------------------------------------
class Occ:
    """One translatable place: setter(value) writes into the live YAML object."""

    def __init__(self, stem, scope, role, src, ctx, setter, kind):
        self.stem, self.scope, self.role, self.src, self.ctx = stem, scope, role, src, ctx
        self.setter, self.kind = setter, kind
        self.id: str | None = None


def container_set(container, key):
    def setter(v):
        container[key] = v
    return setter


def build_overlay_occs(unit: Unit, witnesses: dict[str, dict[str, Path]], src_code: str,
                       ridx: dict[str, dict], y: dict, stats: dict) -> list[Occ]:
    wit_docs = {s: load(p) for s, p in witnesses.get(unit.real_name, {}).items()}
    # scope -> set of witness strings (per non-latin witness) and counts per latin one
    def wit_strings(section, key):
        res = {}
        for s, d in wit_docs.items():
            sub = (d.get(section) or {})
            node = sub.get(key) if isinstance(sub, dict) and section != "course" else sub
            res[s] = {v for _, v in walk_strings(node)} if node is not None else set()
        return res

    occs: list[Occ] = []
    leaves = []
    for path, val in walk_strings(y):
        role = overlay_role(path)
        if role is None or not val.strip():
            continue
        stats["strings_total"] += 1
        leaves.append((path, val, role))

    doc_sets = {s_: {v for _, v in walk_strings({k: v for k, v in d.items() if k not in ("review", "generation_provenance")})}
                for s_, d in wit_docs.items()}

    def witness_english(path, val):
        # strongest evidence: the same string occurs in the same unit of a non-Latin-script sibling
        if any(val in doc_sets[s_] for s_ in doc_sets if s_ in NON_LATIN):
            return True
        section = path[0]
        key = path[1] if section != "course" else None
        ws = wit_strings(section, key)
        return sum(1 for s_ in ws if s_ not in NON_LATIN and val in ws[s_]) >= 2

    # ambiguous roles (options/answers) are English or learner-language per exercise: majority vote
    votes: dict[tuple, list[bool]] = defaultdict(list)
    for path, val, role in leaves:
        if role in AMBIGUOUS:
            if not witness_english(path, val):
                votes[path[:2]].append(english_fraction(val) >= 0.9)
    ex_is_english = {k: sum(v) * 2 > len(v) for k, v in votes.items()}

    for path, val, role in leaves:
        section = path[0]
        key = path[1] if section != "course" else None
        scope = (section, key)
        if section == "teaching" and role == "title":
            english = teaching_title_is_english(val, ridx.get(key or "", {}).get("target", ""))
        elif role in ALWAYS_ENGLISH or not has_words(val):
            english = True
        elif role in ALWAYS_LEARNER:
            english = False
        elif role in AMBIGUOUS:
            english = witness_english(path, val) or (ex_is_english.get(path[:2], False) and english_fraction(val) >= 0.6)
        else:  # unit / lesson titles
            english = False
        if english:
            stats["strings_invariant"] += 1
            continue
        info = ridx.get(key or "", {})
        if section == "exercises":
            ctx = f"{info.get('type', '?')} | tested: {info.get('tested', '')} | prompt: {info.get('prompt', '') or '-'}"
        elif section == "teaching":
            ctx = f"{info.get('kind', 'card')} | English: {info.get('target', '')}" + (
                f" | English example: {info['example']}" if info.get("example") else "")
        else:
            ctx = ""
        parent = y
        for p_ in path[:-1]:
            parent = parent[p_]
        o = Occ(unit.stem, scope, role, val, ctx, container_set(parent, path[-1]), "ov")
        o.contrastive = contrast_hint(src_code, val)  # type: ignore[attr-defined]
        occs.append(o)
    return occs


def build_pack_occs(unit: Unit, src_code: str, y: dict, stats: dict) -> list[Occ]:
    occs: list[Occ] = []
    seen_dicts: set[int] = set()

    def walk(node, tpl):
        if isinstance(node, dict):
            if node.get("language_code") == src_code and isinstance(node.get("text"), str) and id(node) not in seen_dicts:
                seen_dicts.add(id(node))
                txt = node["text"]
                slots = ", ".join(sorted(tpl.get("slots", {}))) if isinstance(tpl, dict) else ""
                ctx = f"pack {tpl.get('type', '?') if isinstance(tpl, dict) else '?'} | slots: {slots}"
                o = Occ(unit.stem, ("pack",), "packtext", txt, ctx, container_set(node, "text"), "pk")
                o.node = node  # type: ignore[attr-defined]
                o.translatable = has_words(txt)  # type: ignore[attr-defined]
                occs.append(o)
                stats["pack_strings_total"] += 1
                if not o.translatable:
                    stats["pack_strings_invariant"] += 1
                return
            for v in node.values():
                walk(v, tpl)
        elif isinstance(node, list):
            for v in node:
                walk(v, tpl)

    for t in y.get("templates", []):
        walk(t, t)
    return occs


def assign_ids(all_occs: list[Occ]) -> tuple[dict[str, list[Occ]], list[tuple[str, str, str, list[str]]]]:
    """Group occurrences into flat items. Returns (items_by_file, shared) with ids set on occs."""
    # global candidates: instruction/feedback/pack text appearing in >=2 stems
    stems_of: dict[tuple, set] = defaultdict(set)
    for o in all_occs:
        if o.role in GLOBAL_ROLES or o.kind == "pk":
            stems_of[(o.kind, o.role, o.src)].add(o.stem)
    groups: "OrderedDict[tuple, list[Occ]]" = OrderedDict()
    for o in all_occs:
        if o.kind == "pk" and not o.translatable:  # type: ignore[attr-defined]
            continue
        gk = (o.kind, o.role, o.src)
        if (o.role in GLOBAL_ROLES or o.kind == "pk") and len(stems_of[gk]) >= 2:
            key = ("shared",) + gk
        elif o.role in GLOBAL_ROLES or o.kind == "pk":
            key = (o.stem, o.kind, o.role, o.src, o.scope)
        elif o.role in OPTION_ROLES:
            # options, answers and pair clues of one exercise must agree: one id per distinct string
            key = (o.stem, o.kind, "option", o.src, o.scope)
        else:
            key = (o.stem, o.kind, o.role, o.src, o.scope)
        groups.setdefault(key, []).append(o)
    counters: dict[str, int] = defaultdict(int)
    by_file: dict[str, list] = defaultdict(list)
    for key, occs in groups.items():
        fname = "shared" if key[0] == "shared" else occs[0].stem
        counters[fname] += 1
        pre = "s" if fname == "shared" else "u"
        gid = f"{pre}{counters[fname]}"
        for o in occs:
            o.id = gid
        by_file[fname].append((gid, occs))
    return by_file, groups


# ---------------------------------------------------------------------------
# Glosses (backfill dictionary)
# ---------------------------------------------------------------------------
def load_backfill_module(pair: str):
    src, tgt = pair.split("-")
    path = ROOT / f"scripts/backfill_lexemes_{src}_{tgt}.py"
    if not path.exists():
        return None, path
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(f"_bf_{src}_{tgt}", path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod, path


def gloss_dicts(mod, levels=None) -> "OrderedDict[str, dict[str, str]]":
    """Module-level str->str gloss dicts keyed by canonical (first) name, de-duplicated by identity."""
    seen: dict[int, str] = {}
    out: "OrderedDict[str, dict[str, str]]" = OrderedDict()
    for name, val in vars(mod).items():
        if not isinstance(val, dict) or name.startswith("_") or name in ("GLOSSES_BY_LEVEL", "CATEGORY_TAGS", "EN_POS"):
            continue
        if not re.search(r"GLOSS|SENSE_FIXES|OVERRIDES", name):
            continue
        m = re.match(r"([AB][12]|C1)_", name)
        if levels is not None and m and m.group(1).lower() not in levels:
            continue
        if not val or not all(isinstance(k, str) and isinstance(v, str) for k, v in val.items()):
            continue
        if id(val) in seen:
            continue
        seen[id(val)] = name
        out[name] = val
    return out


# ---------------------------------------------------------------------------
# JSON output (one item per line, readable and diffable)
# ---------------------------------------------------------------------------
def write_src(path: Path, header: dict, items: list) -> None:
    lines = ["{"]
    for k, v in header.items():
        lines.append(f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)},")
    lines.append('  "items": [')
    body = []
    for it in items:
        body.append("    " + json.dumps(it, ensure_ascii=False))
    lines.append(",\n".join(body))
    lines.append("  ]")
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def guide_text(sib_code: str, new_code: str, target: str) -> str:
    n_en, _, n_notes = LANG.get(new_code, (new_code, new_code, ""))
    s_en = lang_name(sib_code)
    rtl = new_code in RTL
    return f"""# Translator guide: {s_en} -> {n_en} (learner language {new_code}, target {target})

You translate flat item files, not YAML. For every `NAME.src.json` write `NAME.tr.json`:
a JSON object {{"u1": "<translation>", ...}} with one entry per id (ids in `items`).
Output ONLY the translations; do not repeat the source. Header rows `["#", ...]` are context, not items.

Item format: `[id, role, source-text]`. The source is the {s_en} text of the sibling course
that teaches {lang_name(target)} to {s_en} speakers. Write what a careful native {n_en} teacher would write for
a {n_en}-speaking learner of {lang_name(target)}. Do NOT translate word-for-word; where the source makes a
contrastive remark about {s_en} (flagged `CONTRAST`), rewrite it as a true remark about {n_en}, or give a neutral
explanation when {n_en} has no useful parallel. Never mention {s_en} in the result.

Register: {n_notes or 'match the sibling register for the learner'}.

Rules (these are checked by `inject`):
1. Keep every `{{placeholder}}` byte-for-byte (pack texts). They are replaced at runtime with an English word or its {n_en} gloss, so a frame must stay grammatical for ANY word of the pool (avoid articles/gender/case agreement that depends on the slot).
2. Keep `*asterisk*` spans around target-language ({lang_name(target)}) words in notes and feedback. The English inside spans stays English; add spans around English words you introduce.
3. Roles: `gloss` = the shortest natural {n_en} equivalent of the English card (never contains the English word). `correct_option` / `distractor` / `accepted` / `pair_right` = {n_en} meaning strings; the options of one exercise must stay mutually distinct and the distractors must stay clearly wrong. `accepted_note` = short remark on an alternative English answer.
4. An `instruction` must still ask for exactly what the exercise tests (see the context row: type, tested English, prompt).
5. Do not reveal the English answer inside an `instruction` (it must not contain the answer words).
6. Learner-facing text only: no authoring jargon, no ids, no notes to the reviewer.
{"7. RTL language: write normal logical-order text; do not insert bidi control characters. English words inside the sentence stay in Latin script." if rtl else ""}
{"8. Dari (prs) vs Farsi (fa): never copy Iranian-only lexis into Dari; the Dari register checker must report 0 findings." if new_code in ("fa", "prs") else ""}
"""


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------
def collect(args):
    sib_src, target = args.sibling.split("-")
    units = find_units(args.sibling, args.levels, args.units)
    wit = witness_map(target, {sib_src, args.new.split("-")[0]})
    stats: dict = defaultdict(int)
    all_occs: list[Occ] = []
    docs: dict[str, tuple[dict, dict | None, Unit]] = {}
    for u in units:
        y = load(u.overlay)
        ridx = realization_index(u.realization)
        occs = build_overlay_occs(u, wit, sib_src, ridx, y, stats)
        py = None
        if u.pack and u.pack.exists():
            py = load(u.pack)
            occs += build_pack_occs(u, sib_src, py, stats)
        all_occs += occs
        docs[u.stem] = (y, py, u)
        stats["units"] += 1
    by_file, groups = assign_ids(all_occs)
    return units, docs, all_occs, by_file, groups, stats


def cmd_extract(args):
    sib_src, target = args.sibling.split("-")
    new_src = args.new.split("-")[0]
    work = Path(args.work) / args.new
    work.mkdir(parents=True, exist_ok=True)
    units, docs, all_occs, by_file, groups, stats = collect(args)
    (work / "GUIDE.md").write_text(guide_text(sib_src, new_src, target), encoding="utf-8")

    carried = 0
    for fname, entries in by_file.items():
        # incremental re-extract: keep translations whose source text did not change
        old_src_p, old_tr_p = work / f"{fname}.src.json", work / f"{fname}.tr.json"
        carry: dict[str, str] = {}
        if old_src_p.exists() and old_tr_p.exists():
            old_tr = load_tr(work, fname)
            for it in json.loads(old_src_p.read_text(encoding="utf-8"))["items"]:
                if it[0] != "#" and it[0] in old_tr:
                    carry.setdefault(it[2], old_tr[it[0]])
        new_tr = {gid: carry[occs[0].src] for gid, occs in entries if occs[0].src in carry}
        if carry:
            old_tr_p.write_text(json.dumps(new_tr, ensure_ascii=False, indent=0), encoding="utf-8")
            carried += len(new_tr)
        items = []
        last_ctx = None
        for gid, occs in entries:
            o = occs[0]
            if o.ctx and o.ctx != last_ctx:
                items.append(["#", o.ctx])
                last_ctx = o.ctx
            role = o.role + (" CONTRAST" if getattr(o, "contrastive", False) else "")
            items.append([gid, role, o.src])
        write_src(work / f"{fname}.src.json",
                  {"direction": f"{args.sibling} -> {args.new}", "guide": "GUIDE.md"}, items)
        stats["items_sent"] += len(entries)
        stats["words_sent"] += sum(len(e[1][0].src.split()) for e in entries)

    # glosses
    mod, bpath = load_backfill_module(args.sibling)
    if mod is not None:
        gitems = []
        for name, d in gloss_dicts(mod, args.levels).items():
            gitems.append(["#", f"dict {name}"])
            for tok, gl in d.items():
                gitems.append([f"g{len(gitems)}", tok, gl])
        # ids must be stable: index by position within the file
        gitems = [it if it[0] == "#" else [f"g{i}", it[1], it[2]] for i, it in enumerate(gitems)]
        write_src(work / "glosses.src.json",
                  {"direction": f"{args.sibling} -> {args.new}",
                   "note": "[id, english-token, sibling-gloss]; write the "
                           f"{lang_name(new_src)} gloss of the English token (sense taught first). "
                           "Never include the English word in the gloss. Keep the sibling's disambiguation "
                           "style (formal/informal, sense in brackets)."}, gitems)
        stats["glosses"] = sum(1 for it in gitems if it[0] != "#")
    stats["translations_carried_over"] = carried
    json.dump(dict(stats), open(work / "stats.json", "w"), indent=1)
    print(f"extracted {stats['units']} units -> {work}")
    for k in ("strings_total", "strings_invariant", "pack_strings_total", "pack_strings_invariant",
              "items_sent", "words_sent", "glosses", "translations_carried_over"):
        print(f"  {k}: {stats.get(k, 0)}")


# ---------------------------------------------------------------------------
# inject
# ---------------------------------------------------------------------------
def load_tr(work: Path, name: str) -> dict[str, str]:
    p = work / f"{name}.tr.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    return d.get("translations", d) if isinstance(d, dict) else {}


def lint(role: str, src: str, tr: str) -> list[str]:
    problems = []
    if not tr.strip():
        problems.append("empty")
    if sorted(PLACEHOLDER.findall(src)) != sorted(PLACEHOLDER.findall(tr)):
        problems.append("placeholders differ")
    if tr.count("*") % 2:
        problems.append("odd number of asterisks")
    if "\n" in tr and "\n" not in src:
        problems.append("newline added")
    return problems


def cmd_inject(args):
    sib_src, target = args.sibling.split("-")
    new_src = args.new.split("-")[0]
    work = Path(args.work) / args.new
    units, docs, all_occs, by_file, groups, stats = collect(args)
    new_dir_dir = "rtl" if new_src in RTL else "ltr"
    problems: list[str] = []
    n_missing = 0

    # translations + drift check against the stored src files
    tr_by_file: dict[str, dict[str, str]] = {}
    for fname, entries in by_file.items():
        tr = load_tr(work, fname)
        tr_by_file[fname] = tr
        stored = json.loads((work / f"{fname}.src.json").read_text(encoding="utf-8"))
        stored_src = {it[0]: it[2] for it in stored["items"] if it[0] != "#"}
        for gid, occs in entries:
            if stored_src.get(gid) != occs[0].src:
                problems.append(f"{fname}:{gid} sibling text changed since extract; re-run extract")
            t = tr.get(gid)
            if t is None:
                n_missing += 1
                continue
            for pr in lint(occs[0].role, occs[0].src, t):
                problems.append(f"{fname}:{gid} [{occs[0].role}] {pr}: {t[:60]!r}")
    if n_missing and not args.allow_missing:
        problems.append(f"{n_missing} ids have no translation (use `status`)")
    if problems:
        print("\n".join(problems[:60]))
        if len(problems) > 60:
            print(f"... and {len(problems) - 60} more")
        if not args.force:
            sys.exit(f"inject aborted: {len(problems)} problem(s). Fix the .tr.json files (or --force).")

    for g in seed_content_manifests(args.sibling, args.new, args.levels):
        print(f"seeded scripts/manifest.d/content/{g}.txt from the sibling")
    if getattr(args, "no_backfill", False):
        print("note: --no-backfill, backfill script left untouched")
    else:
        write_backfill(args, work, units)
    tag_universe = new_direction_tags(args.new)
    dropped_templates = 0
    cm_new: "OrderedDict[str, tuple[list[str], list[str]]]" = OrderedDict()
    pack_paths: list[str] = []
    new_pair = args.new
    for u in units:
        y, py, _ = docs[u.stem]
        # apply translations
        for fname, entries in by_file.items():
            for gid, occs in entries:
                t = tr_by_file[fname].get(gid)
                if t is None:
                    continue
                for o in occs:
                    if o.stem == u.stem:
                        o.setter(t)
        for o in all_occs:
            if o.stem == u.stem and o.kind == "pk":
                o.node["language_code"] = new_src  # type: ignore[attr-defined]
                o.node["direction"] = new_dir_dir  # type: ignore[attr-defined]
        # overlay metadata
        if "overlay_key" in y:
            y["overlay_key"] = y["overlay_key"].replace(f"{args.sibling}.", f"{new_pair}.", 1)
        y["source_language"] = new_src
        y["overlay_version"] = "2026.1-draft.1"
        y["status"] = "complete_draft"
        y["generation_provenance"] = {"method": "ai_generated", "authoring_system": "derive_direction.py",
                                      "human_reviewed": False}
        y["review"] = {"status": "unreviewed", "required_next_reviewer": "native_speaker_review",
                       "notes": (f"Derived from {args.sibling} by scripts/derive_direction.py: structure, exercise "
                                 f"keys and English answer sets are shared with the sibling; every {lang_name(new_src)} "
                                 f"string was translated and adapted. Needs native {lang_name(new_src)} review "
                                 "(contrastive notes, register, distractor plausibility). NATIVE FLAGS: pending.")}
        out_ov = CONTENT / "overlays" / new_pair / f"{u.stem}.yaml"
        dump(y, out_ov)
        new_ov_rel = str(out_ov.relative_to(ROOT))
        g = group_names(new_pair, [u.level])[0]
        cm_new.setdefault(g, ([], []))
        cm_new[g][0].append(str(u.realization.relative_to(ROOT)))
        cm_new[g][1].append(new_ov_rel)
        if py is not None:
            if tag_universe is not None:
                kept = []
                for t in py.get("templates", []):
                    used: set = set()
                    _collect_semantic(t.get("slots", {}), used)
                    if all(x in tag_universe for x in used):
                        kept.append(t)
                dropped_templates += len(py.get("templates", [])) - len(kept)
                py["templates"] = kept
                sch = (py.get("tag_schema") or {}).get("agreement_tags", {})
                if isinstance(sch.get("semantic"), list):
                    sch["semantic"] = [x for x in sch["semantic"] if x in tag_universe]
            py["pack_key"] = py["pack_key"].replace(f".{args.sibling}.", f".{new_pair}.", 1)
            py["source_language"] = new_src
            for t in py.get("templates", []):
                t["content_key"] = t["content_key"].replace(f"practice.{args.sibling}.", f"practice.{new_pair}.", 1)
            py["review"] = {"status": "unreviewed", "required_next_reviewer": "native_speaker_review",
                            "fresh_context": "false",
                            "notes": (f"Derived from practice.{args.sibling} by scripts/derive_direction.py (templates, slots "
                                      f"and tags unchanged; frame/feedback text translated to {lang_name(new_src)}). "
                                      "Needs native review of frame grammar across the whole slot pool.")}
            out_pk = CONTENT / "practice" / new_pair / f"{u.stem}.yaml"
            dump(py, out_pk)
            pack_paths.append(str(out_pk.relative_to(ROOT)))

    update_manifests(cm_new, new_pair, pack_paths)
    if dropped_templates:
        print(f"dropped {dropped_templates} pack templates that use sibling-specific lexeme tags (see docs/content/DIRECTION_PIPELINE.md)")
    print(f"injected {len(units)} overlays, {len(pack_paths)} packs for {new_pair}")


def _collect_semantic(o, acc: set) -> None:
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "semantic":
                acc.update([v] if isinstance(v, str) else v)
            else:
                _collect_semantic(v, acc)
    elif isinstance(o, list):
        for v in o:
            _collect_semantic(v, acc)


def new_direction_tags(pair: str) -> set | None:
    """Semantic tags the new direction's backfill will create (None if it has no backfill)."""
    try:
        mod, _ = load_backfill_module(pair)
        if mod is None or not hasattr(mod, "iter_specs"):
            return None
        specs = list(mod.iter_specs())
    except SystemExit:
        # first inject of a new pair: its manifest group files do not exist yet (written at the end of inject);
        # re-running inject afterwards applies the tag filter.
        return None
    tags: set = set()
    for spec in specs:
        tags.update(spec["agreement_tags"].get("semantic", []))
    return tags


def update_manifests(cm_new, new_pair, pack_paths):
    """Write one file per group/pack under scripts/manifest.d/ (no shared-file appends).

    Content group files are overwritten (one file per group). The practice file is shared by every
    level of the pair, so it is merged with what is already there: union of pack paths, sorted, no duplicates.
    """
    MANIFEST.mkdir(parents=True, exist_ok=True)
    for g, (reals, ovs) in cm_new.items():
        dest_g = MANIFEST / f"{g}.txt"
        pairs = list(zip(reals, ovs))
        if dest_g.exists():
            # incremental inject (--units): keep the units already listed, add/replace the injected ones,
            # and order by unit number so realizations and overlays stay position-matched.
            old_parts = read_manifest_file(dest_g).get(g)
            if old_parts and len(old_parts) == 2 and len(old_parts[0]) == len(old_parts[1]):
                have = {r for r, _ in pairs}
                pairs = [pr for pr in zip(*old_parts) if pr[0] not in have] + pairs
                num = lambda pr: int(re.search(r"unit(\d+)", pr[0]).group(1)) if re.search(r"unit(\d+)", pr[0]) else 0
                pairs.sort(key=num)
        dest_g.write_text(f"{g}|{' '.join(r for r, _ in pairs)}|{' '.join(o for _, o in pairs)}\n", encoding="utf-8")
    if pack_paths:
        PRACTICE_MANIFEST.mkdir(parents=True, exist_ok=True)
        dest = PRACTICE_MANIFEST / f"{new_pair}.txt"
        existing: list[str] = []
        if dest.exists():
            existing = [p for parts in read_manifest_file(dest).get(new_pair, []) for p in parts]
        merged = sorted(set(existing) | set(pack_paths))
        dest.write_text(f"{new_pair}|{' '.join(merged)}\n", encoding="utf-8")


def read_manifest_file(path: Path) -> "OrderedDict[str, list[list[str]]]":
    out: "OrderedDict[str, list[list[str]]]" = OrderedDict()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#") or "|" not in line:
            continue
        parts = line.split("|")
        out[parts[0]] = [p.split() for p in parts[1:]]
    return out


def seed_content_manifests(sibling: str, new_pair: str, levels: list[str]) -> list[str]:
    """Create scripts/manifest.d/content/<new>-<level>.txt from the sibling's file when missing.

    The generated backfill imports these groups, so they must exist before inject loads it. The seeded line
    points at the sibling's realizations and overlays; update_manifests overwrites it with the real one.
    """
    created: list[str] = []
    MANIFEST.mkdir(parents=True, exist_ok=True)
    for sib_g, new_g in zip(group_names(sibling, levels), group_names(new_pair, levels)):
        dest = MANIFEST / f"{new_g}.txt"
        src = MANIFEST / f"{sib_g}.txt"
        if dest.exists() or not src.exists():
            continue
        text = src.read_text(encoding="utf-8")
        lines = [l for l in text.splitlines() if l.startswith(f"{sib_g}|")]
        if not lines:
            continue
        dest.write_text(f"{new_g}|" + lines[0].split("|", 1)[1] + "\n", encoding="utf-8")
        created.append(new_g)
    return created


def py_dict_literal(d: dict[str, str]) -> str:
    lines = ["{"]
    for k, v in d.items():
        lines.append(f"    {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)},")
    lines.append("}")
    return "\n".join(lines)


def _top_assign(node):
    """(name, value node) of a module-level simple assignment, else (None, None)."""
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id, node.value
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
        return node.target.id, node.value
    return None, None


def _existing_levels(text: str) -> list[str]:
    for node in ast.parse(text).body:
        name, val = _top_assign(node)
        if name == "LEVELS" and isinstance(val, ast.Dict):
            return [k.value for k in val.keys if isinstance(k, ast.Constant)]
    return []


def _gloss_level(name: str) -> str:
    """Level a gloss dict belongs to: A2_/B1_ prefix, otherwise the A1 base table."""
    m = re.match(r"([AB][12]|C1)_", name)
    return m.group(1).lower() if m else "a1"


def merge_backfill(generated: str, existing: str, injected: set) -> str:
    """Keep every level of the existing backfill that is not being injected.

    Gloss dicts of non-injected levels and the LEVELS / GLOSSES_BY_LEVEL entries of non-injected levels are taken
    verbatim from the existing file (hand edits survive); injected levels come from the generated text.
    """
    ex_src = {}
    for node in ast.parse(existing).body:
        name, val = _top_assign(node)
        if name and isinstance(val, ast.Dict):
            ex_src[name] = (node, val)
    gen_lines = generated.split("\n")
    ex_lines = existing.split("\n")
    repl: list[tuple[int, int, str]] = []
    for node in ast.parse(generated).body:
        name, val = _top_assign(node)
        if not name or not isinstance(val, ast.Dict) or name not in ex_src:
            continue
        ex_node, ex_val = ex_src[name]
        if name in ("LEVELS", "GLOSSES_BY_LEVEL"):
            ex_items = {k.value: ast.get_source_segment(existing, v) for k, v in zip(ex_val.keys, ex_val.values)
                        if isinstance(k, ast.Constant)}
            parts = []
            for k, v in zip(val.keys, val.values):
                key = k.value  # type: ignore[union-attr]
                seg = ex_items[key] if key not in injected and key in ex_items else ast.get_source_segment(generated, v)
                parts.append(f"{json.dumps(key)}: {seg}")
            first = gen_lines[node.lineno - 1]
            repl.append((node.lineno - 1, node.end_lineno, first.split("=", 1)[0] + "= {" + ", ".join(parts) + "}"))
        elif re.search(r"GLOSS|SENSE_FIXES|OVERRIDES", name) and not name.startswith("_") \
                and _gloss_level(name) not in injected:
            repl.append((node.lineno - 1, node.end_lineno, "\n".join(ex_lines[ex_node.lineno - 1:ex_node.end_lineno])))
    for start, end, text in sorted(repl, reverse=True):
        gen_lines[start:end] = text.split("\n")
    return "\n".join(gen_lines)


def write_backfill(args, work: Path, units: list[Unit]) -> None:
    """Clone the sibling's backfill script, replacing its gloss dicts with the translated ones."""
    mod, bpath = load_backfill_module(args.sibling)
    if mod is None:
        print(f"note: no {bpath.name}; backfill stub skipped")
        return
    sib_src, target = args.sibling.split("-")
    new_src = args.new.split("-")[0]
    gsrc = json.loads((work / "glosses.src.json").read_text(encoding="utf-8"))
    tr = load_tr(work, "glosses")
    # rebuild per-dict translated literals
    cur = None
    new_dicts: dict[str, dict[str, str]] = {}
    for it in gsrc["items"]:
        if it[0] == "#":
            cur = it[1].split()[1]
            new_dicts[cur] = {}
            continue
        gid, tok, _ = it
        if gid not in tr:
            if not args.allow_missing:
                sys.exit(f"gloss {gid} ({tok}) has no translation")
            continue
        new_dicts[cur][tok] = tr[gid]
    source = bpath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.split("\n")
    repl: list[tuple[int, int, str]] = []
    aliases: dict[str, str] = {}
    all_gloss = set(gloss_dicts(mod))
    dest = ROOT / f"scripts/backfill_lexemes_{new_src}_{target}.py"
    existing = dest.read_text(encoding="utf-8") if dest.exists() else None
    injected = set(args.levels)
    keep_levels = set(injected)
    if existing is not None:
        keep_levels |= set(_existing_levels(existing))
    for node in tree.body:
        tname = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            tname = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            tname = node.target.id
        if tname is not None:
            name = tname
            if name in ("LEVELS", "GLOSSES_BY_LEVEL") and isinstance(node.value, ast.Dict):
                parts = []
                for k, v in zip(node.value.keys, node.value.values):
                    if isinstance(k, ast.Constant) and k.value in keep_levels:
                        parts.append(f"{ast.get_source_segment(source, k)}: {ast.get_source_segment(source, v)}")
                first = lines[node.lineno - 1]
                repl.append((node.lineno - 1, node.end_lineno, first.split("=", 1)[0] + "= {" + ", ".join(parts) + "}"))
            elif name in all_gloss and name not in new_dicts and isinstance(node.value, ast.Dict):
                first = lines[node.lineno - 1]
                repl.append((node.lineno - 1, node.end_lineno,
                             first.split("=", 1)[0] + "= {}  # level not derived yet"))
            elif name in new_dicts and isinstance(node.value, ast.Dict):
                body = py_dict_literal(new_dicts[name])
                first = lines[node.lineno - 1]
                prefix = first.split("=", 1)[0] + "= "
                repl.append((node.lineno - 1, node.end_lineno, prefix + body))
            elif isinstance(node.value, ast.Name) and node.value.id in new_dicts:
                aliases[name] = node.value.id
    for start, end, text in sorted(repl, reverse=True):
        lines[start:end] = text.split("\n")
    out = "\n".join(lines)
    S, N = sib_src.upper(), new_src.upper()
    out = out.replace(f"_{sib_src}_{target}", f"_{new_src}_{target}")
    out = out.replace(f"{sib_src}-{target}", f"{new_src}-{target}")
    out = out.replace(f"TO_{S}_GLOSS", f"TO_{N}_GLOSS")
    out = out.replace(f'source_language="{sib_src}"', f'source_language="{new_src}"')
    out = out.replace(lang_name(sib_src), lang_name(new_src))
    doc_levels = sorted(keep_levels)
    out = re.sub(r'^(#![^\n]*\n)""".*?"""', lambda m_: m_.group(1) + _docstring(args, doc_levels, new_src, target), out, count=1, flags=re.S)
    if existing is not None:
        out = merge_backfill(out, existing, injected)
    dest.write_text(out, encoding="utf-8")
    dest.chmod(0o755)
    print(f"wrote {dest.relative_to(ROOT)} ({sum(len(d) for d in new_dicts.values())} glosses)")


def _docstring(args, levels, new_src, target) -> str:
    lv = ", ".join(levels)
    return f'''"""Idempotently backfill {args.new} ({lang_name(target)} target, {lang_name(new_src)} source) lexemes.

Generated by scripts/derive_direction.py from scripts/backfill_lexemes_{args.sibling.replace("-", "_")}.py
(levels {lv}).  Plumbing lives in scripts/_target_lexeme_backfill_common.py; this
file is data only.  The English classification is shared; every gloss below is
the {lang_name(new_src)} meaning of the English token (it is the answer text of
multiple_choice and the prompt of translation exercises) and must never contain
the English answer word.

Run (after the {args.new} course is imported), from backend/:

    docker compose run --rm -v "$(cd .. && pwd):/repo" -e PYTHONPATH=/repo/backend \\
      --entrypoint python api /repo/scripts/backfill_lexemes_{new_src}_{target}.py

Add --dry-run to classify without touching the database.
"""'''


# ---------------------------------------------------------------------------
# status / validate
# ---------------------------------------------------------------------------
def cmd_status(args):
    work = Path(args.work) / args.new
    total = missing = 0
    for src in sorted(work.glob("*.src.json")):
        name = src.name[: -len(".src.json")]
        ids = [it[0] for it in json.loads(src.read_text(encoding="utf-8"))["items"] if it[0] != "#"]
        tr = load_tr(work, name)
        m = [i for i in ids if i not in tr]
        total += len(ids)
        missing += len(m)
        print(f"{name:14s} {len(ids) - len(m):4d}/{len(ids):4d}" + ("" if not m else f"   missing: {', '.join(m[:6])}..."))
    print(f"TOTAL {total - missing}/{total}")


def run(cmd: list[str], log: list[str]) -> int:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    log.append(out)
    return r.returncode


def cmd_validate(args):
    py = str(ROOT / ".content-venv/bin/python")
    if not Path(py).exists():
        py = sys.executable
    cm = read_manifest(MANIFEST)
    pm = read_manifest(PRACTICE_MANIFEST)
    fails = 0
    for g in group_names(args.new, args.levels):
        reals, ovs = cm[g]
        for mode, extra in (("validate", []), ("compile", ["--out", f"/tmp/derive_{g}.json"])):
            log: list[str] = []
            rc = run([py, "scripts/compile_content.py", mode, "--realization", *reals, "--overlay", *ovs, *extra], log)
            tail = log[-1].splitlines()[-1] if log and log[-1] else ""
            print(f"{mode:9s} {g}: rc={rc} {tail}")
            fails += rc != 0
    if args.new in pm:
        log = []
        rc = run([py, "scripts/compile_content.py", "practice-validate", "--pack", *pm[args.new][0],
                  "--content-root", "docs/content/realizations"], log)
        print(f"practice-validate {args.new}: rc={rc} {log[-1].splitlines()[-1] if log[-1] else ''}")
        fails += rc != 0
    for script, label in (("_answer_leakage_check.py", "leakage"), ("_practice_self_reference_check.py", "self-reference"),
                          ("_practice_slot_check.py", "slot"), ("_practice_unit_scope_check.py", "unit-scope"),
                          ("_fill_in_blank_ambiguity_check.py", "fill-ambiguity"),
                          ("_practice_content_integrity_check.py", "integrity")):
        log = []
        run([py, f"scripts/{script}"], log)
        lines = [l for l in log[-1].splitlines() if args.new in l or re.search(r"\b(hit|flag|DEAD|AMBIG|scanned)", l)]
        print(f"{label:15s} " + " | ".join(lines[-3:])[:200])
    if args.new.split("-")[0] in ("prs", "fa"):
        log = []
        run([py, "scripts/check_dari_register.py"], log)
        print("dari            " + " | ".join(log[-1].splitlines()[-2:]))
    # leftover scan: sibling-language residue / unchanged strings
    left = leftover_scan(args)
    print(f"leftover-scan   {left} suspicious string(s)")
    # German residue in a non-de learner-language overlay/pack (e.g. untranslated card titles)
    sys.path.insert(0, str(ROOT / "scripts"))
    import _german_leftover_check as glc
    german = glc.scan_pair(args.new) if args.new.split("-")[0] != "de" else []
    for h in german[:50]:
        print("  " + h)
    print(f"german-leftover {len(german)} string(s)")
    sys.exit(1 if fails or german else 0)


def leftover_scan(args) -> int:
    """Count new-direction strings that still look like the sibling language."""
    if not args.sibling:
        return 0
    sib_src = args.sibling.split("-")[0]
    new_dir = CONTENT / "overlays" / args.new
    n = 0
    for p in sorted(new_dir.glob("*.yaml")):
        for path, v in walk_strings(load(p)):
            if overlay_role(path) and contrast_hint(sib_src, v):
                n += 1
                print(f"  {p.name}: {'/'.join(map(str, path))[:70]}: {v[:80]!r}")
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("extract", cmd_extract), ("inject", cmd_inject), ("status", cmd_status), ("validate", cmd_validate)):
        sp = sub.add_parser(name)
        sp.add_argument("--sibling", help="existing direction Y-T to derive from, e.g. de-en")
        sp.add_argument("--new", required=True, help="new direction X-T, e.g. es-en")
        sp.add_argument("--levels", default="a1", type=lambda s: s.split(","))
        sp.add_argument("--units", type=lambda s: s.split(","), help="only these unit stems, e.g. a1_unit01,a1_unit02")
        sp.add_argument("--work", default=str(DEFAULT_WORK))
        if name == "inject":
            sp.add_argument("--allow-missing", action="store_true")
            sp.add_argument("--force", action="store_true")
            sp.add_argument("--no-backfill", action="store_true",
                            help="do not (re)write scripts/backfill_lexemes_<x>_<t>.py (hand-maintained glosses)")
        sp.set_defaults(fn=fn)
    args = ap.parse_args()
    if args.cmd in ("extract", "inject") and not args.sibling:
        ap.error("--sibling is required")
    args.fn(args)


if __name__ == "__main__":
    main()
