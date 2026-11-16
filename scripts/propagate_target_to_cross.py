#!/usr/bin/env python3
"""Copy target-language-side changes of the en-<tgt> overlays to every cross overlay <src>-<tgt> (src != en).

Cross overlays are derived from en-<tgt> (see derive_cross.py): target-language text is byte-identical to the English-source
overlay, learner-language text is translated.  Later fixes to target-language text made only in en-<tgt> (extra accepted answers,
corrected tiles / distractors / correct options / listening transcripts) must be mirrored, which is what this does.

Never copies learner-language text.  Two mechanisms, both deterministic:

  1. accepted_answers (current-state sync).  Only string answers.  An exercise counts as target-language when the realization
     exercise type is one whose answers are typed/spoken in the target language (derive_cross.TARGET_ANSWER_TYPES), or when every
     string of the cross list also occurs in the en list (untranslated, so target text).  A list that mixes in strings en lacks
     (translated learner-language answers) is skipped.  The cross list is then rebuilt in the en order: an entry whose value the
     cross list already has is kept (so its translated `note` survives), any other entry is copied from en without its `note`
     (learner-language text).  Entries only the cross list had are dropped (removed in en).
  2. feedback / distractors / correct_option (history sync).  If the en value changed between --base and HEAD and the cross value
     still equals the OLD en value byte for byte (so it is untranslated target text), it is replaced by the new en value; values the
     cross overlay translated are left alone.  A replacement that reads as English prose is refused.

Exercises that exist on only one side, matching-pair (dict/list valued) answers and anything else of a different shape are skipped
and logged.  Usage:
    python3 scripts/propagate_target_to_cross.py [--base 236bcc335~1] [--pairs ar-de,es-fr] [--dry-run] [--log FILE]
"""
from __future__ import annotations

import argparse
import copy
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive_cross as dc  # noqa: E402
import derive_direction as dd  # noqa: E402

OV = dc.CONTENT / "overlays"
HISTORY_FIELDS = ("feedback", "distractors", "correct_option")


def realization_types() -> dict[str, str]:
    types: dict[str, str] = {}
    for p in sorted((dc.CONTENT / "realizations").glob("*/*.yaml")):
        for k, v in dd.realization_index(p).items():
            if "type" in v:
                types[k] = v["type"]
    return types


def at_rev(rev: str, path: Path):
    rel = path.relative_to(dd.ROOT).as_posix()
    try:
        out = subprocess.check_output(["git", "show", f"{rev}:{rel}"], cwd=dd.ROOT, text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return None
    return yaml.safe_load(out)


def val(a):
    return a["value"] if isinstance(a, dict) else a


def reads_english(text: str, tgt: str) -> bool:
    """Learner-language (English) text must never be copied into a cross overlay."""
    return dc.english_prose(text) or dc.looks_english(text, tgt)


def sync_accepted(ck, p_ex, s_ex, b_ex, etype, stats, log, where, tgt):
    ea, ca = s_ex.get("accepted_answers"), p_ex.get("accepted_answers")
    if ea is None or ea == ca:
        return False
    if ca is None:
        log.append(f"{where} {ck}: accepted_answers only in en: skipped (shape)")
        stats["skip_shape"] += 1
        return False
    ev, cv = [val(a) for a in ea], [val(a) for a in ca]
    if any(not isinstance(v, str) for v in ev + cv):
        stats["skip_nonstr"] += 1                       # matching-pair answers: learner-language clues
        return False
    if ev == cv:
        return False
    old = {val(x) for x in b_ex.get("accepted_answers") or []}
    if not (set(ev) & set(cv)) and not set(cv) <= old and etype not in dc.TARGET_ANSWER_TYPES:
        stats["skip_learner"] += 1                      # answers are in the learner language here
        return False
    if etype not in dc.TARGET_ANSWER_TYPES and not (set(ev) & set(cv)) and any(reads_english(v, tgt) for v in ev):
        log.append(f"{where} {ck}: en answers turned into learner-language text, cross needs a translation: skipped")
        stats["skip_en_became_learner"] += 1
        return False
    have = {val(a): a for a in ca}
    if etype not in dc.TARGET_ANSWER_TYPES and not set(cv) <= set(ev) | old:
        # the cross list holds strings en lacks: translated learner-language answers mixed with shared ones
        log.append(f"{where} {ck}: accepted_answers mix learner-language entries, skipped")
        stats["skip_mixed"] += 1
        return False
    new = []
    for i, a in enumerate(ea):
        v = val(a)
        if v in have:
            new.append(have[v])
        else:
            if isinstance(a, dict) and "note" in a:
                a = {k: x for k, x in a.items() if k != "note"}
                old = ca[i] if i < len(ca) else None
                if isinstance(old, dict) and "note" in old:
                    a["note"] = old["note"]                  # translated learner-language note of the entry it replaces
                    stats["note_kept"] += 1
                else:
                    stats["note_dropped"] += 1
            new.append(copy.deepcopy(a))
    stats["acc_added"] += len([v for v in ev if v not in have])
    stats["acc_removed"] += len([v for v in cv if v not in set(ev)])
    p_ex["accepted_answers"] = new
    return True


def sync_history(ck, p_ex, s_ex, b_ex, stats, log, where, tgt):
    changed = False
    for f in HISTORY_FIELDS:
        if f not in s_ex or f not in b_ex or s_ex[f] == b_ex[f] or f not in p_ex:
            continue
        if p_ex[f] != b_ex[f]:
            stats["hist_skip_translated"] += 1          # cross value differs from the old en value: learner-language or already fixed
            continue
        new = s_ex[f]
        strs = [new] if isinstance(new, str) else [x for x in new if isinstance(x, str)] if isinstance(new, list) else []
        if any(reads_english(x, tgt) for x in strs):
            log.append(f"{where} {ck}: {f} new value reads as English, not copied")
            stats["hist_refused_english"] += 1
            continue
        p_ex[f] = copy.deepcopy(new)
        stats["hist_" + f] += 1
        changed = True
    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="236bcc335~1", help="git rev just before the en-<tgt> fixes (history sync)")
    ap.add_argument("--pairs", type=lambda s: s.split(","))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--log")
    a = ap.parse_args()
    types = realization_types()
    stats: Counter = Counter()
    log: list[str] = []
    pairs = a.pairs or sorted(d.name for d in OV.iterdir() if d.is_dir() and "en" not in d.name.split("-")
                              and (OV / f"en-{d.name.split('-')[1]}").is_dir())
    base_cache: dict[Path, object] = {}
    for pair in pairs:
        tgt = pair.split("-")[1]
        for p in sorted((OV / pair).glob("*.yaml")):
            sp = OV / f"en-{tgt}" / p.name
            if not sp.exists():
                log.append(f"{pair}/{p.name}: no en sibling")
                continue
            y, s = dd.load(p), dd.load(sp)
            if sp not in base_cache:
                base_cache[sp] = at_rev(a.base, sp)
            b = base_cache[sp] or {}
            where = f"{pair}/{p.name}"
            touched = False
            for ck, s_ex in (s.get("exercises") or {}).items():
                p_ex = (y.get("exercises") or {}).get(ck)
                if p_ex is None:
                    log.append(f"{where} {ck}: exercise missing in cross overlay (shape differs): skipped")
                    stats["skip_missing"] += 1
                    continue
                b_ex = (b.get("exercises") or {}).get(ck) or {}
                touched |= sync_accepted(ck, p_ex, s_ex, b_ex, types.get(ck), stats, log, where, tgt)
                touched |= sync_history(ck, p_ex, s_ex, b_ex, stats, log, where, tgt)
            if touched:
                stats["files_changed"] += 1
                if not a.dry_run:
                    dd.dump(y, p)
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    if a.log:
        Path(a.log).write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"logged {len(log)} skipped/refused items" + (f" to {a.log}" if a.log else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
