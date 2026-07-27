# Session handoff — 2026-07-27 (content native-review program)

**Read first:** the auto-loaded memory `project_2026-07-24_pack-polish-handoff.md`
+ `project_2026-07-26_coordinator-quality-bar.md` (gates, invariants, git discipline).
This doc is the *operational* snapshot for immediate continuation.

## Git state
- Repo `/Users/raminazizi/dev/LingoSquared` (NOT the iCloud CWD). Branch
  `fix/launch-gate-content-review-wave1`, **UNPUSHED**. HEAD **359d85be**.
- ~22 commits this session (7522844a..HEAD). Working tree clean apart from the
  long-standing untracked noise (.claude/settings.json, a stale .pyc,
  .firecrawl/, .playwright-mcp/, docker-compose.*.yml, .env.faqa, this file).
- Content gate ledger: **0 DEAD / 2 tier-short / 116 below-floor** (unchanged
  baseline). Run `bash -c '.content-venv/bin/python scripts/_practice_unit_scope_check.py'`.

## ✅ BATCH 3 COMPLETE — all 4 reviewers reported & coordinator-processed
No reviewers in flight. Nothing pending in this context. Two batch-3 fixes committed
(nl-en a1_07 menu_meaning `- $3`→bare = 76d519de; prs-en a1_08 پونډ→پوند HIGH = 359d85be).
Everything else from batch 3 is a QUEUED wave, fully written up in
`docs/RAMIN_REVIEW_BACKLOG.md` → "Native review — BATCH 3" (all 4 dirs' findings, ranked).

## ▶ START HERE next session — the two highest-value autonomous items
1. **★ en-nl `_distractor_values` casefold-dedup (BACKEND, one change, corpus-wide, IMMEDIATE
   runtime effect — no re-backfill).** `backend/app/practice/service.py` ~:386. MC/listen option
   lists dedupe by exact string only, so case-variant lexeme pairs (apples/Apples, library/Library,
   route/Route) both appear as options → ambiguous MC. Dedupe by casefold before sampling. Full
   spec + CAUTIONS (pool-floor, dedupe-on-display-value, RUN THE BACKEND TESTS) in the backlog's
   BATCH-3 "★ TOP AUTONOMOUS ITEM". This is the elegant fix for the whole ambiguous-MC class that
   the content-side `_pure`-tag wave was chasing — do this instead. Only ~content-side if rejected.
2. **Launch native-review BATCH 4** (see coverage below) — keep the review program advancing.

The other batch-3 queued waves (fa-en a1_03 "much" leaked-gloss CRITICAL; fa-en pack feedback_frame
register sweep MAJOR-systemic; en-nl route_word contamination; en-nl voor gloss; prs-en a1_10
forward-ref; food_item_orderable; prs-en who/cafe backfill glosses) are all in the backlog, ranked,
with fix approaches. Pick them up after the two above (several are deploy-effect / native-confirm).

## The pipeline (per reviewer batch)
1. **Verify every finding against the code/data** — never trust the report.
   Run the direction's `backfill_lexemes_*.py::iter_specs()` to see the real
   pool/gloss; read `backend/app/practice/service.py` grading if severity depends
   on it. (Reviewers already do this, but the coordinator re-gates.)
2. **Fix the CLEAN pack-side ones** (see patterns below), gate
   (`practice-validate` 0 err; unit-scope no new DEAD; self-reference 0; Dari 0
   for prs/en-prs), commit per direction with the wave-style message + the
   `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` line.
3. **Queue the non-clean ones** as fix-waves in `docs/RAMIN_REVIEW_BACKLOG.md`
   (see "Native review BATCH 2" for the format).
4. **Flip fully-clean packs** to `review.status: reviewed` + `fresh_context: 'true'`
   with a review-confirmation note; commit. (71/553 reviewed so far.)
5. Launch the next batch (see "coverage" below). ~470 packs remain — this is a
   multi-session program; each batch surfaces NEW systemic classes.

## Fix-wave patterns proven this session (clean, pack-side, DB-free)
- **Junk label-phrase / unrestricted `phrase` pools** → narrow the slot POS to
  `[noun,verb,adjective,adverb]` (drops `phrase`). Ex: en-fa 31-36 choose/translate.
- **Plural-number agreement** ("one/hundred dollars") → repoint the number preset
  to `count_plural_no_hundred` (drops both). Ex: nl-en/prs-en a1_03.
- **Deterministic volume_fill singleton wrong-phrase** ("I'm bad") → reframe to the
  taught phrase ("Not {item}, thanks"); span-scope to the volume_fill only.
- **False "this unit's own word" feedback over untagged course pool** → anchor the
  slot to the unit's generated tag (`en_prs_a1_unitNN_words` etc.) where it exists,
  else genericize the feedback string.
- **Stale overlay vs fixed realization** (prices/facts) → edit only the stale
  overlay entries; CHECK every X-en direction's copy (shared realization). Ex:
  unit07 $6→$9 in fa-en/prs-en/nl-en (de-en already fixed).
- **Mis-glossed homograph shown as answer** → lesson-scoped `english_gloss` override
  in the backfill (deploy-effect). Ex: باشید, خراب.
- **Register (fa-en formal→colloquial)** → focused native sonnet agent, calibrated to
  the compliant exemplar (a1_17); verify graded values byte-identical.

## Fix-waves QUEUED (NOT clean pack-side — backfill/deploy/native), see backlog
- **W2**: non-deterministic "I'm bad" word_orders (~1/3) + "Good day" — need a tag
  excluding bad/day. **W3**: fa-en good/fine/okay→خوب gloss-collision — narrower tag
  or restructure (`interchangeable` won't work — pool has بد too).
- **en-nl capitalization + weekday grammar-words** — needs `_pure` exact-case tags +
  repoint ONLY mid-sentence templates. **DO NOT blanket-exclude/skip — it caused 7
  DEAD** (units introduce own tokens capitalized). The metalabel exclusion (checkpoint
  part) is already committed.
- **en-nl a1_04 cafe_meetup function-word contamination** (same blanket-tag class).
- **prs-en a1_03 شمیر** "number" spelling — needs your (Ramin) native-Dari confirm.

## BLOCKED on Ramin / infra (do not attempt)
- Deploy + live lexeme re-backfill (activates all the backfill gloss/tag fixes;
  needs SSH key + live server). Junk-lexeme DB cleanup + `_label_guarded` widen
  (needs a dev DB — docker/colima NOT installed on this machine).
- Product decisions (checkpoint recombination policy, char-name romanization,
  first-teaching-unit root cause, CC share-alike), live-DB SQL, ADMIN_EMAILS.

## Batch 4 coverage (the next reviewer fan-out)
Reviewed so far: batch 1 = en-fa/en-prs wave-4 packs (20); batch 2 = fa-en/prs-en/nl-en/en-nl
a1_01–05 band (20); batch 3 = fa-en a1_02/03/04/06/08 + prs-en a1_06–10 + nl-en a1_04/06/07/08/09 +
en-nl a1_06–10 (20). ~470 packs remain. Batch 4 = continue the pre-recipe a1 band UPWARD on the four
X-en/en-X launch dirs (next untouched a1 units per dir, e.g. the a1_10–15 range, filling gaps), 4
sonnet reviewers, ~5 packs each, one direction per agent. Reviewer-prompt shape: read
AUTHORING_PREFLIGHT.md + docs/content/CLAUDE.md, read every template + its realization + overlay,
independently run the direction's `backfill_lexemes_*.py::iter_specs()` for ground-truth pools, cross
-check against `backend/app/practice/service.py` (lexeme_matches / _distractor_values / build_prompt)
+ `backend/app/review/grading.py`, return structured findings (never trust the pack's own notes).
Dispatch on model `"sonnet"` per [[feedback_2026-07-26_limit-fable-subagent-usage]].

## Scratchpad tools (session-specific → RECREATE if needed; logic in git history)
`pool_check.py` (list a tag's unit-scoped pool via iter_specs + the ported
lexeme_matches) and `union_repass.py` (comment-preserving span-scoped slot
transform + folded-notes append). Reviewer-prompt shape: see this session's
batch-2/batch-3 Agent dispatches.
