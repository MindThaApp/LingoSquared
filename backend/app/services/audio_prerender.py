"""Shared helpers for pre-rendered audio (stdlib only, importable standalone).

Used by scripts/render_audio.py (renders the files) and by the API's static
fallback route (serves them). The web frontend computes the same file names with
packages/shared/src/audio/audioKey.ts; the shared test vectors in
backend/tests/test_audio_prerender.py pin the two implementations together.

File name = sha256("\n".join([provider, voice, language, normalized_text, rate]))[:32] + ".mp3"
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

AUDIO_NAME_RE = re.compile(r"^[0-9a-f]{32}\.mp3$")
_WS = re.compile("[ \t\r\n\f\v\u00a0\u2028\u2029]+")


def default_voices_path() -> Path:
    # backend/app/services -> repo root is parents[3] (LINGO_REPO_ROOT overrides,
    # for containers where only backend/ is mounted at /app and the repo is at /repo)
    root = os.environ.get("LINGO_REPO_ROOT")
    base = Path(root) if root else Path(__file__).resolve().parents[3]
    return base / "packages" / "shared" / "src" / "audio" / "voices.json"


def load_voices(path: Path | None = None) -> dict:
    return json.loads((path or default_voices_path()).read_text(encoding="utf-8"))


def normalize_text(text: str) -> str:
    return _WS.sub(" ", unicodedata.normalize("NFC", text)).strip()


def audio_key(provider: str, voice: str, language: str, text: str, rate: str) -> str:
    payload = "\n".join([provider, voice, language, normalize_text(text), rate])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def file_name_for(voices: dict, language: str, text: str) -> str | None:
    entry = voices["languages"].get(language)
    norm = normalize_text(text)
    if not entry or not norm:
        return None
    return audio_key(entry["provider"], entry["voice"], language, norm, voices["render_rate"]) + ".mp3"


# --- Python port of frontend/src/lib/sanitizeForSpeech.ts -------------------
# Kept in lock-step with the TS file (parity is checked in tests when node is
# available). `re` has no \p{..}, so L/M are expanded from unicodedata once.

def _class_ranges(prefixes: tuple[str, ...], limit: int = 0x30000) -> str:
    out: list[str] = []
    start = prev = None
    for cp in range(0x80, limit):
        if unicodedata.category(chr(cp)).startswith(prefixes):
            if start is None:
                start = prev = cp
            elif cp == prev + 1:
                prev = cp
            else:
                out.append((start, prev)); start = prev = cp
    if start is not None:
        out.append((start, prev))
    esc = lambda c: "\\U%08x" % c
    return "".join(esc(a) if a == b else f"{esc(a)}-{esc(b)}" for a, b in out)


_LM = "A-Za-z" + _class_ranges(("L", "M"))
_LU = "A-Z" + _class_ranges(("Lu",))
_LO = _class_ranges(("Lo",))
_WORD_CONT = rf"[{_LM}‌‍'’.\-]*"
_SPEAKER_LABEL = re.compile(
    rf"^\s*[{_LM}]{_WORD_CONT}(?:\s+[{_LM}]{_WORD_CONT}){{0,2}}\s*(?::\s+|：\s*)"
)
_NAME_WORD = rf"(?:[{_LU}]|[{_LO}]){_WORD_CONT}"
_INNER_LABEL = re.compile(
    rf"([.!?…؟][\"”')»]*\s+|\n\s*){_NAME_WORD}(?:\s+{_NAME_WORD})?\s*(?::\s+|：\s*)"
)
_BLANK = re.compile(r"\s*_{2,}\s*")
_PAREN = re.compile(r"\([^()]*\)|（[^（）]*）")
_BRACKET = re.compile(r"\[[^\[\]]*\]|【[^【】]*】")
_ARROWS = re.compile(r"\s*(?:<=>|<->|<-|->|=>|<=|[→←⇒⇐↔⇔➔➜➞⟶⟵])\s*")


def sanitize_for_speech(text: str) -> str:
    out = _SPEAKER_LABEL.sub("", text, count=1)
    out = _INNER_LABEL.sub(r"\1", out)
    out = _INNER_LABEL.sub(r"\1", out)
    out = _BLANK.sub(" … ", out)
    out = re.sub(r"… ([.,!?;:])", r"…\1", out)
    out = _PAREN.sub(" ", out)
    out = _BRACKET.sub(" ", out)
    out = _ARROWS.sub(", ", out)
    out = re.sub(r"\s+", " ", out).strip()
    out = re.sub(r"^[,\s]+|[,\s]+$", "", out)
    out = re.sub(r"\s+,", ",", out)
    out = re.sub(r",(?:\s*,)+", ",", out)
    return out.strip()


if __name__ == "__main__":  # tiny CLI: print the hash file name for TEXT in LANG
    v = load_voices()
    print(file_name_for(v, sys.argv[1], sys.argv[2]))
