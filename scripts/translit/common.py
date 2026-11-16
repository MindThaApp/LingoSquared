"""Shared helpers for the pronunciation (romanization) store.

Store layout: docs/content/translit/<lang>.json  ->
  {"lang": "fa", "scheme": "...", "entries": {<normalized target string>: {
      "romanization": str, "scheme": str, "source": "rule|llm|human", "reviewed": bool}}}

The key normalisation here MUST stay identical to frontend/src/lib/translitKey.ts
and (if used) backend; both are covered by shared fixtures in tests.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any, Iterator

REPO = Path(__file__).resolve().parents[2]
CONTENT = REPO / "docs" / "content"
STORE_DIR = CONTENT / "translit"

LANGS = ("ru", "hi", "ar", "fa", "prs")
SCRIPT_RANGES = {
    "ru": [(0x0400, 0x04FF)],
    "hi": [(0x0900, 0x097F)],
    "ar": [(0x0600, 0x06FF), (0x0750, 0x077F)],
    "fa": [(0x0600, 0x06FF), (0x0750, 0x077F)],
    "prs": [(0x0600, 0x06FF), (0x0750, 0x077F)],
}

_BIDI = dict.fromkeys(
    [0x200E, 0x200F, 0x061C, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069],
    None,
)
# Arabic harakat, superscript alef, tatweel.
_ARABIC_MARKS = {c: None for c in list(range(0x064B, 0x0653)) + [0x0670, 0x0640]}
_ARABIC_FOLD = {0x064A: "ی", 0x0649: "ی", 0x0643: "ک"}  # ي/ى -> ی, ك -> ک (fa/prs only)
_PUNCT_EDGE = " \t\r\n.,;:!?،؛؟۔…\"'()[]{}«»‘’“”-–—।"


def normalize_key(text: str, lang: str) -> str:
    """Normalised lookup key for a target-language string."""
    t = unicodedata.normalize("NFC", text).translate(_BIDI).replace("*", "")  # '*' = emphasis markup
    if lang in ("ar", "fa", "prs"):
        t = t.translate(_ARABIC_MARKS)
        if lang in ("fa", "prs"):
            t = t.translate(_ARABIC_FOLD)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _in_script(ch: str, lang: str) -> bool:
    o = ord(ch)
    return any(a <= o <= b for a, b in SCRIPT_RANGES[lang])


def is_target_string(s: str, lang: str) -> bool:
    letters = [c for c in s if c.isalpha()]
    if not letters or len(s) > 160 or len(s.split()) > 25 or any(c in s for c in "[]+=\u2192{}<>|"):
        return False
    # Reject strings that carry letters/marks of a foreign non-Latin script (learner-language
    # instructions quoting the target text, e.g. Hindi/Korean/CJK prose around a Russian word).
    for c in s:
        if ord(c) > 0x24F and unicodedata.category(c)[0] in "LM" and not _in_script(c, lang) and not (
            lang in ("ar", "fa", "prs") and 0xFB50 <= ord(c) <= 0xFEFF
        ):
            return False
    if re.search(r"[^\W_]_[^\W_]", s):
        return False  # w_слово style lexeme tags
    if re.search(r"[A-Za-z\u00c0-\u024f]{2,}", s):
        return False  # foreign Latin words: learner-language prose or names, nothing to romanize
    n = sum(1 for c in letters if _in_script(c, lang))
    return n >= 1 and n / len(letters) >= 0.8


def _strings(node: Any, skip_keys=("review", "generation_provenance", "content_key", "media_assets")) -> Iterator[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for k, v in node.items():
            if k in skip_keys:
                continue
            yield from _strings(v, skip_keys)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v, skip_keys)


def split_tokens(s: str) -> list[str]:
    out = []
    for tok in s.split():
        tok = tok.strip(_PUNCT_EDGE)
        if tok:
            out.append(tok)
    return out


def content_files(lang: str, kinds=("realizations", "overlays", "practice")) -> list[Path]:
    files = sorted((CONTENT / "realizations" / lang).glob("*.yaml")) if "realizations" in kinds else []
    for sub in [k for k in kinds if k != "realizations"]:
        for d in sorted((CONTENT / sub).glob(f"*-{lang}")):
            files += sorted(d.glob("*.yaml"))
    return files


def collect_target_strings(lang: str, kinds=("realizations", "overlays", "practice")) -> dict[str, int]:
    """normalised target string -> occurrence count (sentences, plus word tokens)."""
    import yaml

    try:
        Loader = yaml.CSafeLoader
    except AttributeError:  # pragma: no cover
        Loader = yaml.SafeLoader
    counts: dict[str, int] = {}
    for f in content_files(lang, kinds):
        doc = yaml.load(f.read_text(encoding="utf-8"), Loader=Loader)
        for s in _strings(doc):
            if "\n" in s.strip() and len(s) > 400:
                continue
            if not is_target_string(s, lang):
                continue
            key = normalize_key(s, lang)
            if len(key) > 160:
                continue
            counts[key] = counts.get(key, 0) + 1
            toks = split_tokens(key)
            if len(toks) > 1:
                for tok in toks:
                    if is_target_string(tok, lang):
                        k2 = normalize_key(tok, lang)
                        counts[k2] = counts.get(k2, 0) + 1
    return counts


def load_store(lang: str) -> dict[str, Any]:
    import json

    p = STORE_DIR / f"{lang}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"lang": lang, "entries": {}}


def save_store(lang: str, store: dict[str, Any]) -> None:
    import json

    STORE_DIR.mkdir(parents=True, exist_ok=True)
    store["entries"] = dict(sorted(store["entries"].items()))
    (STORE_DIR / f"{lang}.json").write_text(
        json.dumps(store, ensure_ascii=False, indent=0, sort_keys=False) + "\n", encoding="utf-8"
    )


def latin_ok(r: str) -> bool:
    """Romanization sanity: has letters; every letter is Latin; no markup junk."""
    letters = [c for c in r if c.isalpha()]
    return bool(letters) and all(ord(c) < 0x250 for c in letters) and not any(c in r for c in "\n\t\u200c\u200f")
