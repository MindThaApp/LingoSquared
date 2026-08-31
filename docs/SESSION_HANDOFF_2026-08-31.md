# Session Handoff — 2026-08-31 (overnight C1 rollout session, updated ~06:20)

**Read this first, then root `CLAUDE.md` and `docs/content/CLAUDE.md`.**
This session finished the Dutch C1 tier (started by the 2026-08-30 handoff) and then
rolled the same 8-unit C1 tier out to three more languages: **Spanish, German
(fully shipped), and Italian (in progress, 4/8 units).** Paused mid-Italian-tier at
the user's explicit request, twice (once after unit01, again after unit04). Working
tree state below.

**Worker note (important, read before dispatching anything):** deepseek ran out of
API balance (`402 Insufficient Balance`) partway through Italian unit02 authoring and
is now completely unusable until Ramin tops up the DeepSeek account. Ramin explicitly
chose to switch to **Codex** for the rest of this session (see §8 for what that's
like in practice — noticeably slower per-unit but so far equal or better quality, and
it hit one real hang that needed a `--fresh` restart). Check whether deepseek's
balance has been restored before defaulting back to it.

---

## 0. What shipped this session (committed + pushed to origin)

All four commits are on `fix/launch-gate-content-review-wave1`, pushed to
`git@github.com:ramin-azizi/LingoSquared.git` (redirects to `MindThaApp/LingoSquared`):

1. **`en-nl-c1`** — completed (units 05-08 added to the 4 that existed from the prior
   session), full fresh-context review (7 defects found incl. a systemic missing-
   punctuation grading bug), all fixed, verified, committed, pushed.
2. **`en-es-c1`** — new tier, all 8 units, full review (10 defects, mostly a recurring
   "writing fully delivers the spine outcome, speaking only partially does" pattern +
   one real untaught-vocabulary gap), all fixed, verified, committed, pushed.
3. **`en-de-c1`** — new tier, all 8 units, full review (only 2 residual defects — much
   cleaner than nl/es, because units 06-08 were dispatched with a **self-compile
   requirement baked into the prompt**, which caught real errors before they even
   reached review). Unit05 shipped genuine course-scoped compile errors mid-authoring
   (untaught vocabulary including the counterfactual auxiliary "hätte" itself, and a
   dictation exercise wrongly pointed at a shared multi-turn dialogue audio asset
   instead of a dedicated single-sentence one) — both caught and fixed before
   continuing. Committed, pushed.
4. **`en-it-c1`** — **STARTED, NOT FINISHED.** Units 01-04 exist and compile
   course-scoped clean, committed **locally only, NOT pushed** (see §1). NOT
   fresh-context reviewed. Units 05-08 remain to build.

## 1. Git state at handoff

- Branch `fix/launch-gate-content-review-wave1`, local tip `c910793a` (2026-08-31,
  ~06:17). Two local-only commits ahead of `origin`:
  - `c9e2c753` — it C1 unit01
  - `c910793a` — it C1 units 02-04
- **`origin` is TWO commits behind.** Push both (or squash) before assuming any of
  the Italian unit01-04 work is backed up off-machine.
- Working tree is otherwise clean of C1 work — no uncommitted C1 content.
- Misc untracked infra carried over from prior sessions, not touched, not mine to
  clean up: `.firecrawl/`, `.playwright-mcp/`, `backend/docker-compose.faqa.yml`,
  `backend/docker-compose.play.yml`, `backend/web_dist/`, `frontend/.env.faqa`,
  `docs/SESSION_HANDOFF_2026-07-17.md`.

## 2. NEXT TASK — finish the Italian C1 tier, then keep rolling out

**Italian (`en-it`) units 01-04 exist and compile clean but are UNREVIEWED.** Same 8
universal C1 outcomes as every other tier, in this fixed order:
1. `discourse.structure_extended_discourse` → built: `c1_unit01_mobilita` (Sam's
   bike-commuting proposal to Elena; do NOT copy this content when building unit05+,
   it's just there for continuity/register reference)
2. `inference.infer_implicit_meaning` → built: `c1_unit02_ironia`
3. `register.control_tone_and_register_precisely` → built: `c1_unit03_registro`
4. `argumentation.concede_and_counter_with_subtlety` → built:
   `c1_unit04_concedere_e_controbattere`
5. `hypothesis.reason_about_counterfactuals` → **TODO**
6. `idiom.use_idiomatic_and_figurative_language` → **TODO**
7. `mediation.mediate_and_synthesize_complex_sources` → **TODO**
8. `persuasion.persuade_with_rhetorical_devices` → **TODO**

**CHARACTER CANON — critical, this exact lane has a real history of violating it:**
Sam is an **American engineer** (ingegnere) in an office in Milan; Elena is an
**Italian teacher** (insegnante). Established since A1 (`a1_unit02`/`a1_unit17`); a
2026-07-12 review had to fix a prior contradiction where a different unit made Sam a
teacher. Grep `docs/content/realizations/it/` before writing any new dialogue that
touches either character's profession or facts.

**Register:** informal `tu` throughout (it lane pin, unchanged from A1 through C1 —
do not introduce formal `Lei`).

**After Italian C1:** the remaining mature languages with zero C1 are fr, ru, ar, ro,
pl, hi (see §5 matrix). fa/prs stay native-reserved/blocked. de-en is separately
underbuilt (not part of the C1 rollout — it's the shared-English-realization X→en
lane, different axis).

## 3. HOW to build it (the pipeline this session validated across 4 languages)

This is now a proven, repeatable loop — run it per unit, per language:

1. **Dispatch authoring to `~/bin/deepseek --yolo "<prompt>"` in the background**
   (`run_in_background: true` on the Bash tool call, NOT a manual trailing `&` —
   double-backgrounding breaks output capture). Every dispatch prompt MUST:
   - Paste `docs/content/AUTHORING_PREFLIGHT.md` **verbatim** (not linked).
   - Point at `docs/content/AUTHORING_GUIDE.md` + the sibling unit's realization/
     overlay as a structural (not content) template.
   - State the exact spine outcome text (grep it fresh from `universal_spine.yaml`
     every time — don't trust a remembered version).
   - State the lane's register pin explicitly (read it off an existing unit's
     `course.register_policy` block, don't guess).
   - Include the STRONG sibling-isolation instruction.
   - **Include the accumulated cross-tier lessons** (see §4 below) — every one of
     these was a REAL defect found in a prior tier; restating them up front measurably
     reduced defect rates tier over tier (nl: 7 defects → es: 10 but no systemic bug →
     de: 2 after adding a self-compile requirement).
   - For unit03+ in any tier, **require the worker to self-run course-scoped compile
     before reporting done** and fix any ERROR itself. This was added starting with de
     C1 unit06 and worked well — catches real bugs one round-trip earlier.
2. **After each dispatch, before trusting the output:**
   - Check for exactly 2 new files (one realization, one overlay). **If you see MORE
     than one realization file for the same unit number, this is very likely a
     deepseek self-confusion artifact** (it happened 4 times this session — nl unit05,
     de unit03, de unit04, it unit01), not a real concurrent worker. Verify: (a) was
     only one deepseek process launched for this unit, (b) does the overlay's
     content_key match one specific realization file. Delete the stray, keep the
     matched one. Do NOT ask the user to adjudicate a "collision" that's actually just
     one worker's own earlier output.
   - Cross-check the overlay's `content_key` prefix (e.g. `it.c1.unit02.<slug>`)
     against the realization's own `content_key` — they must match exactly.
   - **~1 in 4-5 background dispatches this session produced NOTHING** (either a
     silent stdin-detection stall — log shows only "Warning: no stdin data received in
     3s..." — or got killed with "Execution error" and no files). Always verify files
     exist before treating a "completed" notification as success; if nothing landed,
     just retry the identical dispatch — every single retry succeeded on the 2nd try.
3. **Wire the manifest** — `deepseek --flash --yolo` a one-line append/insert to
   `scripts/content_manifest.txt` (new course → new line after the language's B2 line;
   existing course → append to both the realizations and overlays fields, position-
   matched). Always paste back the resulting line and eyeball it.
4. **Verify course-scoped**: `bash scripts/verify.sh --content-only`, then grep for
   `COMPILE FAILED` and the specific course's `-- compiling en-XX-c1 --` stanza —
   **`content: pass` in the summary is necessary but not sufficient**; a per-course
   `COMPILE FAILED` can hide inside an overall "pass" if you don't grep for it (this
   bit de C1 unit05 — the top-line summary looked fine on a stale read).
5. Repeat 1-4 for all 8 units.
6. **Full fresh-context review is mandatory** for a language's FIRST C1 tier — dispatch
   a `general-purpose` agent (not a fork) with zero authoring context, pointed at all
   16 files (8 realizations + 8 overlays), the binding docs, and explicit call-outs of
   every defect class found in PRIOR tiers (paste the actual list — this is what makes
   each review find fewer NEW defects; it's not going to spontaneously re-derive "check
   for regret-framing contradictions" on its own).
7. **Fix every finding** via one consolidated deepseek dispatch (all fixes for all
   units in one prompt is fine — deepseek handled 7-10 fixes across 8 files correctly
   in one dispatch, twice). Independently re-verify course-scoped yourself afterward —
   don't just trust the fix job's own "0 errors" claim; deepseek's self-reports were
   accurate every time this session, but re-verifying is cheap and the rule stands.
8. **Commit with explicit pathspecs** (`git add <files...>`, never `-A`/`.`), stage
   only that language's new files + the manifest — check `git status --short` first,
   this repo always has unrelated untracked infra files sitting around from other
   sessions/machines that must NOT get swept in.
9. **Ask before pushing** — commit/push is owner-reserved per root CLAUDE.md. Ramin
   approved "commit and push" explicitly for nl and es in this session; I re-asked and
   got the same answer for de. Keep asking each time unless told otherwise.

## 3a. Codex dispatch pattern (used for it C1 units 02-04 after deepseek ran dry)

Different mechanics from deepseek — use `node "<codex-companion.mjs path from root
CLAUDE.md>" task --cwd "<repo>" --background --write --resume --prompt-file <file>`
(first dispatch in a session needs `--fresh` instead of `--resume` — there's no prior
thread to resume yet, it errors "No previous Codex task thread was found"). Same
prompt content works fine (spine outcome, character canon, register, the accumulated
lessons in §4, preflight instructions) — Codex doesn't need the CLI-wrapper-specific
framing deepseek dispatches used.

- **Poll with `status <job-id> --cwd ... --json`**, or better, use the Monitor tool
  with an until-loop polling that same command every 5-15s until `"status"` matches
  `succeeded|completed|failed|cancelled` — avoids manual re-checking.
- **Get the final report** with `result <job-id> --cwd ...` (not just the status
  JSON's truncated `summary` field) — this is where the preflight self-report and
  compile output live.
- **Per-unit timing is wildly inconsistent.** Unit03 took ~7 minutes end to end.
  Unit04's first attempt (via `--resume`, continuing the thread from unit03) produced
  one planning message in the first 30 seconds, then went **completely silent for
  ~55 minutes** with zero further log lines and no files written — a genuine hang,
  not just "Codex is slower." Cancelled it (`cancel <job-id> --cwd ...`) and
  redispatched the identical prompt with `--fresh` instead of `--resume`; it
  completed normally on the fresh thread. **If a Codex job has been silent for more
  than ~10-15 minutes past its last log line (check the raw log file path from the
  status JSON's `logFile` field, not just the `progressPreview` array which can look
  identical to an active job), don't assume it's just slow — cancel and retry
  `--fresh`.**
- **Content quality so far (units 03-04, one clean run each): as good as deepseek's
  best output, possibly better** — unit03's sourcing disclosure named specific URLs
  actually checked (not just "no source found"), the preflight self-report was
  detailed and accurate, and no stray duplicate-draft files were left on disk (unlike
  deepseek, which did this 4 times this session). Too small a sample (2 clean runs)
  to call it definitively better, but nothing worse than deepseek either.
- **Always diff Codex's manifest edits yourself** (`git diff scripts/content_manifest.txt`)
  per root CLAUDE.md's standing "never trust Codex's self-report" rule — this applied
  even to the small one-line manifest appends in this session; every diff checked out
  clean, but the rule doesn't get suspended just because the edit is trivial.
- **Codex jobs run unisolated in the main working tree** (same as documented in root
  CLAUDE.md) — don't run two Codex dispatches concurrently on this repo; this session
  serialized every dispatch (author → verify → wire manifest → verify → next unit),
  never launching a second Codex job before the first fully completed or was
  cancelled.

## 4. Accumulated cross-tier lessons (restate these VERBATIM in every future dispatch)

1. **Punctuation**: `backend/app/review/grading.py::_normalize` casefolds + collapses
   whitespace but does NOT strip punctuation; typo tolerance is distance-1 only. Every
   multi-sentence `accepted_answers`/`tested_text` must carry the SAME internal
   punctuation as its matching teaching-card sentence. `word_order` exercises are the
   one exception (token sequences, must stay unpunctuated to match `word_bank` tiles).
   This was a SYSTEMIC bug across the entire nl tier — the single most expensive defect
   class found this session.
2. **Open-ended production instructions** graded against one narrow exact string mark
   correct learners wrong. Either tighten the instruction to require exact reproduction
   of a named taught model, or broaden `accepted_answers` to cover the realistic range
   the instruction actually allows.
3. **Speaking-vs-writing outcome-delivery asymmetry**: when a spine outcome names both
   a speaking and a writing requirement, the speaking exercise must deliver it as fully
   as the writing exercise does. Recurred 1x in nl, 3x in es (units 02/04/05) — check
   ALL 8 units every time, not just the unit where it recurred historically.
4. **Teaching-card vs bound audio mismatch**: a "full text/model" teaching card must
   match the unit's own audio asset and every exercise's `tested_text` EXACTLY,
   sentence for sentence. Every `introduced_tokens` entry on such a card must be tested
   somewhere. Found in nl unit08.
5. **Regret-framing contradictions** (counterfactuals unit): two exercises testing the
   same passage must characterize the same detail (e.g. regret vs. no-regret)
   consistently, and any instruction naming "an expression of regret" must be honestly
   satisfied by its accepted answer, not contradicted by it. Found in nl unit05.
6. **Dictation exercises must use a DEDICATED single-sentence audio asset**,
   byte-identical to `tested_text` — never reuse a shared multi-turn dialogue asset.
   This is a REAL course-scoped-compile-breaking bug (byte-equality check), not just a
   review nit — shipped in de C1 unit05, caught by `verify.sh`, fixed before
   continuing. Also flag any dictation asset reused by other (non-dictation) exercises
   as a style issue even if the text happens to match (de unit04, low severity).
7. **Course-scoped compile finds REAL "tokens not introduced" errors**, not just
   phantom single-unit-validation noise — de C1 unit05 shipped 10 genuine ones
   (including the unit's own core grammar word, "hätte," for a counterfactuals unit).
   Trace every exercise's tested vocabulary back to a teaching card that appears
   EARLIER and genuinely displays that exact word before finalizing a unit.
8. **German's rich morphology can mask untaught tokens**: a capitalized/inflected form
   (e.g. formal "Ihre" vs. the already-taught "Ihr"/"ihre") can slip past both the
   author and a normal review pass if the check doesn't distinguish forms carefully —
   found in de unit08 by the review, not the compiler. Worth an explicit check in any
   morphologically-rich language (de done; it/ru/ar/pl worth the same scrutiny later).

## 5. Tier coverage matrix (as of 2026-08-31, post-session)

```
dir        A1  A2  B1  B2  C1
de-en      14   0   3   0   0
en-ar      24  10  19   8   0
en-de      24  10  19   9   8   <- shipped this session
en-es      15  10  19   8   8   <- shipped this session
en-fa      57  10  16   0   0   (native-reserved; no B2)
en-fr      14  10  19   8   0
en-hi      19   6  19   8   0
en-it      24  10  19   8   4   <- IN PROGRESS, units 01-04, unreviewed
en-nl      67  10  11   8   8   <- completed this session (was 4, now 8)
en-pl      20   6  19   8   0
en-prs     61  10  11   0   0   (native-reserved; no B2)
en-ro      20   6  19   8   0
en-ru      24  10  19   8   0
fa-en      63  16  19   8   0
nl-en      63  16  19   8   0
prs-en     63  16  19   8   0
```
(shared English realization feeds all 4 X-en overlay sets: nl-en/fa-en/prs-en/de-en —
any en-realization shape change must update all four + grep content_manifest.txt.)

## 6. Pending owner decisions / reserved

- **Push the two local-only it-C1 commits** (`c9e2c753` unit01, `c910793a` units
  02-04) — owner-reserved, ask before pushing, same as every other commit this
  session.
- **Top up the DeepSeek API account** (`402 Insufficient Balance` as of this session)
  if you want to go back to deepseek for future authoring — otherwise Codex is the
  working fallback (see §3a).
- Friend-beta feedback loop + live deploy: still blocked per the 2026-08-30 handoff
  (SSH key on 192.168.4.4 + app-admin 401) — untouched this session.
- App name still Ramin's call. fa/prs sentence authoring still native-reserved.

## 7. Clearing the chat

Safe. No env/settings changes this session beyond creating `.content-venv/` (a local
Python venv with PyYAML — gitignored, harmless, re-creatable via
`python3 -m venv .content-venv && .content-venv/bin/pip install pyyaml` if missing).
The uncommitted-until-now C1 work for nl/es/de is already committed+pushed; the it
units 01-04 work is committed locally (not pushed — see §1). `/clear` is enough.
