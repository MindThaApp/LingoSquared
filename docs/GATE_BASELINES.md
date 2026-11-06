# Daily-ship gate baselines (set 2026-10-30)

Run from a clean checkout of the commit to ship. All must hold or the ship stops.

| Gate | Threshold |
|---|---|
| `scripts/verify.sh --content-only` | pass; WARN line count (full run) <= baseline below |
| `scripts/_answer_leakage_check.py` | <= 13 hits (ci_local.sh hard limit 36; 91 allowlisted in `scripts/_answer_leakage_allowlist.tsv`) |
| german / dutch / cross leftover | 0 |
| `scripts/_note_language_check.py` (English in grammar-note target spans / untranslated note titles; baseline `scripts/_note_language_baseline.tsv` may only shrink) | 0 new, 0 stale |
| `scripts/_cyrillic_latin_check.py`, `scripts/check_dari_register.py` | 0 findings |
| `scripts/_target_name_check.py` (wrong language name in cross-pair overlays/practice; allowlist `scripts/_target_name_allowlist.tsv`) | 0 hits |
| `scripts/_hindi_name_check.py` (one Devanagari spelling per person name, and no Latin-script person name inside Hindi text; table `scripts/_hindi_names.tsv`, exceptions `scripts/_hindi_latin_name_allowlist.tsv`; `scripts/_hindi_latin_names_fix.py` converts new content) | 0 findings |
| practice-validate (all packs) | 0 errors |
| `pytest scripts/tests` | pass (217 at e7eaf91c4) |
| backend pytest (repo mounted, full suite including `test_content_answer_shapes`) | pass |
| vitest (`VITE_API_BASE_URL=http://localhost:8000`) | pass (492) |

## WARN baseline

Counting method (one method, used everywhere): the WARN count is the number of log lines starting with `WARN`
in the full `scripts/verify.sh --content-only` output, exactly what `scripts/ci_local.sh` prints as "WARN lines".
Realization warnings are printed twice (validate pass + compile pass), so each realization WARN is 2 lines;
practice-pack WARNs (e.g. the ambiguity-check "could not load lexeme data" line) are printed once, 1 line.
Older entries below that quote a per-course "validate count" are half of the line counts used here; all numbers in
this section are lines.

Current baseline: 5486 lines (shipped 2026-11-05, content at e7eaf91c4 plus #172/#173) = 5046 + 440:
- 5046: acfde1144 (the previous ship), unchanged: the per-course diff acfde1144 vs e7eaf91c4 shows no pre-existing course
  gained or lost a WARN (#169, #170, #171 and the other merges changed no WARN).
- +440: the 20 new courses' realization WARNs, each equal to its `en-Y` sibling line count:
  nl/pl/ro/ru -> ar-a1 4 x 56 = 224; -> hi 4 x 8 = 32; -> prs 4 x 38 = 152; de/es/fr/it/nl/pl/ro/ru -> fa 8 x 4 = 32.
- The gate run at e7eaf91c4 showed 5494: 8 extra single-line practice WARNs ("could not load lexeme data for ambiguity check ...
  missing X gloss for 'تنبل نیست (he/she is not lazy)'", one per X-fa pack). Cause: #165 changed that fa unit36 card text but the 8
  X-fa lexicons kept the old key, which also made `backfill_lexemes_<X>_fa.py` fail during the deploy. Fixed in #173 (key renamed,
  all 8 packs validate with 0 warnings), so the baseline is 5486. Not a content regression of any pre-existing course.

Cross-pair rule (lines per new learner-language X -> target Y course = line count of `en-Y`, plus any practice WARN lines of the new pack):
es 138, fr 112, de 4, it-a1 8, nl 56, ru-a1 20, pl 16, ro 10, ar-a1 56, hi 8, prs 38, fa 4.
Known exceptions: es-it-a1 +2 (cognate false positives), ro-fr +4. A new cross pair adds its `en-Y` sibling count;
verify with a per-course diff against a verify run of the previous shipped commit that no pre-existing course changed.

C1 tiers (en-fa-c1 and en-prs-c1; 8 units each, built from the same discourse-move template as en-ar-c1): each validate and compile with 0 errors and 0 warnings, as does its sibling en-ar-c1, so the WARN baseline does not move (5486 stays). A new course adds 0 lines; no pre-existing course changed.

History (lines): 740 pre-existing courses at 1cca942a0; 2542 at 69aaabfdb; 3000 at a6f9f44ec; 3060 at d9d564b64; 3750 at 294b3618b;
4230 at 53bec4a11; 4534 at 76a2dd9c5; 4638 at 20b648c90; 5046 at acfde1144 (de/es/fr/it -> ar-a1 4x56, -> hi 4x8, -> prs 4x38);
5486 at e7eaf91c4 + #172/#173 (5494 before #173).

Other gates at e7eaf91c4: leakage 13 hits (91 allowlisted); german/dutch/cross leftover, cyrillic-latin, target-name, hindi-name,
check_dari_register 0; note-language 0 hit(s) (baseline emptied); practice packs 0 errors; scripts/tests 217; vitest 492;
backend pytest full suite pass (test_content_answer_shapes included, deselect removed in #172); frontend lint and build pass.

## Running all gates locally

`scripts/ci_local.sh` runs every gate above in one command (content verify, leakage, scripts pytest, backend pytest in an isolated compose project `lsci_<pid>` that is torn down on exit, vitest). Flags: `--skip-backend`, `--skip-frontend`, `--skip-content`, `--with-build`; `CI_WARN_MAX=<n>` enforces the WARN formula. Content verify takes about an hour; use `--skip-content` for code-only changes. GitHub Actions (`.github/workflows/ci.yml`) runs the same gates on pushes and PRs for the integration branch.

Group D (ar/fa/hi/prs among themselves): each new X-Y pair adds its en-Y sibling count (ar 28, fa 2, hi 4, prs 19). Batch 1: ar-fa +2, ar-hi +4, ar-prs +19 = +25. Batch 2: fa-ar +28, fa-hi +4, fa-prs +19, prs-ar +28 = +79. Batch 3: prs-fa +2, prs-hi +4 = +6.
fa-prs / prs-fa prompt==answer coincidences are reported by `_answer_leakage_check.py` separately and are not counted against the leakage threshold.
