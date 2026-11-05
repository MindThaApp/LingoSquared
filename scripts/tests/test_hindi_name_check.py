"""Tests for scripts/_hindi_name_check.py (one Devanagari spelling per person name)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _hindi_name_check as hn  # noqa: E402


def test_skeleton_ignores_length_nukta_and_chandrabindu():
    assert hn.skeleton("नीना") == hn.skeleton("निना")
    assert hn.skeleton("फ़ेना") == hn.skeleton("फेना")
    assert hn.skeleton("लोटे") == hn.skeleton("लॉटे")


def test_table_is_consistent():
    std, rej = hn.load()
    assert "नीना" in std and rej["निना"] == "नीना"
    assert not set(std) & set(rej)            # a spelling is never both standard and rejected
    assert all(g in std for g in rej.values())


def test_content_has_one_spelling_per_name(capsys):
    assert hn.main() == 0, capsys.readouterr().out
