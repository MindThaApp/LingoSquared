# Fresh-context review — 13 unreviewed prs (Dari) draft units (2026-08-02)

Three fresh-context reviews (zero authoring context) over the 13 `status: unreviewed`
en-prs realizations + overlays: a1_unit19; a2 units 11–18; b1 units 02–05. Scope was
STRUCTURAL/PEDAGOGICAL (the classes a green compile misses); Dari-language naturalness
was quarantined to native flags. All 13 compile clean and grade-corpus-clean already;
this pass adds the qualitative checks.

## Result
- **Structurally CLEAN (9):** a2_unit14, 15, 16, 17, 18; b1_unit02, 03, 04. (unit14
  already carried a review stamp.)
- **3 real grading defects — FIXED this session** (each fix only ADDS accepted variants
  built from the unit's OWN taught/modeled Dari, or rewords an English instruction — no
  new Dari authored, cannot break a passing case; all recompile 0 errors):
  1. `a1_unit19` `write_own_home_sentence` — accepted میز/چوکی دارم but NOT تخت/کلکین دارم
     though both are taught objects (lesson02). Added `تخت دارم`, `کلکین دارم`.
  2. `a2_unit11` `write_pin_summary` — instruction said "quoting the clerk" but the accepted
     answer is a first-person restatement and the feedback quoted a different string.
     Reworded instruction → "Restate the clerk's answer as a full sentence: when do you
     get the PIN?" (matches the accepted answer + feedback).
  3. `b1_unit05` reported-QUESTION exercises (l03 ex05/06/07, l06 ex05) — accepted only the
     `که`-bearing form, but the unit's grammar note marks `که` optional (`پرسید (که)`) and
     its own dialogue/reading model it WITHOUT `که`. Added the `که`-less variant to all four.

## Systemic / corpus-wide — NOT fixed (policy decision; mirror already-shipped b1_unit01)
Fixing only these 4 units would make them inconsistent with the rest of the shipped prs
corpus, so these need a corpus-wide call, not a per-unit edit:
- **S-1 Pro-drop single-answer.** Dari is pro-drop; some translate/write exercises accept
  only the pronoun-INCLUDED string, others only the pronoun-DROPPED string, none both
  (e.g. b1_unit02 l02 ex05 "آنها باید نان بخرن" vs ex06 "باید نان بخریم"). A learner using
  the other equally-valid pattern is marked wrong. Recurs across b1 02–05. Decision: accept
  both variants corpus-wide for pronoun-subject translate/write items.
- **S-2 dialogue_response terminal period.** Every `dialogue_response` accepts only a
  period-terminated string; prs grades exact with punctuation load-bearing, so omitting the
  final `.` grades wrong. Decision: add a period-less variant corpus-wide.
- **Untaught tokens in a2 comprehension prompt stems** (a2_11/12/13): Dari question words
  اسنادی/لازم/چقدر/چیزی/برای/کدام + a forward-ref مشکل appear in `prompt.target_blocks`
  before being taught. Mitigated (the English `instruction` duplicates each question) but
  not eliminated. Decision: teach these stems, or reword the Dari prompts (needs Dari).

## NATIVE-DARI FLAGS — route to the native pass (same reviewer as the gloss drafts)
- **Register split (corpus-wide):** these units use formal `می‌توانین`/`است`; the lane pin
  is colloquial `می‌تانین`/`استه`. Grep: `می‌تانین` in 10 files, `می‌توانین` in 8, `استه` in 0.
  A native must decide the canonical prs register and reconcile — this is the single biggest
  prs-wide item.
- Word-choice/idiom naturalness (تشناب/چوکی/کلکین, داکتر صاحب, اینه, به دلیل, ترجیح دادن,
  sequencing اول…بعد…در آخر), the و-joined conditional variant, embedded-question `؟`
  orthography, and grammar accuracy of the taught B1 forms (باید+subjunctive, اگر+باشد,
  گفت که / پرسید که reported speech). None ruled on — need native Dari judgment.

## Status
The 3 grading defects are fixed + committed. The 13 units are structurally reviewed;
they remain `unreviewed` in metadata pending the native-Dari pass (register + naturalness),
which — with no in-house Dari native — rides with the fa/prs gloss drafts the user is
routing to a native (`docs/FA_PRS_GLOSS_DRAFTS_a2_unit35-40.md`). The systemic S-1/S-2 items
are a corpus-wide grading-policy call.
