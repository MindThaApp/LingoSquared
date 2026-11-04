"""Grammar-note language check: English prose in a target-language note span, or an untranslated English note title."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _note_language_check as nl  # noqa: E402


class EnglishHits(unittest.TestCase):
    def test_polish_note_with_english_prose_is_flagged(self):
        text = "Proszę + bezokolicznik -- Proszę (please) plus a verb in the infinitive is the everyday polite way."
        self.assertTrue(nl.english_hits(text, "pl"))

    def test_polish_note_with_english_gloss_is_flagged(self):
        self.assertTrue(nl.english_hits("Gdzie (where) plus jest (is) pyta o lokalizację.", "pl"))

    def test_clean_polish_note_passes(self):
        text = "Jechać: jadę (ja), jedzie (on/ona). Jutro jadę do Krakowa. Marek jedzie do Krakowa."
        self.assertEqual(nl.english_hits(text, "pl"), [])

    def test_non_ascii_words_are_not_split(self):
        self.assertEqual(nl.english_hits("Jestem inżynierem. inżynier i nauczycielka zmieniają końcówkę.", "pl"), [])


class RepoState(unittest.TestCase):
    def test_no_new_or_stale_hits_in_repo_content(self):
        hits = {**nl.realization_hits(), **nl.title_hits()}
        baseline = {l for l in nl.BASELINE.read_text(encoding="utf-8").splitlines() if l.strip()}
        self.assertEqual(sorted(set(hits) - baseline), [])
        self.assertEqual(sorted(baseline - set(hits)), [])

    def test_polish_a1_notes_and_titles_are_clean(self):
        hits = {**nl.realization_hits(), **nl.title_hits()}
        self.assertEqual([k for k in hits if "pl.a1." in k], [])


if __name__ == "__main__":
    unittest.main()
