# Daily-ship gate baselines (set 2026-10-30)

Run from a clean checkout of the commit to ship. All must hold or the ship stops.

| Gate | Threshold |
|---|---|
| `scripts/verify.sh --content-only` | pass; WARN count (lines starting `WARN`, full run) <= formula below |
| `scripts/_answer_leakage_check.py` | <= 36 hits (17 at a6f9f44ec, 31 at 69aaabfdb, 26 more allowlisted in `scripts/_answer_leakage_allowlist.tsv`) |
| german / dutch / cross leftover | 0 |
| practice-validate (all packs) | 0 errors |
| `pytest scripts/tests` | pass (187 at 294b3618b) |
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

- target nl: +56 each (de-nl, es-nl, fr-nl, it-nl; same as en-nl)
- nl-/pl-/ro- sources into de/es/fr/it follow the same per-target counts (de 4, es 138, fr 112, it-a1 8)

Known exceptions (not regressions; WARN-only cognate false positives on pair-side text):
- es-it-a1: +2 (en-it-a1 is 8, es-it-a1 is 10)
- ro-fr: +4 (116 vs en-fr 112: a1_unit04 match_price_phrases, a1_unit13 match_preference_phrases; validate+compile lines)

Measured at 69aaabfdb (shipped 2026-10-30): 2542 = 740 + 3x138 + 3x112 + 3x4 + 2x8 + 10 (to 4fc57331f: 1528)
+ 4x56 (nl targets) + nl/pl/ro cross pairs into de/es/fr/it + 4 (ro-fr exception). Ru cross pairs (#70-#73) were not part of this ship:
they were not gated (leakage 95 with them) and need their own leakage fix/allowlist first.
When a new cross pair merges, add its `en-Y` sibling count; verify no pre-existing course changed.

Measured at a6f9f44ec (shipped 2026-10-31): 3000 = 2542 + 7 x 20 (de/es/fr/it/nl/pl/ro -> ru, each equals en-ru-a1's 20)
+ 318 for ru -> X (ru-es 138, ru-fr 112, ru-de 4, ru-nl 56, ru-it-a1 8). en-ru unchanged by #85 (a1 20, a2 2, b1 10, c1 2);
no pre-existing course changed. The de/nl realization compile WARNs count (they are the en-de 4 / en-nl 56 siblings).
Leakage 17 hits (29 allowlisted); cyrillic-latin 0; 67 practice packs 0 errors.

Measured at d9d564b64 (shipped 2026-10-31, second ship): 3060 = 3000 + 6 x 10 (de/es/fr/it/nl/pl -> ro, each equals en-ro's 10;
en-ro is 10, not 5). en-ro (10) and en-de (4) unchanged by #87 versus a6f9f44ec; no pre-existing course changed.
Leakage 17 hits (29 allowlisted); cyrillic-latin 0; leftovers 0; all practice packs 0 errors; scripts/tests 181; vitest 461.
Current WARN baseline: 3060 (superseded below).

Measured at 294b3618b (shipped 2026-10-31, third ship): 3750 = 3060 + ru-ro 10 + 7 X-pl x 16 (de/es/fr/it/nl/ro/ru -> pl, each equals en-pl's 16)
+ 4 es-target x 138 (hi-es, ar-es, fa-es, prs-es) + 4 de-target x 4 (hi-de, ar-de, fa-de, prs-de). Per-course diff versus d9d564b64: only the 16 new
courses appear; en-pl, en-de, en-es and every other pre-existing course unchanged. Leakage 22 hits (29 allowlisted); cyrillic-latin 0;
leftovers 0; check_dari_register 0 findings; 89 practice packs 0 errors; scripts/tests 187; vitest 461; backend pytest pass.
Current WARN baseline: 3750.
