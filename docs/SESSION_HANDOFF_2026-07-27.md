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

## ✅ DONE since this doc — en-nl `_distractor_values` casefold-dedup (PARTIAL, commit e4144c8e)
Landed a casefold-dedup on MC/listen distractors (+ `backend/tests/test_distractor_casefold.py`,
DB-free). It merges pairs whose GLOSS differs only by case (apples/Apples, library/Library) —
NOT ones whose capitalized variant is also reworded (the hospital/Hospital, the route/Route). Two
residuals, both in the backlog's BATCH-3 "★" item: (a) run the backend INTEGRATION suite before
merge (needs Postgres — docker not installed here — to confirm no seeded template starves below the
3-option floor); (b) a more complete token-identity dedup (catches reworded-gloss variants too) is
deferred until it can be integration-tested. NOTE: local Python is 3.9 (backend targets 3.12) so the
real module won't even import here — the algorithm was proven via a standalone harness instead.

## ⏳ IN FLIGHT — native-review BATCH 4 (launched 2026-07-28)
4 sonnet reviewers running (read-only), reports arrive as `<task-notification>`s in your context:
- **fa-en** a1_09/10/11/12/13 · **prs-en** a1_11-15 · **nl-en** a1_10/11/12/13/14 · **en-nl** a1_11-15.
Process each per the pipeline: verify → fix clean pack-side ones + commit → queue deploy/native waves
→ flip clean packs reviewed. Then launch batch 5 (next a1 band).

## ✅ Batch-3 pack-side wins DONE 2026-07-28 (all committed, ledger 0 DEAD / 2 tier / 116 floor)
- prs-en a1_08 پونډ→پوند (HIGH, 359d85be) · prs-en a1_10 forward-ref move to lesson04 (d5ffa1d1)
  · fa-en a1_03 "much" prompt-shows-answer CRITICAL → noun-only slot (1910f052)
  · backend casefold-dedup PARTIAL (e4144c8e).
- fa-en pack-feedback register = escalated to a Ramin POLICY call (not drift; 116 formal/0 colloquial
  is a uniform authored convention; pin is overlay-only). See backlog.
- REMAINING batch-3 items are all DEPLOY-EFFECT or native/policy — consolidate into the en-nl backfill
  wave below AFTER batch-4 en-nl findings land (touch backfill_lexemes_en_nl.py once).

## ▶ Next autonomous items (after processing batch-4 reports)
1. **Consolidated en-nl backfill wave** (deploy-effect) — the other half of the ambiguous-MC
   fix the backend casefold couldn't reach (reworded capitalized variants: the hospital/Hospital,
   the route/Route) PLUS the a1_09 route_word false-attribution contamination. Deploy-effect. See
   the backlog BATCH-3 en-nl items. (Do NOT blanket-exclude caps — caused 7 DEAD before; use `_pure`
   exact-case tags + selective repoint.)
3. **If/when Postgres is up:** run the backend suite (`pytest` in backend/) to clear residual (a) on
   the casefold fix, then take the token-identity dedup (residual (b)).

The other batch-3 queued waves (fa-en a1_03 "much" leaked-gloss CRITICAL; fa-en pack feedback_frame
register sweep MAJOR-systemic; en-nl voor gloss; prs-en a1_10 forward-ref; food_item_orderable;
prs-en who/cafe backfill glosses) are all in the backlog, ranked, with fix approaches — several are
deploy-effect / native-confirm.

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
