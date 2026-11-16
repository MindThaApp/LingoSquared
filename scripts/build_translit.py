#!/usr/bin/env python3
"""Build / check the pronunciation store docs/content/translit/<lang>.json.

  build_translit.py rule --lang ru|hi     rule-generate every target string (source=rule)
  build_translit.py export-backend --lang L   write the compact backend mirror used by grading
                                          (backend/app/data/translit/<lang>.json; answers + single words)
  build_translit.py check [--lang L]      validate stores (shape, keys normalised, Latin-only output,
                                          coverage of the current corpus; exits 1 on structural errors)
LLM-drafted languages (ar, fa, prs) are produced by scripts/translit/llm_draft.py.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from translit.common import LANGS, STORE_DIR, collect_target_strings, latin_ok, load_store, normalize_key, save_store  # noqa: E402
from translit import rules  # noqa: E402

RULE_FN = {"ru": rules.ru, "hi": rules.hi}
SCHEMES = {"ru": "ru-bgn-simple-v1", "hi": "hi-hunterian-schwa-v1"}


def cmd_rule(lang: str) -> None:
    store = load_store(lang)
    store.setdefault("lang", lang)
    store["scheme"] = SCHEMES[lang]
    store["entries"] = {k: e for k, e in store.get("entries", {}).items() if e.get("source") != "rule"}
    n = 0
    for key in collect_target_strings(lang):
        e = store["entries"].get(key)
        if e and e.get("source") == "human":
            continue
        r = RULE_FN[lang](key)
        if not r.strip():
            continue
        store["entries"][key] = {"romanization": r, "scheme": SCHEMES[lang], "source": "rule", "reviewed": False}
        n += 1
    save_store(lang, store)
    print(f"{lang}: {n} rule entries written ({len(store['entries'])} total)")


ANSWER_KEYS = {"accepted_answers", "correct_response", "canonical", "accepted", "value", "tested_text"}


def _answer_strings(node, lang, in_answer=False):
    from translit.common import is_target_string

    if isinstance(node, str):
        if in_answer and is_target_string(node, lang):
            yield normalize_key(node, lang)
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _answer_strings(v, lang, in_answer or k in ANSWER_KEYS)
    elif isinstance(node, list):
        for v in node:
            yield from _answer_strings(v, lang, in_answer)


def cmd_export_backend(lang: str) -> None:
    import json
    import yaml
    from translit.common import CONTENT, REPO

    store = load_store(lang)["entries"]
    answers: set[str] = set()
    for f in [*(CONTENT / "realizations" / lang).glob("*.yaml")] + [
        g for d in sorted((CONTENT / "overlays").glob(f"*-{lang}")) for g in d.glob("*.yaml")
    ]:
        doc = yaml.load(f.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader)
        answers.update(_answer_strings(doc, lang))
    keep = {k: e["romanization"] for k, e in store.items() if k in answers or " " not in k}
    out = REPO / "backend" / "app" / "data" / "translit" / f"{lang}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"v": 1, "lang": lang, "entries": dict(sorted(keep.items()))}
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{lang}: {len(keep)} entries -> {out.relative_to(REPO)} ({out.stat().st_size // 1024} KiB)")


def cmd_check(langs) -> int:
    bad = 0
    for lang in langs:
        p = STORE_DIR / f"{lang}.json"
        if not p.exists():
            print(f"{lang}: no store")
            continue
        st = load_store(lang)
        ents = st["entries"]
        errs = 0
        for k, e in ents.items():
            ok = (
                normalize_key(k, lang) == k
                and set(e) == {"romanization", "scheme", "source", "reviewed"}
                and e["source"] in ("rule", "llm", "human")
                and isinstance(e["reviewed"], bool)
                and latin_ok(e["romanization"])
            )
            if not ok:
                errs += 1
                if errs <= 5:
                    print(f"  {lang}: bad entry {k!r}: {e}")
        cov = sum(1 for k in collect_target_strings(lang) if k in ents)
        tot = len(collect_target_strings(lang))
        print(f"{lang}: {len(ents)} entries, {errs} structural errors, corpus coverage {cov}/{tot}")
        bad += errs
    return 1 if bad else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rule")
    r.add_argument("--lang", required=True, choices=["ru", "hi"])
    x = sub.add_parser("export-backend")
    x.add_argument("--lang", required=True, choices=list(LANGS))
    c = sub.add_parser("check")
    c.add_argument("--lang", default=None)
    a = ap.parse_args()
    if a.cmd == "rule":
        cmd_rule(a.lang)
    elif a.cmd == "export-backend":
        cmd_export_backend(a.lang)
    else:
        sys.exit(cmd_check([a.lang] if a.lang else list(LANGS)))
