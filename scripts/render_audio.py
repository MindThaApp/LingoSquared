#!/usr/bin/env python3
"""Pre-render every target-language string the app speaks to mp3 files.

Why: POST /tts synthesises per request. Rendering each unique string once, with
a content-hash file name, makes runtime cost ~zero and survives model churn.

Lookup order in the app (see frontend/src/api/tts.ts):
    recorded human clip (/media/<key>)  ->  pre-rendered /media/audio/<hash>.mp3
    ->  POST /tts  ->  browser speechSynthesis

File name = sha256(provider, voice, language, normalized text, rate)[:32].mp3
(backend/app/services/audio_prerender.py and packages/shared/src/audio/audioKey.ts
compute the same name). Voices/providers: packages/shared/src/audio/voices.json.

Slow playback is NOT rendered; the client applies playbackRate (pitch-preserving)
to the single normal-speed file. That halves volume/cost, needs no ffmpeg pass
and works for Chirp 3 HD / Gemini, which have no rate control.

Usage (dry run needs no credentials):
    python scripts/render_audio.py --dry-run [--lang nl,fa]
    python scripts/render_audio.py --max-chars 400000 --lang en --out-dir ~/lingosquared-media/audio
    python scripts/render_audio.py --check-voices            # free list-voices calls only

Credentials come from the environment, then --env-file (default backend/.env),
then secrets/gemini/api-key.txt for GEMINI_API_KEY. Never committed.
Resumable: existing <hash>.mp3 files are skipped; manifest.json is rewritten
atomically every few renders and on exit. Ctrl-C is safe.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
from collections import OrderedDict, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
REALIZATIONS_DIR = REPO_ROOT / "docs" / "content" / "realizations"
PRACTICE_DIR = REPO_ROOT / "docs" / "content" / "practice"


def _load_helpers():
    path = REPO_ROOT / "backend" / "app" / "services" / "audio_prerender.py"
    spec = importlib.util.spec_from_file_location("audio_prerender", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["audio_prerender"] = mod
    spec.loader.exec_module(mod)
    return mod


ap = _load_helpers()

TASHKEEL = re.compile("[ً-ْٰ]")
ARABIC_LETTER = re.compile("[ء-ي]")
LISTEN_TYPES = {"listen_select", "listen_type", "dictation", "listen_order"}
MIN_INTERVAL = {"google": 0.05, "azure": 0.1, "gemini": 4.0}  # seconds between calls, per provider


class RetryableError(Exception):
    def __init__(self, msg: str, retry_after: float | None = None):
        super().__init__(msg)
        self.retry_after = retry_after


# --------------------------------------------------------------------------- collection

def _walk(node: Any):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def collect(realizations: Path | None = None, practice: Path | None = None,
            langs: set[str] | None = None) -> tuple[dict[str, "OrderedDict[str, set[str]]"], dict[str, int]]:
    """Return {language: {raw_text: {source kinds}}} plus counters (dynamic practice frames skipped)."""
    import yaml
    realizations = realizations or REALIZATIONS_DIR
    practice = practice or PRACTICE_DIR
    out: dict[str, OrderedDict[str, set[str]]] = defaultdict(OrderedDict)
    stats = {"dynamic_practice_frames_skipped": 0}

    def add(lang: str, text: Any, kind: str):
        if langs and lang not in langs:
            return
        if isinstance(text, str) and text.strip():
            out[lang].setdefault(text, set()).add(kind)

    for path in sorted(realizations.glob("*/*.yaml")):
        lang = path.parent.name
        if langs and lang not in langs:
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for asset in data.get("media_assets") or []:
            if asset.get("language", lang) == lang:
                add(lang, asset.get("text"), "media_asset")
        for node in _walk(data.get("units") or []):
            if node.get("language_code") == lang and "text" in node:
                add(lang, node["text"], "text_block")
            for tok in node.get("introduced_tokens") or []:
                add(lang, tok, "token")
            if node.get("type") in LISTEN_TYPES:
                add(lang, node.get("tested_text"), "listen_tested_text")
            for pair in node.get("pairs") or []:
                if isinstance(pair, dict):
                    add(lang, pair.get("left"), "pair_left")

    for path in sorted(practice.glob("*/*.yaml")):
        pair = path.parent.name  # e.g. en-nl: source-target
        lang = pair.split("-")[-1]
        if langs and lang not in langs:
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for node in _walk(data.get("templates") or []):
            if node.get("language_code") == lang and isinstance(node.get("text"), str):
                if "{" in node["text"]:
                    stats["dynamic_practice_frames_skipped"] += 1
                else:
                    add(lang, node["text"], "practice_frame")
    return out, stats


def prepare(raw: dict[str, "OrderedDict[str, set[str]]"], voices: dict) -> dict[str, "OrderedDict[str, dict]"]:
    """Sanitize (exactly like the frontend does at the speech boundary), normalize, dedupe, key."""
    plan: dict[str, OrderedDict[str, dict]] = {}
    for lang in sorted(raw):
        entry = voices["languages"].get(lang)
        if not entry:
            continue
        items: OrderedDict[str, dict] = OrderedDict()
        for text, kinds in raw[lang].items():
            spoken = ap.normalize_text(ap.sanitize_for_speech(text))
            if not spoken or not any(c.isalnum() for c in spoken):
                continue
            key = ap.audio_key(entry["provider"], entry["voice"], lang, spoken, voices["render_rate"])
            rec = items.setdefault(key, {"text": spoken, "chars": len(spoken), "kinds": set(), "flags": []})
            rec["kinds"] |= kinds
        for rec in items.values():
            if lang == "ar" and ARABIC_LETTER.search(rec["text"]) and not TASHKEEL.search(rec["text"]):
                rec["flags"].append("arabic_no_tashkeel")
        plan[lang] = OrderedDict(sorted(items.items(), key=lambda kv: kv[0]))
    return plan


# --------------------------------------------------------------------------- reporting

def provider_available(entry: dict, env: dict) -> tuple[bool, str]:
    need = entry.get("requires_env")
    if need and not env.get(need):
        return False, f"{need} is not set"
    return True, ""


def report(plan, voices, out_dir: Path, env: dict, max_chars: int | None, ledger_used: dict) -> dict:
    rows, tiers = [], defaultdict(lambda: {"strings": 0, "chars": 0, "todo_chars": 0})
    for lang, items in plan.items():
        entry = voices["languages"][lang]
        chars = sum(r["chars"] for r in items.values())
        todo = sum(r["chars"] for k, r in items.items() if not (out_dir / f"{k}.mp3").is_file())
        ok, why = provider_available(entry, env)
        flagged = sum(1 for r in items.values() if r["flags"])
        rows.append(dict(lang=lang, tier=entry["tier"], strings=len(items), chars=chars, todo_chars=todo,
                         skipped=(None if ok else why), flagged=flagged))
        t = tiers[entry["tier"]]
        t["strings"] += len(items); t["chars"] += chars; t["todo_chars"] += todo if ok else 0
    print(f"{'lang':5}{'tier':17}{'strings':>9}{'chars':>10}{'to render':>11}  note")
    for r in rows:
        note = f"SKIPPED ({r['skipped']})" if r["skipped"] else ""
        if r["flagged"]:
            note += f" {r['flagged']} strings lack tashkeel (rendered as-is)"
        print(f"{r['lang']:5}{r['tier']:17}{r['strings']:>9}{r['chars']:>10}{r['todo_chars']:>11}  {note}")
    print()
    print(f"{'tier':17}{'strings':>9}{'chars':>10}{'to render':>11}{'free/month':>12}  fit")
    for name, t in sorted(tiers.items()):
        free = voices["tiers"][name]["free_chars_per_month"]
        used = ledger_used.get(name, 0)
        if free is None:
            fit = "n/a (token-billed; free tier rate-limited)"
        else:
            left = free - used
            fit = f"FITS ({t['todo_chars'] * 100 // max(free, 1)}% of allowance)" if t["todo_chars"] <= left else \
                f"EXCEEDS by {t['todo_chars'] - left} -> spread over months or --allow-paid"
        print(f"{name:17}{t['strings']:>9}{t['chars']:>10}{t['todo_chars']:>11}{str(free) if free is not None else '-':>12}  {fit}")
    total = sum(r["chars"] for r in rows); todo_total = sum(t["todo_chars"] for t in tiers.values())
    print(f"\nTOTAL unique strings={sum(r['strings'] for r in rows)} chars={total} to-render chars={todo_total}"
          + (f" (max-chars cap {max_chars})" if max_chars else ""))
    return {"rows": rows, "tiers": dict(tiers), "total_chars": total, "todo_chars": todo_total}


# --------------------------------------------------------------------------- env / secrets

def load_env(env_file: Path | None) -> dict:
    env: dict[str, str] = {}
    if env_file and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    env.update({k: v for k, v in os.environ.items() if v})
    if not env.get("GEMINI_API_KEY"):
        key_file = REPO_ROOT / "secrets" / "gemini" / "api-key.txt"
        if key_file.is_file() and key_file.read_text().strip():
            env["GEMINI_API_KEY"] = key_file.read_text().strip()
    return env


# --------------------------------------------------------------------------- providers

def _raise_http(resp) -> None:
    if resp.status_code in (429, 500, 502, 503, 504):
        ra = resp.headers.get("Retry-After")
        raise RetryableError(f"HTTP {resp.status_code}", float(ra) if ra and ra.isdigit() else None)
    resp.raise_for_status()


def _google_provider(env: dict):
    from google.cloud import texttospeech
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_info(json.loads(env["GOOGLE_CLOUD_TTS_CREDENTIALS_JSON"]))
    client = texttospeech.TextToSpeechClient(credentials=creds)

    def synth(text: str, entry: dict) -> bytes:
        cfg = dict(audio_encoding=texttospeech.AudioEncoding.MP3)
        if "Chirp3" not in entry["voice"]:
            cfg["speaking_rate"] = 1.0  # Chirp 3 HD takes no rate for plain text; normal speed is its default
        try:
            r = client.synthesize_speech(
                input=texttospeech.SynthesisInput(text=text),
                voice=texttospeech.VoiceSelectionParams(language_code=entry["language_code"], name=entry["voice"]),
                audio_config=texttospeech.AudioConfig(**cfg))
        except Exception as exc:  # noqa: BLE001
            if type(exc).__name__ in {"ResourceExhausted", "ServiceUnavailable", "TooManyRequests", "InternalServerError", "DeadlineExceeded"}:
                raise RetryableError(type(exc).__name__) from exc
            raise
        return r.audio_content
    return synth


def _azure_provider(env: dict):
    import httpx
    from xml.sax.saxutils import escape
    region, key = env["AZURE_SPEECH_REGION"], env["AZURE_SPEECH_KEY"]
    state = {"tok": None, "at": 0.0}

    def token() -> str:
        if not state["tok"] or time.time() - state["at"] > 540:
            r = httpx.post(f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken",
                           headers={"Ocp-Apim-Subscription-Key": key}, timeout=15)
            _raise_http(r)
            state.update(tok=r.text, at=time.time())
        return state["tok"]

    def synth(text: str, entry: dict) -> bytes:
        loc = entry["language_code"]
        ssml = (f"<speak version='1.0' xml:lang='{loc}'><voice xml:lang='{loc}' name='{entry['voice']}'>"
                f"{escape(text)}</voice></speak>")
        r = httpx.post(f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
                       content=ssml.encode("utf-8"),
                       headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/ssml+xml",
                                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3", "User-Agent": "LingoSquared"},
                       timeout=30)
        _raise_http(r)
        return r.content
    return synth


GEMINI_STYLE = ("Speak clearly at a natural, moderate pace, like a language teacher modelling the sentence. "
                "Read the text exactly as written, adding nothing.")


def _gemini_provider(env: dict):
    import base64
    import httpx
    key = env["GEMINI_API_KEY"]
    hdr = {"x-goog-api-key": key, "Content-Type": "application/json"}
    resolved: dict[str, str] = {}

    def voice_for(entry: dict) -> str:
        v = entry["voice"]
        if not v.startswith("voices-api:"):
            return v
        lc = v.split(":", 1)[1]
        if lc not in resolved:
            r = httpx.get("https://generativelanguage.googleapis.com/v1beta/voices", params={"language_code": lc},
                          headers=hdr, timeout=30)
            _raise_http(r)
            found = r.json().get("voices") or []
            if not found:
                raise RuntimeError(f"Gemini voice library returned no voices for {lc}; pick a prebuilt voice in voices.json")
            resolved[lc] = found[0].get("id") or found[0].get("name")
            print(f"  gemini voice for {lc}: {resolved[lc]}", file=sys.stderr)
        return resolved[lc]

    def synth(text: str, entry: dict) -> bytes:
        body = {"model": entry.get("model", "gemini-3.8-flash-lite-tts"),
                "input": [{"type": "user_input", "content": [{"type": "text", "text": text,
                           "annotations": [{"type": "speech_metadata", "style": GEMINI_STYLE}]}]}],
                "response_format": {"type": "audio"},
                "generation_config": {"speech_config": [{"voice": voice_for(entry)}]}}
        r = httpx.post("https://generativelanguage.googleapis.com/v1beta/interactions", json=body, headers=hdr, timeout=120)
        _raise_http(r)
        blocks = [c for s in r.json().get("steps", []) if s.get("type") == "model_output"
                  for c in s.get("content", []) if c.get("type") == "audio"]
        if not blocks:
            raise RuntimeError("Gemini returned no audio block")
        wav = base64.b64decode(blocks[-1]["data"])
        return wav_to_mp3(wav)
    return synth


def wav_to_mp3(wav: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        src, dst = Path(td, "in.wav"), Path(td, "out.mp3")
        src.write_bytes(wav)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "24000",
                        "-codec:a", "libmp3lame", "-b:a", "48k", str(dst)], check=True)
        return dst.read_bytes()


def build_providers(env: dict) -> dict[str, Callable[[str, dict], bytes]]:
    """Lazy: a provider is constructed on first use so missing creds only matter for languages you render."""
    makers = {"google": ("GOOGLE_CLOUD_TTS_CREDENTIALS_JSON", _google_provider),
              "azure": ("AZURE_SPEECH_KEY", _azure_provider), "gemini": ("GEMINI_API_KEY", _gemini_provider)}
    cache: dict[str, Callable] = {}

    class Lazy(dict):
        def __missing__(self, name):
            var, mk = makers[name]
            if not env.get(var):
                raise RuntimeError(f"{var} is not set")
            cache[name] = mk(env)
            return cache[name]
    return Lazy()


def with_backoff(fn: Callable[[], bytes], *, retries: int = 6, base: float = 2.0, sleep=time.sleep) -> bytes:
    for attempt in range(retries + 1):
        try:
            return fn()
        except RetryableError as exc:
            if attempt == retries:
                raise
            wait = exc.retry_after if exc.retry_after else min(base * 2 ** attempt, 120) * (0.5 + random.random())
            print(f"  rate limited/transient ({exc}); retry {attempt + 1}/{retries} in {wait:.1f}s", file=sys.stderr)
            sleep(wait)
    raise AssertionError("unreachable")


# --------------------------------------------------------------------------- render

def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def run(args, providers=None, env: dict | None = None, sleep=time.sleep, out=print) -> int:
    env = load_env(args.env_file) if env is None else env
    voices = ap.load_voices(args.voices)
    langs = set(args.lang.split(",")) if args.lang else None
    raw, stats = collect(langs=langs)
    plan = prepare(raw, voices)
    out_dir: Path = args.out_dir
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    ledger_path = out_dir / "usage.json"
    ledger = load_json(ledger_path, {})
    used = ledger.get(month, {})

    report(plan, voices, out_dir, env, args.max_chars, used)
    if stats["dynamic_practice_frames_skipped"]:
        print(f"note: {stats['dynamic_practice_frames_skipped']} practice frames with {{slots}} are generated per request; "
              "they are not pre-rendered (they fall back to /tts).")
    if args.dry_run:
        return 0
    if not args.max_chars:
        print("refusing to render without --max-chars N (hard character budget for this run)", file=sys.stderr)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    manifest = load_json(manifest_path, {"version": 1, "entries": {}})
    providers = providers if providers is not None else build_providers(env)
    spent, rendered, failures = 0, 0, 0
    last_call: dict[str, float] = {}

    def save():
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True).encode())
        ledger[month] = used
        _atomic_write(ledger_path, json.dumps(ledger, indent=1, sort_keys=True).encode())

    stop = False
    try:
        for lang, items in plan.items():
            entry = voices["languages"][lang]
            ok, why = provider_available(entry, env)
            if not ok:
                print(f"SKIP {lang}: {why}. No audio rendered for {lang}; the app keeps falling back to /tts or browser speech.")
                continue
            tier = voices["tiers"][entry["tier"]]
            for key, rec in items.items():
                path = out_dir / f"{key}.mp3"
                if path.is_file():
                    manifest["entries"].setdefault(key, _entry(key, lang, entry, voices, rec, path))
                    continue
                if spent + rec["chars"] > args.max_chars:
                    print(f"STOP: --max-chars {args.max_chars} reached after {spent} chars; rerun to resume.")
                    stop = True
                    break
                free = tier["free_chars_per_month"]
                if free is not None and not args.allow_paid and used.get(entry["tier"], 0) + rec["chars"] > free:
                    print(f"STOP {lang}: {entry['tier']} free allowance ({free}) for {month} would be exceeded; "
                          "rerun next month or pass --allow-paid.")
                    break
                gap = MIN_INTERVAL.get(entry["provider"], 0) - (time.time() - last_call.get(entry["provider"], 0))
                if gap > 0:
                    sleep(gap)
                try:
                    audio = with_backoff(lambda: providers[entry["provider"]](rec["text"], entry), sleep=sleep)
                except Exception as exc:  # noqa: BLE001
                    failures += 1
                    print(f"FAIL {lang} {key}: {exc}", file=sys.stderr)
                    if failures >= args.max_failures:
                        print("too many failures, aborting", file=sys.stderr)
                        stop = True
                        break
                    continue
                last_call[entry["provider"]] = time.time()
                _atomic_write(path, audio)
                spent += rec["chars"]; rendered += 1
                used[entry["tier"]] = used.get(entry["tier"], 0) + rec["chars"]
                manifest["entries"][key] = _entry(key, lang, entry, voices, rec, path)
                if rendered % 25 == 0:
                    save()
            if stop:
                break
    finally:
        save()
    print(f"done: rendered={rendered} chars={spent} failures={failures} out={out_dir}")
    return 1 if failures else 0


def _entry(key, lang, entry, voices, rec, path: Path) -> dict:
    return {"file": f"{key}.mp3", "language": lang, "provider": entry["provider"], "voice": entry["voice"],
            "rate": voices["render_rate"], "text": rec["text"], "chars": rec["chars"], "bytes": path.stat().st_size,
            "flags": rec["flags"], "rendered_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}


def check_voices(env: dict, voices: dict) -> int:
    """Free list-voices calls: confirm every configured voice name exists before spending anything."""
    bad = 0
    if env.get("GOOGLE_CLOUD_TTS_CREDENTIALS_JSON"):
        from google.cloud import texttospeech
        from google.oauth2 import service_account
        client = texttospeech.TextToSpeechClient(credentials=service_account.Credentials.from_service_account_info(
            json.loads(env["GOOGLE_CLOUD_TTS_CREDENTIALS_JSON"])))
        names = {v.name for v in client.list_voices().voices}
        for lang, e in voices["languages"].items():
            if e["provider"] == "google":
                ok = e["voice"] in names
                bad += not ok
                print(f"google {lang:3} {e['voice']:28} {'ok' if ok else 'MISSING'}")
    else:
        print("google: GOOGLE_CLOUD_TTS_CREDENTIALS_JSON not set, not checked")
    if env.get("AZURE_SPEECH_KEY"):
        import httpx
        r = httpx.get(f"https://{env['AZURE_SPEECH_REGION']}.tts.speech.microsoft.com/cognitiveservices/voices/list",
                      headers={"Ocp-Apim-Subscription-Key": env["AZURE_SPEECH_KEY"]}, timeout=30)
        names = {v["ShortName"] for v in r.json()}
        for lang, e in voices["languages"].items():
            if e["provider"] == "azure":
                ok = e["voice"] in names
                bad += not ok
                print(f"azure  {lang:3} {e['voice']:28} {'ok' if ok else 'MISSING'}")
    else:
        print("azure: AZURE_SPEECH_KEY not set, not checked")
    if env.get("GEMINI_API_KEY"):
        import httpx
        r = httpx.get("https://generativelanguage.googleapis.com/v1beta/voices", params={"language_code": "fa-AF"},
                      headers={"x-goog-api-key": env["GEMINI_API_KEY"]}, timeout=30)
        print(f"gemini fa-AF voice library: HTTP {r.status_code}, {len((r.json() if r.ok else {}).get('voices') or [])} voices")
    else:
        print("gemini: GEMINI_API_KEY not set, prs would be skipped")
    return 1 if bad else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="count characters per language/provider vs free allowance; no network")
    p.add_argument("--lang", help="comma-separated target languages (default: all)")
    p.add_argument("--max-chars", type=int, help="hard cap on characters rendered in this run (required to render)")
    p.add_argument("--out-dir", type=Path, default=Path(os.environ.get("MEDIA_AUDIO_DIR") or Path.home() / "lingosquared-media" / "audio"))
    p.add_argument("--voices", type=Path, default=None, help="voices.json (default: packages/shared/src/audio/voices.json)")
    p.add_argument("--env-file", type=Path, default=REPO_ROOT / "backend" / ".env")
    p.add_argument("--allow-paid", action="store_true", help="allow exceeding a tier's monthly free allowance")
    p.add_argument("--max-failures", type=int, default=10)
    p.add_argument("--check-voices", action="store_true")
    args = p.parse_args(argv)
    if args.check_voices:
        return check_voices(load_env(args.env_file), ap.load_voices(args.voices))
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
