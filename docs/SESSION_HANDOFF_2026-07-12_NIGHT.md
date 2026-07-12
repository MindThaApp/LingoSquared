# Session handoff — 2026-07-12 night (supersedes the EVENING doc)

Read this + `docs/COORDINATOR_HANDBOOK.md` + root `CLAUDE.md` to resume.
Everything below is committed and pushed to master EXCEPT the one in-flight
Codex task called out in §2 — **read §2 before touching `scripts/compile_content.py`.**

---

## 1. THE HEADLINE — a launch blocker was found live, fixed, and deployed

`frontend/src/components/exercises/MatchingPairs.tsx` keyed and disabled the
right-hand option tiles **by their text value**. Content legitimately maps many
lefts onto one right (nl A1 unit13 sends 3 items to `lekker`, 3 to `leuk`), so
matching the first pair instantly disabled EVERY tile sharing that text. The
remaining lefts became unmatchable, `Check` never enabled, and **the learner was
hard-stuck — the lesson could not be completed at all.** In en-nl, the reference
launch pair.

- Fixed by tracking matches as `left -> right INDEX` (commit `ba804a7`).
  **Index 0 is falsy** — every "is this matched" test is `!== undefined`, never a
  truthiness check. Do not "simplify" that back.
- Reproduced live, fixed, re-verified live (all 6 pairs match, grades Correct,
  React duplicate-key console errors gone), full `npm run build` green.
- **Deployed to 192.168.4.4** (frontend only, `--mode production.lan`, bundle
  `index-DAFhXV6O.js` confirmed being served). Backend NOT deployed.
- It compiled clean and validated at 0 errors. **Only playing the lesson found it.**
  One fix cleared 5 broken exercises (nl u11/u12/u13, it u01).

## 2. IN FLIGHT — one Codex task, tree is DIRTY

`scripts/compile_content.py` is **modified in the working tree, uncommitted**, by
a running Codex task (job `task-mri56xl9-ifgl0z`, model gpt-5.5, effort high).

Four new validators were added (all four are IN that uncommitted diff):
- **3 are GOOD and already found real bugs — keep them:**
  duplicate matching_pairs LEFT items; production-prompt word-count contradiction;
  dialogue-audio vs teaching-cards (correctly fires zero times).
- **1 was BROKEN** — the untaught-vocabulary check extended to `prompt.target_blocks`
  emitted **360 false positives** (it tokenized English gloss text, and even
  content-key fragments like `lesson01`, as untaught target-language words).
  The running task is repairing exactly that, with instructions to downgrade it to
  a WARNING if it cannot reach zero false positives.

**To resume:** `node .../codex-companion.mjs status task-mri56xl9-ifgl0z --cwd <repo> --json`
then `result <job-id>`. **Verify it yourself** — run `bash scripts/verify.sh --content-only`
and confirm the ONLY errors are none. Do not trust the report (see §5).
If the task died, `git diff scripts/compile_content.py` still holds the work —
a "failed" Codex task often has done most of it.

## 3. What shipped today (all merged, validated, pushed)

- **Admin user management** (migration `0026`, Ramin-requested): create a user with
  a server-generated one-time temp password, reset password, list/search,
  deactivate/delete, promote/demote admin, unlock lessons. `is_admin` is a persisted
  column OR'd with `ADMIN_EMAILS` (env var still bootstraps); demoting/deactivating
  the LAST active admin is refused (409). Deactivated users rejected at login,
  refresh, AND on existing access tokens. **API-only — no admin UI yet.**
  Full backend suite green on an isolated DB (`ls_admin_test`).
- **Content:** English B1 units 12-14; Italian A1 16-18; Russian A1 16-18 (all
  fresh-context reviewed, manifest-wired); fa u37 ambiguous-matching fix;
  3 more unanswerable exercises fixed (nl u49/u50 duplicate lefts, it u14 word-count).
- **Compiler/infra:** listen_select same-speaker validator; `sync_dev_db.sh` re-auths
  and retries once on a mid-run 401.

## 4. THE BIG LESSON — sampling was tried, measured, and REVERSED

I put it/ru on 1-in-3 review sampling to economize. **It was wrong and the data says so.**

| Wave | Review | Defects |
|---|---|---|
| en B1 12-14 (launch-gate) | full | **9** |
| ru A1 16-18 | 1-in-3 sample | **4** (one NEW bug class) |
| it A1 16-18 | was going to merge on VALIDATORS ALONE | **10** |

Italian was pulled back to full review only because the Russian sample found a new
class — and it turned out to have **10 compiler-invisible defects** (it validated at
0 errors). Three of them **graded a CORRECT learner answer as WRONG**. It also broke
character canon (Sam is an engineer since u02; u17 made him a teacher) — text that
`audio_manifest.py` would have sent to the **paid audio recording queue**.

**Rule now in root CLAUDE.md §Tiered review 4: a lane is mature per-RECIPE, not
per-language. Moving to new TOPICS is new territory.** it/ru are back at FULL review.

## 5. Root cause of the 23 defects — and the cheap fix

**Authors don't apply rules that are merely auto-loaded/"binding". They apply rules
that are in front of them while writing.**

Proof from the same day: the ONE class I quoted VERBATIM in those dispatch prompts
(duplicate/gloss-sharing matching_pairs lefts) came back with **ZERO findings in two
independent reviews** — after needing 5 fixes the previous wave. Every defect found
was a class the prompts did NOT mention. All three authors were **Sonnet**, and all
had `docs/content/CLAUDE.md` auto-loaded. **Sonnet's capability was never the binding
constraint — the prompt was.**

→ **`docs/content/AUTHORING_PREFLIGHT.md` now exists. PASTE IT VERBATIM into every
content-authoring dispatch** (do not link it), and require a per-item self-report.
First trial: the Sonnet fixer using it found an overlay-mirror dependency nobody had
told it about, because it ran the real acceptance command.

**Cost order, cheapest first: validator → checklist → review.** A validator costs
tokens once and catches its class forever (the 3 new ones found 3 real bugs on their
first corpus run — one in a unit Opus had already "reviewed" and passed). An Opus
review costs 160-216k tokens EVERY wave. Reserve review for what neither can reach:
character canon, "is this answerable by a human", genuine judgment. Review's real job
is discovering NEW classes (it found 4 → 4 permanent validators), not re-finding known ones.

## 6. Budget & model routing (Ramin, 2026-07-12 night)

- **Remaining: Codex ~25%, Opus ~31%.** Codex is ~10x cheaper per month ($20 vs the
  $200 Max 20x plan) but is the SCARCER resource right now — don't dump routine work
  into it. Spend the last 25% on things only Codex should do: **compiler validators**
  (permanent value) and backend surgery.
- **Recommended coordinator seat: Fable 5 at LOW effort** (bump to medium only when
  actively diagnosing or ruling on something). Fable was the previous coordinator and
  wrote the handbook heuristics. **Do NOT drop the coordinator to Sonnet** — every
  worker today self-reported success and THREE were wrong; the coordinator is the last
  line of defence. Cheap workers, expensive verifier, not the reverse.
- **Summon Opus deliberately** for exactly two things: fresh-context review of
  launch-gate content, and live debugging of a real bug.
- **The dominant coordinator cost is context re-sent per tool call and huge tool
  outputs — not thinking tokens.** Fewer, denser tool calls beats lowering effort.
  (I wasted budget today re-running `verify.sh` three times where one pass would do.)

## 7. Open decisions for Ramin

1. **The B1 English spine is EXHAUSTED.** Units 12-14 consumed the last three spine
   outcomes. A 15th unit needs a NEW spine outcome added first — his call.
2. **Teaching-depth ruling (given today):** per-DIRECTION, but *launch on what exists*.
   So X→en depth (7.90h) is drip, NOT a launch blocker.
3. Dev-DB sync not yet run — **the new it/ru units will not appear in the app until
   `scripts/sync_dev_db.sh` runs.**
4. Unchanged from before: domain + Cloudflare tunnel; Apple/Google accounts; Azure
   Speech key for real Farsi TTS; **live `ADMIN_EMAILS` swap before any beta user**;
   Dutch native review + phone QA; ja/ko IME decision; C1/C2 planning.

## 8. Next actions (in order)

1. Land the in-flight Codex validator repair (§2) — verify the corpus YOURSELF, commit
   `scripts/compile_content.py` with an explicit pathspec, push.
2. Run `scripts/sync_dev_db.sh` so it/ru 16-18 + en B1 12-14 reach the app.
3. Optional drip (NOT launch-blocking): X→en overlays for English B1 12-14
   (nl-en/fa-en/prs-en) — quote the register pins VERBATIM and paste the pre-flight.
4. Consider an admin UI for the new user-management API (currently API-only).

## 9. State at handoff

- master = `0638e39` + whatever §2 lands. Pushed to private GitHub.
- Working tree: `scripts/compile_content.py` DIRTY (in-flight Codex, §2);
  `.claude/settings.json` modified (pre-existing, not mine).
- 9 worktree entries exist from today's dispatches — all merged; safe to prune, but
  **check `git log --oneline <branch> -1` against each branch's own base before
  `git worktree remove`** (standing footgun: "ancestor of master" != "merged").
