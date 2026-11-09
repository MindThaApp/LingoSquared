"""Tests for the compiled Russian-block Latin-script checker."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _cyrillic_latin_check as chk  # noqa: E402


def test_main_counts_latin_hits_and_compile_failures(tmp_path, monkeypatch, capsys):
    content = tmp_path / "content"
    (content / "overlays" / "en-ru").mkdir(parents=True)
    monkeypatch.setattr(chk.dc, "CONTENT", content)
    monkeypatch.setattr(chk.dc.dd, "MANIFEST", tmp_path / "manifest")
    monkeypatch.setattr(chk.dc.dd, "read_manifest", lambda _: {
        "en-ru-a1": (["real-a1"], ["overlay-a1"]),
        "en-ru-a2": (["real-a2"], ["overlay-a2"]),
    })

    def run(command, **kwargs):
        return SimpleNamespace(returncode=1 if "real-a2" in command else 0)

    monkeypatch.setattr(chk.subprocess, "run", run)
    monkeypatch.setattr(chk.dc, "latin_in_cyrillic", lambda *_: ["Latin word"])
    monkeypatch.setattr(sys, "argv", ["check", "--pairs", "en-ru"])

    assert chk.main() == 1
    output = capsys.readouterr().out
    assert "cyrillic-latin en-ru-a1: 1" in output
    assert "en-ru-a2: compile failed" in output
    assert "cyrillic-latin total: 2" in output


def test_main_returns_zero_for_clean_compile(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(chk.dc.dd, "MANIFEST", tmp_path / "manifest")
    monkeypatch.setattr(chk.dc.dd, "read_manifest", lambda _: {
        "de-ru": (["real"], ["overlay"]),
    })
    monkeypatch.setattr(chk.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0))
    monkeypatch.setattr(chk.dc, "latin_in_cyrillic", lambda *_: [])
    monkeypatch.setattr(sys, "argv", ["check", "--pairs", "de-ru"])
    assert chk.main() == 0
    assert "cyrillic-latin total: 0" in capsys.readouterr().out
