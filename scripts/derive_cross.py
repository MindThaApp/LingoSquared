#!/usr/bin/env python3
"""Derive a cross-language direction X->Y (neither side English) from the English-source course en->Y.

A direction = shared target realizations (reused untouched) + overlay per unit + practice pack per unit + lexeme
glosses + manifest lines.  For X->Y only the learner-language strings differ from en->Y, so the job is a flat
translation of the English learner-language strings of the en->Y overlays and packs into X; the target-language
text (French/German/... options, answers, quoted words) is kept byte for byte.

This is the target-side mirror of scripts/derive_direction.py (which keeps the target and swaps the sibling's
learner language).  It reuses that tool's extract/inject machinery and changes only what is language-direction
specific:

    extract   en-Y overlays/packs/glosses -> flat *.src.json files (+ GUIDE.md) in .local/derive-cross/X-Y/
              (translate: write NAME.tr.json next to each NAME.src.json, by hand, by agents, or `translate`)
    translate call the Gemini API for the missing ids (key from $GEMINI_API_KEY or secrets/gemini/api-key.txt)
    status    coverage per file
    inject    overlays, packs, manifest lines, lexicon (docs/content/lexicon/X-Y.json) + backfill shim
    validate  compiler, practice-validate, leakage gates, English-leftover scan

    python3 scripts/derive_cross.py extract  --new es-fr --levels a1
    python3 scripts/derive_cross.py translate --new es-fr          # or fill the *.tr.json files otherwise
    python3 scripts/derive_cross.py inject   --new es-fr --levels a1
    python3 scripts/derive_cross.py validate --new es-fr --levels a1

The sibling is always en-Y.  Lexeme glosses are not cloned into a new backfill script: the shim
scripts/backfill_lexemes_X_Y.py reuses the en-Y classification (tokens, parts of speech, tags) through
scripts/_cross_lexeme_backfill.py and takes only the gloss text from docs/content/lexicon/X-Y.json.
See docs/content/DIRECTION_PIPELINE.md ("Cross pairs").
"""
from __future__ import annotations

import argparse
import functools
import importlib
import json
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive_direction as dd  # noqa: E402

ROOT, CONTENT = dd.ROOT, dd.CONTENT


def group_names(pair: str, levels: list[str]) -> list[str]:
    """Manifest group names; a target whose en-Y A1 group is called `en-Y-a1` (ar, it, ru) gets `X-Y-a1` too."""
    a1_suffix = (dd.MANIFEST / f"en-{pair.split('-')[1]}-a1.txt").exists()
    return [f"{pair}-{lv}" if (lv != "a1" or a1_suffix) else pair for lv in levels]


dd.group_names = group_names
WORK = ROOT / ".local/derive-cross"
LEXICON = CONTENT / "lexicon"

TOKEN = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", re.UNICODE)
# English words that also read as target-language words; never evidence for either side on their own.
STOP = set("a an the i you he she it we they me my your his her its our their this that these those is are am was were be been do does did have has had will would can could should may might must not no yes and or but if then so to of in on at by for with from as about into up out down over under more most very too also just only here there what which who when where why how all any some one two".split())
EN_ONLY = set("the is are was were you your this that these those with from and for to of it its not what which how why when where does did have has can will would should my his her our their they we she i'm don't it's isn't".split())
EN_STRONG = {"the", "is", "are", "this", "with", "your", "you", "what", "how"}


ALWAYS_LEARNER_CROSS = dd.ALWAYS_LEARNER | {"glosses", "title_unit", "correct_response_value"}
CONTRAST = re.compile(r"\b(English|English-speaking|in English|Spanish|German|Dutch|French|Italian)\b")


def norm_tokens(s: str) -> list[str]:
    return [t.lower().replace("’", "'") for t in TOKEN.findall(re.sub(r"\{[^}]*\}", " ", s))]


@functools.lru_cache(maxsize=None)
def node_tokens(real_path: Path) -> dict[str, frozenset]:
    """content_key -> every token of every string inside that realization node (target-language side)."""
    out: dict[str, frozenset] = {}

    target = dd.load(real_path).get("target_language", "")

    def strings(o):
        if isinstance(o, str):
            yield o
        elif isinstance(o, dict):
            if o.get("language_code") not in (None, target):
                return                                    # learner-language block inside the realization
            for k, v in o.items():
                if k not in ("content_key", "type", "lesson_content_key") and not (k == "right" and "left" in o):
                    yield from strings(v)
        elif isinstance(o, list):
            for v in o:
                yield from strings(v)

    def walk(o):
        if isinstance(o, dict):
            ck = o.get("content_key")
            if isinstance(ck, str):
                out[ck] = frozenset(t for s in strings(o) for t in norm_tokens(s))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(dd.load(real_path))
    return out


def en_fraction(s: str) -> float:
    toks = norm_tokens(s)
    if not toks:
        return 0.0
    vocab = dd.english_vocab()
    return sum(t in vocab for t in toks) / len(toks)


def is_target_text(val: str, key_tokens: frozenset) -> bool:
    """Is `val` text of the target language (keep) rather than learner-language English (translate)?"""
    toks = [t for t in norm_tokens(val)]
    if not toks:
        return True
    non_stop = [t for t in toks if t not in STOP or t in key_tokens]
    if toks and all(t in key_tokens for t in toks):
        # every token occurs in the realization node: target text, unless it is plain English prose
        return en_fraction(val) < 0.85 or len(toks) <= 2 or all(t in key_tokens for t in non_stop)
    hits = {t for t in toks if t in EN_ONLY and t not in key_tokens}      # English function words the node does not use
    if len(hits) >= 2 or hits & EN_STRONG:
        return False
    return en_fraction(val) < 0.5


def target_of(unit) -> str:
    return unit.real_name and dd.load(unit.realization).get("target_language", "")


@functools.lru_cache(maxsize=None)
def foreign_prompt_blocks(real_path: Path, target: str) -> dict[str, tuple]:
    """exercise content_key -> ((block index, text), ...) of realization prompt blocks that show learner-language text:
    blocks coded with another language (English), and target-coded blocks that end in an English hint."""
    out = {}
    for unit in dd.load(real_path).get("units", []):
        for lesson in unit.get("lessons", []):
            for ex in lesson.get("exercises", []):
                prompt = ex.get("prompt")
                blocks = prompt.get("target_blocks") if isinstance(prompt, dict) else None
                found = []
                for i, b in enumerate(blocks or []):
                    if not (isinstance(b, dict) and isinstance(b.get("text"), str) and b["text"].strip()):
                        continue
                    if b.get("language_code") not in (None, target) or (
                            english_prose(b["text"]) and re.search(r"\((the|a|an|to) [^)]*\)\s*$", b["text"])):
                        found.append((i, b["text"], b.get("language_code") not in (None, target)))
                if found:
                    out[ex["content_key"]] = tuple(found)
    return out


def build_cross_overlay_occs(unit, witnesses, src_code, ridx, y, stats):
    """Occurrences of English learner-language text in an en->Y overlay (Y-language text is invariant)."""
    ntok = node_tokens(unit.realization)
    leaves = []
    for path, val in dd.walk_strings(y):
        role = dd.overlay_role(path)
        if role is None and path[0] == "teaching" and len(path) > 2 and path[2] == "glosses":
            role = "glosses"
        if role is None or not val.strip():
            continue
        stats["strings_total"] += 1
        leaves.append((path, val, role))

    # exercise-level vote for short ambiguous option strings
    votes: dict[tuple, list[bool]] = defaultdict(list)
    for path, val, role in leaves:
        if role in dd.AMBIGUOUS:
            keyt = ntok.get(path[1], frozenset())
            votes[path[:2]].append(not is_target_text(val, keyt) and en_fraction(val) >= 0.8)
    ex_learner = {k: sum(v) * 2 > len(v) for k, v in votes.items()}

    occs = []
    for ck, found in foreign_prompt_blocks(unit.realization, target_of(unit)).items():
        ex = y.setdefault("exercises", {}).setdefault(ck, {})
        if all(f[2] for f in found):
            ex["prompt_blocks"] = [f[1] for f in found]                  # list form: every learner-language block, in order
            holder = [(ex["prompt_blocks"], i) for i in range(len(found))]
        else:
            ex["prompt_blocks"] = {str(f[0]): f[1] for f in found}      # index form: target-coded blocks with an English hint
            holder = [(ex["prompt_blocks"], str(f[0])) for f in found]
        info = ridx.get(ck, {})
        ctx = f"{info.get('type', '?')} | tested: {info.get('tested', '')} | prompt block shown to the learner (keep any target-language words)"
        for (container, k), f in zip(holder, found):
            stats["strings_total"] += 1
            o = dd.Occ(unit.stem, ("exercises", ck), "prompt_block", f[1], ctx, dd.container_set(container, k), "ov")
            o.contrastive = bool(CONTRAST.search(f[1]))  # type: ignore[attr-defined]
            occs.append(o)
    for path, val, role in leaves:
        section = path[0]
        key = path[1] if section != "course" else None
        keyt = ntok.get(key or "", frozenset())
        if not dd.has_words(val):
            learner = False
        elif section == "course":
            learner = True
        elif section in ("units", "lessons"):
            learner = True
        elif section == "teaching" and role == "title":
            learner = not is_target_text(val, keyt)
        elif role in ALWAYS_LEARNER_CROSS:
            learner = True
        elif role == "correct_response" and not isinstance(path[-1], str):
            learner = False                               # word-order tile lists are target text
        elif role == "correct_response":
            learner = not is_target_text(val, keyt)       # match values: learner meaning or target form (decide on text)
        elif role == "pair_left" or role == "accepted_word":
            learner = False
        elif role in dd.AMBIGUOUS:
            tgt = is_target_text(val, keyt)
            learner = (not tgt) or (ex_learner.get(path[:2], False) and en_fraction(val) >= 0.5 and tgt is False)
        else:
            learner = not is_target_text(val, keyt)       # unknown role: decide on the text
        if not learner:
            stats["strings_invariant"] += 1
            continue
        info = ridx.get(key or "", {})
        if section == "exercises":
            ctx = f"{info.get('type', '?')} | tested: {info.get('tested', '')} | prompt: {info.get('prompt', '') or '-'}"
        elif section == "teaching":
            ctx = f"{info.get('kind', 'card')} | target: {info.get('target', '')}" + (
                f" | target example: {info['example']}" if info.get("example") else "")
        else:
            ctx = ""
        parent = y
        for p_ in path[:-1]:
            parent = parent[p_]
        o = dd.Occ(unit.stem, (section, key), role, val, ctx, dd.container_set(parent, path[-1]), "ov")
        o.contrastive = bool(CONTRAST.search(val))  # type: ignore[attr-defined]
        occs.append(o)
    return occs


def cross_guide(sib_code: str, new_code: str, target: str) -> str:
    n_en, _, n_notes = dd.LANG.get(new_code, (new_code, new_code, ""))
    t_en = dd.lang_name(target)
    return f"""# Translator guide: English -> {n_en} (learner language {new_code}, target {target} = {t_en})

You translate flat item files, not YAML. For every `NAME.src.json` write `NAME.tr.json`:
a JSON object {{"u1": "<translation>", ...}} with one entry per id. Output ONLY the translations.
Item format: `[id, role, English text]`; `["#", context]` rows describe the exercise or card the following items belong to
(exercise type, tested {t_en} text, prompt). The English text belongs to a course that teaches {t_en} to English speakers.
Write what a careful native {n_en} teacher would write for a {n_en}-speaking learner of {t_en}.

Register: {n_notes or 'match the register of the learner-language text already used in the app'}.

Rules (checked by `inject`):
1. Keep every `{{placeholder}}` byte for byte (pack frames). Packs fill them at runtime with a {t_en} word or its {n_en} gloss, so
   a frame must stay grammatical for ANY word of the pool (no gender/article/case agreement that depends on the slot).
2. {t_en} words, phrases and sentences quoted inside an English text (inside `*asterisks*`, quotes or plain) stay EXACTLY as written,
   in the same script, including accents. Keep the `*asterisk*` spans (same number) around them.
3. Roles: `gloss` = shortest natural {n_en} equivalent of the {t_en} card (never contains the {t_en} word). `correct_option`,
   `distractor`, `accepted`, `pair_right` = {n_en} meaning strings; options of one exercise stay mutually distinct, wrong ones stay wrong.
   `instruction` asks for exactly what the exercise tests and must not reveal the answer. `feedback`/`note` explain the {t_en} point.
4. Contrast with English (flagged `CONTRAST`, or any remark about how English does it): the learner does not speak English. Rewrite it
   as a TRUE remark about {n_en} versus {t_en}, or state the {t_en} rule neutrally when {n_en} has no useful parallel. Never claim
   something false about {n_en}. Never mention English as the learner's language.
5. English example sentences translate into natural {n_en} (not word for word); keep names, numbers, times, prices as in the source
   unless the currency or unit is part of the {t_en} cultural setting (then keep it).
6. Learner-facing text only: no authoring jargon, no ids, no notes to the reviewer, no remark that the text was translated.
7. Course titles read like "<{t_en} in {n_en}> A1" in the {n_en} naming style of the other courses of the app.
{"8. RTL language: logical-order text, no bidi control characters; Latin-script target words stay in Latin script." if new_code in dd.RTL else ""}
"""


# ---------------------------------------------------------------------------
# lexicon (learner-language glosses of the target tokens)
# ---------------------------------------------------------------------------
def sibling_specs(target: str):
    sys.path.insert(0, str(ROOT / "scripts"))
    mod = importlib.import_module(f"backfill_lexemes_en_{target}")
    return list(mod.iter_specs())


def lexicon_items(target: str, levels: list[str]) -> list[list]:
    items, seen = [], set()
    for s in sibling_specs(target):
        if s["level"] not in levels or (s["level"], s["token"]) in seen:
            continue
        seen.add((s["level"], s["token"]))
        items.append([f"g{len(items) + 1}", f"{s['level']}|{s['token']}|{s['part_of_speech']}", s["english_gloss"]])
    return items


def cmd_extract(args):
    sib = args.sibling or f"en-{args.new.split('-')[1]}"
    args.sibling = sib
    target = args.new.split("-")[1]
    dd.build_overlay_occs = build_cross_overlay_occs
    dd.guide_text = cross_guide
    dd.load_backfill_module = lambda pair: (None, Path("-"))
    dd.cmd_extract(args)
    work = Path(args.work) / args.new
    print(f"  translation memory filled {tm_prefill(args)} item(s)")
    items = lexicon_items(target, args.levels)
    old = dd.load_tr(work, "glosses")
    old_src = work / "glosses.src.json"
    carry = {}
    if old_src.exists() and old:
        for it in json.loads(old_src.read_text(encoding="utf-8"))["items"]:
            if it[0] in old:
                carry[(it[1], it[2])] = old[it[0]]
    dd.write_src(work / "glosses.src.json", {"direction": f"{sib} -> {args.new}",
                 "note": "[id, level|token|pos, English gloss]: write the learner-language gloss of the target token "
                         "(sense taught first, same disambiguation style: formal/informal, masc./fem.). Never contain the target word."},
                 items)
    tr = {i[0]: carry[(i[1], i[2])] for i in items if (i[1], i[2]) in carry}
    if tr:
        (work / "glosses.tr.json").write_text(json.dumps(tr, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"  glosses: {len(items)} ({len(tr)} carried over)")


# ---------------------------------------------------------------------------
# lint (stricter than derive_direction.lint)
# ---------------------------------------------------------------------------
_BASE_LINT = dd.lint


def span_set(s: str) -> list[str]:
    return re.findall(r"\*([^*]+)\*", s)


def lint(role: str, src: str, tr: str, key_tokens: frozenset = frozenset()) -> list[str]:
    problems = _BASE_LINT(role, src, tr)
    if len(span_set(src)) != len(span_set(tr)):
        problems.append("asterisk span count differs")
    low = tr.lower().replace("’", "'")
    for sp in span_set(src):
        if en_fraction(sp) < 0.5 and sp.lower().replace("’", "'") not in low:
            problems.append(f"target span *{sp}* not kept verbatim")
    return problems


TM_DIR = CONTENT / "tm"
TM_ROLES = {"instruction", "feedback", "packtext", "title", "gloss", "example_gloss", "note", "distractor", "correct_option",
            "accepted", "correct_response", "pair_right", "accepted_note", "glosses", "prompt_block"}


def tm_path(learner: str) -> Path:
    return TM_DIR / f"{learner}.json"


def tm_load(learner: str) -> dict[str, str]:
    p = tm_path(learner)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def tm_key(role: str, src: str) -> str | None:
    base = role.split()[0]
    if base not in TM_ROLES or "CONTRAST" in role or "*" in src:
        return None                                   # contrast notes and target-word spans are target specific
    return f"{base}|{src}"


def tm_prefill(args) -> int:
    """Fill missing ids of the work dir from the learner-language translation memory (exact role + English text)."""
    work = Path(args.work) / args.new
    tm = tm_load(args.new.split("-")[0])
    n = 0
    for src in sorted(work.glob("*.src.json")):
        name = src.name[: -len(".src.json")]
        if name == "glosses":
            continue
        tr = dd.load_tr(work, name)
        added = 0
        for it in json.loads(src.read_text(encoding="utf-8"))["items"]:
            if it[0] == "#" or it[0] in tr:
                continue
            k = tm_key(it[1], it[2])
            if k and k in tm:
                tr[it[0]] = tm[k]
                added += 1
        if added:
            (work / f"{name}.tr.json").write_text(json.dumps(tr, ensure_ascii=False, indent=0), encoding="utf-8")
            n += added
    return n


def tm_harvest(args) -> int:
    """Add the checked translations of the work dir to the memory (called after a successful inject)."""
    work = Path(args.work) / args.new
    learner = args.new.split("-")[0]
    tm = tm_load(learner)
    n = 0
    for src in sorted(work.glob("*.src.json")):
        name = src.name[: -len(".src.json")]
        if name == "glosses":
            continue
        tr = dd.load_tr(work, name)
        for it in json.loads(src.read_text(encoding="utf-8"))["items"]:
            k = tm_key(it[1], it[2]) if it[0] != "#" else None
            if k and it[0] in tr and tm.get(k) != tr[it[0]]:
                n += 1
                tm.setdefault(k, tr[it[0]])
    if n:
        TM_DIR.mkdir(parents=True, exist_ok=True)
        tm_path(learner).write_text(json.dumps(dict(sorted(tm.items())), ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    return n


def existing_pairs() -> set[str]:
    return {d.name for d in (CONTENT / "overlays").iterdir() if d.is_dir()}


def all_missing_pairs() -> list[str]:
    learners = sorted({p.split("-")[0] for p in existing_pairs()} | {p.split("-")[1] for p in existing_pairs()} - {"en"})
    targets = sorted({p.split("-")[1] for p in existing_pairs() if p.startswith("en-")})
    have = existing_pairs()
    return [f"{x}-{y}" for x in learners for y in targets if x != y and f"{x}-{y}" not in have]


def cmd_plan(args):
    """List every missing X->Y pair with the strings/words a derivation must translate (sibling en-Y), per level set."""
    import types
    rows, total_w, total_i, total_g, pairs = [], 0, 0, 0, all_missing_pairs()
    dd.build_overlay_occs = build_cross_overlay_occs
    per_target: dict[str, tuple[int, int, int]] = {}
    for t in sorted({p.split("-")[1] for p in pairs}):
        try:
            a = types.SimpleNamespace(sibling=f"en-{t}", new=f"x-{t}", levels=args.levels, units=None)
            units, docs, occs, by_file, groups, stats = dd.collect(a)
        except SystemExit:
            continue
        words = sum(len(e[1][0].src.split()) for e in by_file.values() for e in e)
        items = sum(len(e) for e in by_file.values())
        gl = len(lexicon_items(t, args.levels)) if args.glosses else 0
        per_target[t] = (items, words, gl)
    for p in pairs:
        i, w, g = per_target.get(p.split("-")[1], (0, 0, 0))
        total_i, total_w, total_g = total_i + i, total_w + w, total_g + g
        rows.append(f"{p:8s} items={i:6d} words={w:7d} glosses={g:5d}")
    print("\n".join(rows))
    print(f"{len(pairs)} missing pairs, levels {','.join(args.levels)}: {total_i} items, {total_w} words (~{int(total_w * 1.6)} output tokens), "
          f"{total_g} glosses before translation memory")


def cmd_batch(args):
    """extract -> TM prefill -> (translate) -> status -> check for several pairs; resumable (re-run continues)."""
    for pair in args.pairs:
        a = argparse.Namespace(**{**vars(args), "new": pair, "sibling": None})
        print(f"=== {pair} ===")
        cmd_extract(a)
        print(f"  translation memory filled {tm_prefill(a)} item(s)")
        if args.gemini:
            a.model, a.batch = args.model, args.batch
            cmd_translate(a)
        work = Path(args.work) / pair
        miss = 0
        for src in work.glob("*.src.json"):
            name = src.name[: -len(".src.json")]
            ids = [i[0] for i in json.loads(src.read_text(encoding="utf-8"))["items"] if i[0] != "#"]
            miss += sum(1 for i in ids if i not in dd.load_tr(work, name))
        print(f"  {pair}: {miss} item(s) still untranslated")
        if not miss and args.inject:
            a.allow_missing = a.force = a.no_backfill = False
            cmd_inject(a)
            print(f"  translation memory +{tm_harvest(a)}")


def cmd_check(args):
    """Lint the *.tr.json files against their *.src.json (placeholders, asterisk spans, kept target words, English left)."""
    work = Path(args.work) / args.new
    names = args.files or sorted(p.name[: -len(".src.json")] for p in work.glob("*.src.json"))
    bad = 0
    for name in names:
        src = json.loads((work / f"{name}.src.json").read_text(encoding="utf-8"))["items"]
        tr = dd.load_tr(work, name)
        miss = [i[0] for i in src if i[0] != "#" and i[0] not in tr]
        probs = []
        for i in src:
            if i[0] == "#" or i[0] not in tr:
                continue
            for pr in lint(i[1], i[2], tr[i[0]]):
                probs.append(f"{name}:{i[0]} [{i[1].split()[0]}] {pr}: {tr[i[0]][:70]!r}")
            if tr[i[0]].strip() == i[2].strip() and english_prose(i[2]):
                probs.append(f"{name}:{i[0]} [{i[1].split()[0]}] unchanged English: {i[2][:60]!r}")
        extra = [k for k in tr if k not in {i[0] for i in src}]
        print(f"{name}: {len(src) - sum(1 for i in src if i[0] == '#') - len(miss)}/{len([i for i in src if i[0] != '#'])} translated"
              + (f", MISSING {miss[:5]}" if miss else "") + (f", unknown ids {extra[:3]}" if extra else ""))
        for pr in probs[:40]:
            print("  " + pr)
        bad += len(probs) + len(miss) + len(extra)
    sys.exit(1 if bad else 0)


def cmd_inject(args):
    sib = args.sibling or f"en-{args.new.split('-')[1]}"
    args.sibling = sib
    dd.build_overlay_occs = build_cross_overlay_occs
    dd.lint = lint
    dd.load_backfill_module = _load_backfill_for_tags(args.new, sib)
    dd.write_backfill = write_lexicon
    dd.cmd_inject(args)
    localize_pairs(args)
    tm_harvest(args)
    # provenance wording: this tool, not derive_direction.py
    new_dir = CONTENT / "overlays" / args.new
    for p in list(new_dir.glob("*.yaml")) + list((CONTENT / "practice" / args.new).glob("*.yaml")):
        t = p.read_text(encoding="utf-8")
        t2 = t.replace("scripts/derive_direction.py", "scripts/derive_cross.py").replace("derive_direction.py", "derive_cross.py")
        if t2 != t:
            p.write_text(t2, encoding="utf-8")


def localize_pairs(args):
    """matching_pairs: the realization carries the English right-hand clues; the overlay `pairs` override replaces them
    with the translated clues already present in the overlay's accepted answer set (lefts stay byte-identical)."""
    cm = dd.read_manifest(dd.MANIFEST)
    n = 0
    for g in dd.group_names(args.new, args.levels):
        reals, ovs = cm[g]
        for r, o in zip(reals, ovs):
            real, path = dd.load(ROOT / r), ROOT / o
            if args.units and path.stem not in args.units:
                continue
            y = dd.load(path)
            changed = False
            for unit in real.get("units", []):
                for lesson in unit.get("lessons", []):
                    for ex in lesson.get("exercises", []):
                        if ex.get("type") != "matching_pairs" or not ex.get("pairs"):
                            continue
                        ov = y.get("exercises", {}).get(ex["content_key"])
                        if ov is None:
                            continue
                        acc = {}
                        for a in ov.get("accepted_answers") or []:
                            v = a.get("value") if isinstance(a, dict) else None
                            if isinstance(v, list):
                                acc.update({p["left"]: p["right"] for p in v if isinstance(p, dict) and "left" in p})
                        cr = ov.get("correct_response")
                        if isinstance(cr, dict):
                            acc.update({k: v for k, v in cr.items() if isinstance(v, str)})
                        elif isinstance(cr, list):
                            acc.update({q["left"]: q["right"] for q in cr if isinstance(q, dict) and "left" in q and "right" in q})
                        pairs = [{"left": p["left"], "right": acc.get(p["left"], p["right"])} for p in ex["pairs"]]
                        if pairs != ov.get("pairs"):
                            ov["pairs"] = pairs
                            changed = True
                            n += 1
            if changed:
                dd.dump(y, path)
    print(f"localized {n} matching_pairs clue sets")


def _load_backfill_for_tags(new_pair: str, sib: str):
    def loader(pair):
        use = sib if pair == new_pair else pair
        src, tgt = use.split("-")
        path = ROOT / f"scripts/backfill_lexemes_{src}_{tgt}.py"
        if not path.exists():
            return None, path
        sys.path.insert(0, str(ROOT / "scripts"))
        return importlib.import_module(f"backfill_lexemes_{src}_{tgt}"), path
    return loader


def write_lexicon(args, work: Path, units):
    learner, target = args.new.split("-")
    gsrc = json.loads((work / "glosses.src.json").read_text(encoding="utf-8"))
    tr = dd.load_tr(work, "glosses")
    path = LEXICON / f"{args.new}.json"
    lex = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    fresh: dict[str, dict] = {}
    missing = 0
    for gid, key, _src in (it for it in gsrc["items"] if it[0] != "#"):
        lvl, tok, _pos = key.split("|", 2)
        if gid not in tr:
            missing += 1
            continue
        fresh.setdefault(lvl, {})[tok] = tr[gid]
    if missing and not args.allow_missing:
        sys.exit(f"{missing} lexeme glosses have no translation (glosses.tr.json)")
    lex.update(fresh)
    LEXICON.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({k: lex[k] for k in sorted(lex)}, ensure_ascii=False, indent=0, sort_keys=False) + "\n", encoding="utf-8")
    shim = ROOT / f"scripts/backfill_lexemes_{learner}_{target}.py"
    shim.write_text(f'''#!/usr/bin/env python3
"""Idempotently backfill {args.new} ({dd.lang_name(target)} target, {dd.lang_name(learner)} learner) lexemes.

Generated by scripts/derive_cross.py.  Tokens, parts of speech and tags are the en-{target} classification
(scripts/backfill_lexemes_en_{target}.py); the {dd.lang_name(learner)} glosses live in docs/content/lexicon/{args.new}.json.

Run (after the {args.new} course is imported), from backend/:

    docker compose run --rm -v "$(cd .. && pwd):/repo" -e PYTHONPATH=/repo/backend \\\\
      --entrypoint python api /repo/scripts/backfill_lexemes_{learner}_{target}.py

Add --dry-run to classify without touching the database.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cross_lexeme_backfill import build, main  # noqa: E402


def iter_specs():
    """Specs for the practice-pack checks (same interface as the other backfill scripts)."""
    return build("{learner}", "{target}")[1]()


if __name__ == "__main__":
    raise SystemExit(main("{learner}", "{target}"))
''', encoding="utf-8")
    shim.chmod(0o755)
    print(f"wrote {path.relative_to(ROOT)} ({sum(len(v) for v in fresh.values())} glosses) and {shim.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# translate (Gemini)
# ---------------------------------------------------------------------------
def gemini_key() -> str:
    import os
    k = os.environ.get("GEMINI_API_KEY", "")
    if not k:
        p = ROOT / "secrets/gemini/api-key.txt"
        if p.exists():
            k = p.read_text().strip()
    if not k:
        sys.exit("no Gemini key: set GEMINI_API_KEY or create secrets/gemini/api-key.txt (never committed)")
    return k


def gemini_call(model: str, prompt: str, key: str) -> str:
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}}).encode()
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=body, headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["candidates"][0]["content"]["parts"][0]["text"]


def cmd_translate(args):
    work = Path(args.work) / args.new
    guide = (work / "GUIDE.md").read_text(encoding="utf-8")
    key = gemini_key()
    for src in sorted(work.glob("*.src.json")):
        name = src.name[: -len(".src.json")]
        items = json.loads(src.read_text(encoding="utf-8"))["items"]
        tr = dd.load_tr(work, name)
        todo = [it for it in items if it[0] != "#" and it[0] not in tr]
        if not todo:
            continue
        # keep context rows next to their items, in chunks of ~60 items
        chunk, chunks, pending_ctx = [], [], None
        for it in items:
            if it[0] == "#":
                pending_ctx = it
                continue
            if it[0] in tr:
                continue
            if pending_ctx:
                chunk.append(pending_ctx)
                pending_ctx = None
            chunk.append(it)
            if sum(1 for c in chunk if c[0] != "#") >= args.batch:
                chunks.append(chunk)
                chunk = []
        if chunk:
            chunks.append(chunk)
        for ch in chunks:
            prompt = (guide + "\n\nTranslate these items. Return ONLY a JSON object {id: translation} with one entry for every "
                      "non-'#' item.\n\n" + "\n".join(json.dumps(c, ensure_ascii=False) for c in ch))
            for attempt in range(3):
                try:
                    out = json.loads(gemini_call(args.model, prompt, key))
                    break
                except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
                    print(f"  retry {attempt + 1}: {type(e).__name__}")
            else:
                sys.exit("translate failed")
            tr.update({k: v for k, v in out.items() if isinstance(v, str)})
            (work / f"{name}.tr.json").write_text(json.dumps(tr, ensure_ascii=False, indent=0), encoding="utf-8")
        print(f"{name}: {len(todo)} translated")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------
STRICT_LEARNER_ROLES = {"instruction", "feedback", "note", "gloss", "example_gloss", "course_description",
                        "prompt_block", "glosses", "accepted_note"}


def english_prose(v: str) -> bool:
    """English sentence left in a learner-language string (function-word evidence; Spanish/French/Italian cognates do not count)."""
    toks = norm_tokens(v)
    if len(toks) < 3:
        return False
    hits = [t for t in toks if t in EN_ONLY]
    return len(set(hits)) >= 2 or bool(set(hits) & EN_STRONG)


def learner_leftovers(pair: str) -> list[str]:
    """Learner-role strings of a cross pair that are still English prose, or that changed target-language text."""
    learner, target = pair.split("-")
    sib = f"en-{target}"
    out = []
    for kind in ("overlays", "practice"):
        d = CONTENT / kind / pair
        for p in sorted(d.glob("*.yaml")) if d.is_dir() else []:
            sp = CONTENT / kind / sib / p.name
            if not sp.exists():
                out.append(f"{kind}/{pair}/{p.name}: no sibling file {sib}")
                continue
            y, s = dd.load(p), dd.load(sp)
            ys, ss = dict(dd.walk_strings(y)), dict(dd.walk_strings(s))
            added = {k for k in ys if k not in ss and len(k) > 2 and k[0] == "exercises" and k[2] in ("prompt_blocks", "pairs")}
            ys = {k: v for k, v in ys.items() if k not in added and k[0] not in ("review", "generation_provenance", "status")}
            ss = {k: v for k, v in ss.items() if k[0] not in ("review", "generation_provenance", "status")}
            if set(ys) != set(ss):
                out.append(f"{kind}/{pair}/{p.name}: structure differs from {sib}")
                continue
            for path, v in ys.items():
                if path[0] in ("review", "generation_provenance", "status"):
                    continue
                role = dd.overlay_role(path) if kind == "overlays" else "packtext"
                if kind == "overlays" and role is None:
                    if path[-2:-1] == ("prompt_blocks",) or path[2:3] == ("prompt_blocks",):
                        role = "prompt_block"
                    elif len(path) > 2 and path[0] == "teaching" and path[2] == "glosses":
                        role = "glosses"
                    else:
                        continue
                if v == ss[path] and not (role in STRICT_LEARNER_ROLES or role in ("title", "packtext")
                                          and path[0] != "teaching"):
                    continue          # unchanged option/answer/title text is normally target-language text
                if english_prose(v):
                    out.append(f"{kind}/{pair}/{p.name}: {'/'.join(map(str, path))[-60:]}: {v[:70]!r} [English]")
    return out


def compiled_leftovers(path: Path) -> list[str]:
    """English prose (or language_code en blocks) in the compiled course JSON of a cross pair: what the learner would see."""
    d = json.loads(path.read_text(encoding="utf-8"))
    out = []

    def walk(o, trail):
        if isinstance(o, dict):
            if o.get("language_code") == "en" and isinstance(o.get("text"), str):
                out.append(f"compiled {'/'.join(trail)[-60:]}: English block {o['text'][:60]!r}")
            for k, v in o.items():
                if k not in ("content_key", "media_asset_key", "lesson_content_key", "unit_content_key"):
                    walk(v, trail + [str(k)])
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, trail + [str(i)])
        elif isinstance(o, str) and not re.match(r"^[a-z0-9_.\-]+$", o) and english_prose(o):
            out.append(f"compiled {'/'.join(trail)[-60:]}: {o[:70]!r} [English]")

    walk(d, [])
    return out


def cmd_validate(args):
    import subprocess
    py = str(ROOT / ".content-venv/bin/python")
    if not Path(py).exists():
        py = sys.executable
    cm, pm = dd.read_manifest(dd.MANIFEST), dd.read_manifest(dd.PRACTICE_MANIFEST)
    fails = 0
    for g in dd.group_names(args.new, args.levels):
        reals, ovs = cm[g]
        for mode, extra in (("validate", []), ("compile", ["--out", f"/tmp/derive_cross_{g}.json"])):
            r = subprocess.run([py, "scripts/compile_content.py", mode, "--realization", *reals, "--overlay", *ovs, *extra],
                               cwd=ROOT, capture_output=True, text=True)
            tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
            print(f"{mode:9s} {g}: rc={r.returncode} {tail[0]}")
            fails += r.returncode != 0
    if args.new in pm:
        r = subprocess.run([py, "scripts/compile_content.py", "practice-validate", "--pack", *pm[args.new][0],
                            "--content-root", "docs/content/realizations"], cwd=ROOT, capture_output=True, text=True)
        print(f"practice-validate {args.new}: rc={r.returncode} {(r.stdout + r.stderr).strip().splitlines()[-1:]}")
        fails += r.returncode != 0
    left = learner_leftovers(args.new)
    for g in dd.group_names(args.new, args.levels):
        left += compiled_leftovers(Path(f"/tmp/derive_cross_{g}.json"))
    for h in left[:60]:
        print("  " + h)
    print(f"cross-leftover  {len(left)} string(s)")
    sys.exit(1 if fails or left else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("extract", cmd_extract), ("translate", cmd_translate), ("status", dd.cmd_status), ("check", cmd_check), ("plan", cmd_plan), ("batch", cmd_batch),
                     ("inject", cmd_inject), ("validate", cmd_validate)):
        sp = sub.add_parser(name)
        if name == "batch":
            sp.add_argument("--pairs", required=True, type=lambda s: s.split(","))
            sp.add_argument("--gemini", action="store_true", help="translate missing ids with the Gemini API")
            sp.add_argument("--inject", action="store_true", help="inject pairs that are fully translated")
            sp.add_argument("--model", default="gemini-2.5-flash")
            sp.add_argument("--batch", type=int, default=60)
        elif name == "plan":
            sp.add_argument("--glosses", action="store_true")
        else:
            sp.add_argument("--new", required=True, help="new direction X-Y, e.g. es-fr (sibling is en-Y)")
        sp.add_argument("--sibling", default=None)
        sp.add_argument("--levels", default="a1", type=lambda s: s.split(","))
        sp.add_argument("--units", type=lambda s: s.split(","))
        sp.add_argument("--work", default=str(WORK))
        if name == "check":
            sp.add_argument("files", nargs="*", help="file stems, e.g. a1_unit05 shared glosses (default: all)")
        if name == "translate":
            sp.add_argument("--model", default="gemini-2.5-flash")
            sp.add_argument("--batch", type=int, default=60)
        if name == "inject":
            sp.add_argument("--allow-missing", action="store_true")
            sp.add_argument("--force", action="store_true")
            sp.add_argument("--no-backfill", action="store_true")
        sp.set_defaults(fn=fn)
    args = ap.parse_args()
    if args.cmd in ("translate", "status", "check"):
        args.sibling = args.sibling or f"en-{args.new.split('-')[1]}"
    args.fn(args)


if __name__ == "__main__":
    main()
