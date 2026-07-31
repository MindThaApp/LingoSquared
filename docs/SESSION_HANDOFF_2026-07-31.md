# Session handoff — 2026-07-31 (burn-wave execution)

## Git state
- Branch: `fix/launch-gate-content-review-wave1` (NO upstream — nothing pushed).
- 6 commits ahead of `7fcea523`. **Do NOT push/merge/deploy without an explicit ask from Ramin.**
- Only pre-existing untracked/modified files remain in `git status` (a .pyc, repo `.claude/settings.json`, some docker-compose/env files) — none of them mine.

## What landed this session (all local commits)
Fixes: volume_translate debug-placeholder strip (37 packs); a2_30 untaught `qualified`
matching pair dropped (realization + 3 overlays synced); §12 contraction-expansion
accepted-answer variants (136 X-en gaps); `case_sensitive: true` on the 2 en-nl
capitalization MCQs (real grading bug — casefold accepted the capitalized distractor);
a1_02 `reply_as_leila` tested_text de-fused.
Docs: backlog session section + `docs/NATIVE_REVIEW_full_turn_instructions_2026-07-31.md`.

Verified clean (no churn): full `verify.sh` content stage = 0 err / 0 warn; `realizations/en`
a1_01–53 fresh 3-agent semantic review = NO DEFECTS; entire a2/b1/b2 English free-text set
(283 prompt/answer pairs) reviewed by hand = clean; deterministic MCQ / matching-pairs /
German Sie-sie audits = clean. Non-defects triaged (documented in backlog): dialogue_comprehension
empty target_blocks (all have audio), matching-pairs cognates/categorization, fa a1_11 wake-time.

## START HERE next session (limits now 1000 session / 30 concurrent after relaunch)
The **English content is verifiably clean** — do NOT re-review it. The un-reviewed, high-value,
parallelizable work is the **target-language overlays** (Dutch/Farsi/Dari/German/French/Italian
ANSWER + GLOSS correctness), ~400+ packs never agent-reviewed (I hit the 200-agent cap).

1. **Target-language overlay review fan-out.** Partition by direction × level; report-only
   (structured: file/ck/defect/evidence/fix + IN-LANE vs NATIVE flag). Fix English-side
   issues in-lane; queue target-language answer/gloss issues for native confirm. Directions:
   en-nl (88), en-fa (83), en-prs (82), en-de (54), en-it (53), en-fr (43), de-en (17).
   Prefer fewer/larger agents (~15 files each) — per-agent overhead is real.
2. **59 full-turn role-play instructions** — `docs/NATIVE_REVIEW_full_turn_instructions_2026-07-31.md`.
   fa-en/prs-en instructions under-specify the 3-turn answer → partial answers graded wrong.
   NATIVE-RESERVED (Farsi/Dari authoring) — do NOT author; confirm with Ramin or leave queued.
3. **German a1 capitalization** — free-text grading casefolds, so lowercase German nouns / "sie"
   for "Sie" pass. DESIGN DECISION for Ramin (opt de exercises into case_sensitive?), not a clear bug.

## Hard constraints (unchanged)
- Never push/merge/deploy without an explicit ask. Dev-DB/deploy owner-reserved.
- Do NOT author fa/prs sentences (native-reserved; single-word factual fixes confirmed by sibling
  files are OK). Dutch/German/French/Italian authoring is sensitive — prefer flag-and-queue.
- Grading + overlay mechanics that decide what's a real defect: see memory
  `reference_2026-07-31_grading-and-overlay-mechanics` (free-text graded ONLY vs overlay
  accepted_answers; MCQ casefolds; overlay cks live under `ov["exercises"]`; etc.).

## Pointers
- Queue/details: bottom of `docs/RAMIN_REVIEW_BACKLOG.md` (2026-07-31 section).
- Native list: `docs/NATIVE_REVIEW_full_turn_instructions_2026-07-31.md`.
- Validate: `.content-venv/bin/python -m pytest scripts/tests/test_compile_content.py -q` (fast unit)
  and `bash scripts/verify.sh` (full chained content stage; ~5 min; backend/frontend stages will
  "fail" only because Docker/npm aren't up — ignore those).
