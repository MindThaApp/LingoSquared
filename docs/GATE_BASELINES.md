# Daily-ship gate baselines (set 2026-10-30)

Run from a clean checkout of the commit to ship. All must hold or the ship stops.

| Gate | Threshold |
|---|---|
| `scripts/verify.sh --content-only` | pass; WARN count (lines starting `WARN`, full run) <= formula below |
| `scripts/_answer_leakage_check.py` | <= 36 hits (32 at 4fc57331f, 13 more allowlisted in `scripts/_answer_leakage_allowlist.tsv`) |
| german / dutch / cross leftover | 0 |
| practice-validate (all packs) | 0 errors |
| `pytest scripts/tests` | pass (170 at 4fc57331f) |
| backend pytest (repo mounted, `test_content_answer_shapes` deselected) | pass |
| vitest (`VITE_API_BASE_URL=http://localhost:8000`) | pass (461) |

## WARN baseline

740 for all pre-existing courses (server state 1cca942a0; no pre-existing course may gain a WARN)
plus, for every cross pair (non-en learner language X -> target Y), the per-course WARN count of its
`en-Y` sibling, because the en->Y realization warnings are re-reported once per learner-language pair:

- target es: +138 each (de-es, fr-es, it-es)
- target fr: +112 each (de-fr, es-fr, it-fr)
- target de: +4 each (es-de, it-de, fr-de)
- target it (A1): +8 each (de-it, fr-it); es-it-a1 is +10 (two extra cognate false positives)

Measured at 4fc57331f: 740 + 3x138 + 3x112 + 3x4 + 2x8 + 10 = 1528.
When a new cross pair merges, add its `en-Y` sibling count; verify no pre-existing course changed.
