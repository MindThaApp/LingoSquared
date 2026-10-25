"""Pre-rendered audio: hashing, render script (mocked providers), serving path."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest
import yaml

from app.core.config import get_settings
from app.services import audio_prerender as ap

# The backend image only has backend/; script-level tests need the repo mounted
# (same convention as test_content_answer_shapes: LINGO_REPO_ROOT=/repo).
REPO = Path(os.environ.get("LINGO_REPO_ROOT") or Path(__file__).resolve().parents[2])
SCRIPT = REPO / "scripts" / "render_audio.py"
needs_repo = pytest.mark.skipif(not SCRIPT.is_file(), reason="repo root not mounted (set LINGO_REPO_ROOT)")


@pytest.fixture(scope="module")
def ra():
    if not SCRIPT.is_file():
        pytest.skip("repo root not mounted (set LINGO_REPO_ROOT)")
    spec = importlib.util.spec_from_file_location("render_audio_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# --- hashing -----------------------------------------------------------------

def test_hash_vectors_match_frontend():
    # Same vector as frontend/src/lib/audioKey.test.ts
    assert ap.audio_key("google", "en-US-Neural2-C", "en", "Hello  world", "1.00") == "18ab77b27d268b236c607e04aca81acb"


def test_hash_is_deterministic_and_sensitive_to_every_field():
    base = ap.audio_key("google", "v", "nl", "hallo", "1.00")
    assert ap.audio_key("google", "v", "nl", "hallo", "1.00") == base
    assert len(base) == 32
    for variant in (("azure", "v", "nl", "hallo", "1.00"), ("google", "w", "nl", "hallo", "1.00"),
                    ("google", "v", "en", "hallo", "1.00"), ("google", "v", "nl", "hallo!", "1.00"),
                    ("google", "v", "nl", "hallo", "0.75")):
        assert ap.audio_key(*variant) != base


def test_normalization_collapses_whitespace_and_composes_unicode():
    assert ap.normalize_text("  é  x\n") == "é x"
    assert ap.audio_key("p", "v", "fr", "café", "1.00") == ap.audio_key("p", "v", "fr", "café", "1.00")


@needs_repo
def test_voices_config_is_complete():
    voices = ap.load_voices()
    for lang, entry in voices["languages"].items():
        assert entry["tier"] in voices["tiers"], lang
        assert voices["tiers"][entry["tier"]]["provider"] == entry["provider"], lang
    assert voices["tiers"]["google-wavenet"]["free_chars_per_month"] == 1_000_000
    assert voices["languages"]["fa"]["provider"] == "azure"
    assert voices["languages"]["prs"]["requires_env"] == "GEMINI_API_KEY"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
@needs_repo
def test_python_sanitizer_matches_the_frontend_sanitizer():
    samples = ["Lotte: Hoi, ik ben Lotte. Omar: Ik heet Omar.", "Bent ___ nieuw hier?", "Dit (gloss) is [een] test -> ja",
               "10:30 uur", "من: سلام نام من مینا است.",
               "Let op: dit blijft", "Meine Frage: Wo? Antwort: Hier."]
    js = ("import {sanitizeForSpeech as s} from '%s';"
          "const a=JSON.parse(process.argv[1]);console.log(JSON.stringify(a.map(s)))"
          % (REPO / "frontend/src/lib/sanitizeForSpeech.ts"))
    res = subprocess.run(["node", "--input-type=module", "-e", js, json.dumps(samples)], capture_output=True, text=True)
    if res.returncode != 0:
        pytest.skip(f"node cannot import TS here: {res.stderr[:200]}")
    assert [ap.sanitize_for_speech(t) for t in samples] == json.loads(res.stdout)


# --- render script ------------------------------------------------------------

def _content(tmp_path, ra, monkeypatch, nl=("Hallo", "Goedemorgen"), ar=("مرحبا", "مَرْحَباً"), prs=("سلام",)):
    real = tmp_path / "realizations"
    for lang, texts in (("nl", nl), ("ar", ar), ("prs", prs)):
        d = real / lang
        d.mkdir(parents=True)
        data = {"media_assets": [{"content_key": f"{lang}.{i}", "language": lang, "text": t} for i, t in enumerate(texts)],
                "units": [{"lessons": [{"teaching": [{"target": {"text": texts[0], "language_code": lang}, "introduced_tokens": [texts[0]]}],
                                        "exercises": [{"type": "listen_select", "tested_text": texts[-1]}]}]}]}
        (d / "a1.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    pr = tmp_path / "practice" / "en-nl"
    pr.mkdir(parents=True)
    (pr / "u1.yaml").write_text(yaml.safe_dump({"templates": [
        {"frame": {"text": "Ben {item} nieuw?", "language_code": "nl"}},
        {"frame": {"text": "Ik heet Noor.", "language_code": "nl"}}]}, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(ra, "REALIZATIONS_DIR", real)
    monkeypatch.setattr(ra, "PRACTICE_DIR", tmp_path / "practice")


def _args(tmp_path, **kw):
    base = dict(dry_run=False, lang=None, max_chars=10_000, out_dir=tmp_path / "out", voices=None,
                env_file=None, allow_paid=False, max_failures=3, check_voices=False)
    base.update(kw)
    return Namespace(**base)


class FakeProviders(dict):
    def __init__(self):
        super().__init__()
        self.calls = []
        for name in ("google", "azure", "gemini"):
            self[name] = (lambda n: (lambda text, entry: self.calls.append((n, entry["voice"], text)) or b"ID3" + text.encode()))(name)


def test_collect_matches_what_the_frontend_requests(ra, tmp_path, monkeypatch):
    _content(tmp_path, ra, monkeypatch)
    raw, stats = ra.collect()
    assert set(raw["nl"]) == {"Hallo", "Goedemorgen", "Ik heet Noor."}  # slot frame skipped, frame without slots kept
    assert stats["dynamic_practice_frames_skipped"] == 1
    plan = ra.prepare(raw, ap.load_voices())
    assert {r["text"] for r in plan["nl"].values()} == {"Hallo", "Goedemorgen", "Ik heet Noor."}


def test_dry_run_prints_counts_and_writes_nothing(ra, tmp_path, monkeypatch, capsys):
    _content(tmp_path, ra, monkeypatch)
    rc = ra.run(_args(tmp_path, dry_run=True), env={})
    out = capsys.readouterr().out
    assert rc == 0
    assert "google-wavenet" in out and "FITS" in out
    nl_line = next(l for l in out.splitlines() if l.startswith("nl "))
    assert str(len("Hallo") + len("Goedemorgen") + len("Ik heet Noor.")) in nl_line
    assert not (tmp_path / "out").exists()


def test_prs_is_skipped_without_a_gemini_key(ra, tmp_path, monkeypatch, capsys):
    _content(tmp_path, ra, monkeypatch)
    fake = FakeProviders()
    ra.run(_args(tmp_path), providers=fake, env={}, sleep=lambda s: None)
    out = capsys.readouterr().out
    assert "SKIP prs: GEMINI_API_KEY is not set" in out
    assert all(c[0] != "gemini" for c in fake.calls)
    fake2 = FakeProviders()
    ra.run(_args(tmp_path, out_dir=tmp_path / "out2"), providers=fake2, env={"GEMINI_API_KEY": "k"}, sleep=lambda s: None)
    assert any(c[0] == "gemini" for c in fake2.calls)


def test_render_is_idempotent_and_resumable(ra, tmp_path, monkeypatch):
    _content(tmp_path, ra, monkeypatch)
    first = FakeProviders()
    assert ra.run(_args(tmp_path, lang="nl"), providers=first, env={}, sleep=lambda s: None) == 0
    out = tmp_path / "out"
    files = sorted(p.name for p in out.glob("*.mp3"))
    assert len(files) == 3 and len(first.calls) == 3
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["entries"]) == {f[:-4] for f in files}
    hallo = ap.file_name_for(ap.load_voices(), "nl", "Hallo")
    assert hallo in files and manifest["entries"][hallo[:-4]]["text"] == "Hallo"
    second = FakeProviders()
    ra.run(_args(tmp_path, lang="nl"), providers=second, env={}, sleep=lambda s: None)
    assert second.calls == []  # nothing re-rendered
    # changed text -> only the new string renders
    _content(tmp_path / "v2", ra, monkeypatch, nl=("Hallo", "Goedemorgen", "Nieuw"))
    third = FakeProviders()
    ra.run(_args(tmp_path, lang="nl"), providers=third, env={}, sleep=lambda s: None)
    assert [c[2] for c in third.calls] == ["Nieuw"]


def test_max_chars_is_a_hard_cap_and_required(ra, tmp_path, monkeypatch, capsys):
    _content(tmp_path, ra, monkeypatch)
    assert ra.run(_args(tmp_path, max_chars=None), providers=FakeProviders(), env={}) == 2
    fake = FakeProviders()
    ra.run(_args(tmp_path, lang="nl", max_chars=12), providers=fake, env={}, sleep=lambda s: None)
    assert sum(len(c[2]) for c in fake.calls) <= 12
    assert "STOP: --max-chars 12" in capsys.readouterr().out
    # resuming with a bigger cap finishes the rest without redoing the first
    fake2 = FakeProviders()
    ra.run(_args(tmp_path, lang="nl", max_chars=1000), providers=fake2, env={}, sleep=lambda s: None)
    assert len(fake.calls) + len(fake2.calls) == 3


def test_free_tier_guard_stops_unless_paid_allowed(ra, tmp_path, monkeypatch, capsys):
    _content(tmp_path, ra, monkeypatch)
    out = tmp_path / "out"
    out.mkdir()
    month = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m")
    (out / "usage.json").write_text(json.dumps({month: {"google-wavenet": 999_999}}))
    fake = FakeProviders()
    ra.run(_args(tmp_path, lang="nl"), providers=fake, env={}, sleep=lambda s: None)
    assert fake.calls == [] and "free allowance" in capsys.readouterr().out
    ra.run(_args(tmp_path, lang="nl", allow_paid=True), providers=fake, env={}, sleep=lambda s: None)
    assert len(fake.calls) == 3


def test_arabic_without_tashkeel_is_flagged_but_rendered_as_is(ra, tmp_path, monkeypatch):
    _content(tmp_path, ra, monkeypatch)
    plan = ra.prepare(ra.collect(langs={"ar"})[0], ap.load_voices())["ar"]
    flags = {r["text"]: r["flags"] for r in plan.values()}
    assert flags["مرحبا"] == ["arabic_no_tashkeel"]
    assert flags["مَرْحَباً"] == []
    fake = FakeProviders()
    ra.run(_args(tmp_path, lang="ar"), providers=fake, env={}, sleep=lambda s: None)
    assert "مرحبا" in {c[2] for c in fake.calls}  # text untouched


def test_backoff_retries_rate_limits_then_gives_up(ra):
    sleeps, attempts = [], []

    def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise ra.RetryableError("429", retry_after=1.5)
        return b"ok"

    assert ra.with_backoff(flaky, sleep=sleeps.append) == b"ok"
    assert sleeps == [1.5, 1.5]

    def always():
        raise ra.RetryableError("503")

    with pytest.raises(ra.RetryableError):
        ra.with_backoff(always, retries=2, sleep=lambda s: None)


# --- serving path -------------------------------------------------------------

def test_api_serves_prerendered_clip_with_immutable_cache(client, tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "media_audio_dir", str(tmp_path))
    name = ap.audio_key("google", "nl-NL-Wavenet-F", "nl", "Hallo", "1.00") + ".mp3"
    (tmp_path / name).write_bytes(b"ID3fake")
    res = client.get(f"/media/audio/{name}")
    assert res.status_code == 200
    assert res.content == b"ID3fake"
    assert res.headers["content-type"] == "audio/mpeg"
    assert "immutable" in res.headers["cache-control"]


@pytest.mark.parametrize("bad", ["../../etc/passwd", "short.mp3", "g" * 32 + ".mp3", ("a" * 32) + ".wav", ("A" * 32) + ".mp3"])
def test_api_rejects_bad_or_missing_audio_names(client, tmp_path, monkeypatch, bad):
    monkeypatch.setattr(get_settings(), "media_audio_dir", str(tmp_path))
    assert client.get(f"/media/audio/{bad}").status_code in (404, 405)
    assert client.get("/media/audio/" + "a" * 32 + ".mp3").status_code == 404


def test_default_tts_budget_reflects_the_one_million_free_tier():
    assert type(get_settings()).model_fields["tts_monthly_char_budget"].default == 1_000_000
