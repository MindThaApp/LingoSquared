"""german_markers: Polish "ich"/"wie" are Polish words, real German in a Polish overlay is still flagged."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import _german_leftover_check as g  # noqa: E402


def test_polish_ich_and_wie_are_not_german():
    assert not g.german_markers("Czytanie o ich pracy", "pl")
    assert not g.german_markers("Elena jeszcze nie wie", "pl")
    assert not g.german_markers("jej/jego/ich", "pl")


def test_real_german_in_polish_overlay_is_still_flagged():
    assert g.german_markers("Das ist nicht ein Beispiel", "pl")
    assert g.german_markers("Ich habe einen Hund und eine Katze", "es")
