"""Compile-time attachment of pronunciation (romanization) to compiled content.

Additive only: text blocks gain `translit`; exercise prompts gain `translit_map`
({exact target string as it appears in options / word_bank / pairs: romanization}).
Nothing existing is changed, and content in languages without a store is untouched.

Answer-leak rules (the romanization must never give away the answer):
  * a prompt text block whose normalised text equals any correct answer gets no translit
  * `romanize*` exercises (the answer IS the romanization) get nothing at all
  * exercises in a `script_ramp` lesson (letter-sound drills) get nothing
  * listen_* / dictation exercises get no prompt-block translit (audio is the stimulus)
"""
from __future__ import annotations

from typing import Any

from .common import LANGS, load_store, normalize_key, split_tokens

_STORES: dict[str, dict[str, dict]] = {}
_NO_PROMPT_TRANSLIT = {"listen_select", "listen_type", "dictation", "listen_order"}


def _store(lang: str) -> dict[str, dict]:
    if lang not in _STORES:
        _STORES[lang] = load_store(lang).get("entries", {}) if lang in LANGS else {}
    return _STORES[lang]


def lookup_entry(text: Any, lang: str) -> dict | None:
    if not isinstance(text, str) or not _store(lang):
        return None
    return _store(lang).get(normalize_key(text, lang))


def lookup(text: Any, lang: str) -> str | None:
    e = lookup_entry(text, lang)
    return e["romanization"] if e else None


def _answer_keys(correct: Any, lang: str) -> set[str]:
    out: set[str] = set()

    def walk(v: Any) -> None:
        if isinstance(v, str):
            out.add(normalize_key(v, lang))
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)

    walk(correct)
    return out


def attach_card(card: dict[str, Any], lang: str) -> None:
    def blocks(bs: list[dict[str, Any]]) -> None:
        for b in bs:
            if str(b.get("language_code", "")).split("-")[0] == lang:
                e = lookup_entry(b.get("text"), lang)
                if e:
                    b["translit"] = e["romanization"]
                    b["translit_reviewed"] = bool(e.get("reviewed"))

    blocks(card.get("text_blocks", []))
    for ex in card.get("examples", []) or []:
        blocks(ex.get("text_blocks", []))


def attach_exercise(ex: dict[str, Any], lang: str, module_kind: str | None = None) -> None:
    if lang not in LANGS or not _store(lang):
        return
    if module_kind == "script_ramp":
        return  # letter-to-sound drills: the romanization IS the answer
    key = str(ex.get("content_key", ""))
    if "romanize" in key or "romanise" in key:
        return
    prompt = ex["prompt"]
    answers = _answer_keys(ex.get("correct_response"), lang)

    def blocks(bs: list[dict[str, Any]]) -> None:
        for b in bs:
            if str(b.get("language_code", "")).split("-")[0] != lang:
                continue
            if normalize_key(str(b.get("text", "")), lang) in answers:
                continue
            e = lookup_entry(b.get("text"), lang)
            if e:
                b["translit"] = e["romanization"]
                b["translit_reviewed"] = bool(e.get("reviewed"))

    if ex["type"] not in _NO_PROMPT_TRANSLIT:
        blocks(prompt.get("text_blocks", []))
        blocks(prompt.get("back_text_blocks", []) or [])

    tmap: dict[str, str] = {}
    reviewed: list[str] = []

    def add(s: Any) -> None:
        if isinstance(s, str) and s not in tmap:
            e = lookup_entry(s, lang)
            if e:
                tmap[s] = e["romanization"]
                if e.get("reviewed"):
                    reviewed.append(s)

    for o in prompt.get("options", []) or []:
        add(o)
    for w in prompt.get("word_bank", []) or []:
        add(w)
    for p in prompt.get("pairs", []) or []:
        if isinstance(p, dict):
            add(p.get("left"))
            add(p.get("right"))
    if tmap:
        prompt["translit_map"] = tmap
        if reviewed:
            prompt["translit_reviewed_list"] = reviewed
