# Session handoff — 2026-09-29

Repo is now **`~/dev/LingoSquared`** (moved out of iCloud today; the iCloud copy is stale —
see `STALE-DO-NOT-USE.md` there). Branch `fix/launch-gate-content-review-wave1`, pushed,
GitHub CI **green** (first time since 2026-09-01).

**DEPLOYED LIVE 2026-09-29 evening** (192.168.4.4, frontend :8011, API :8010): backend at
migration **0030**, full content+lexeme+practice sync (74 courses / 1,191 units), new LAN
frontend build. Backups in `~/backups/` on the server (`lingosquared_pre_deploy_20260929.sql.gz`,
`lingosquared_pre_0030_20260929.sql.gz`, `web_dist_20260929/`). Live admin is `admin@example.com`
(is_admin flag). Deploy recipe that worked: rsync ONLY tracked files
(`git ls-files backend | sed 's#^backend/##'` → `rsync --files-from`; same for `scripts/`, needed
by the remote lexeme backfill) — never plain-rsync `backend/` (local untracked `web_dist/`);
`docker compose build api` then **`up -d --force-recreate api`** (plain `up -d` once kept the old
image); content via `LINGO_ADMIN_EMAIL=admin@example.com LINGO_ADMIN_PASSWORD_FILE=~/.lingo_admin_pw
LINGO_BACKFILL_SSH=ramin@192.168.4.4 scripts/sync_dev_db.sh http://192.168.4.4:8010` (updates
existing units in place by content_key). Mic answers still need HTTPS on live. Throwaway
`smoke-*@example.com` accounts exist on live (registration is rate-limited after a few).
**Later (live at migration 0031):** import retires vanished keyed exercises (`retired_at`; first
live sync retired 3, all en-A2 for fa/nl speakers); refresh-token pruning
(`python -m app.scripts.prune_refresh_tokens`); SRS seeded from first-try lesson score;
wrong/almost lesson answers create ReviewItems → "Fix your mistakes" on Review (browser-verified);
e2e route-mocked specs (PR #23). Accessibility PR #22 is back with its cloud session for a rebase
(was 54 commits stale, 17 conflicts) — merge only after full vitest passes. Cloud usage near the
weekly limit (resets Fri 2026-10-02 17:00).
Also shipped this evening: Unit.track (core|situation) mechanism + Situations shelf (no unit
flagged — A2 plan Q8 open); 5 es/fr/ar dialogue_comprehension audio pointers.
No credentials in this file — keep it that way.

## What shipped (2026-09-28/29)

Ranked fix list from the 4-way review: https://claude.ai/artifact/7xcm4p4jNeqEogF3Kp4Qpk

- **Grading:** punctuation/curly-apostrophe/NFC no longer fail correct answers; multi-answer
  typo tolerance; Arabic-only hamza "almost"; matching-pairs multi-answer bug. Corpus harness:
  `scripts/grading_harness/`.
- **Lesson flow:** MCQ/word-tile shuffle; teaching cards interleaved with exercises; Next lesson;
  active course; Restart labels; runner hides nav; no unfinishable lessons / double submit.
- **Data:** no cross-user cache leak; live top-bar XP/streak; zero-answer completion blocked;
  idempotent answers (`client_operation_id`); atomic XP; effective streak on read; replay-XP cap.
- **Security:** sha256 refresh-token lookup (migration 0028); no auto-admin (use
  `backend/app/scripts/promote_admin.py`); startup refuses default JWT secret.
- **RTL/a11y/input:** virtual keyboard fixes; Enter/Ctrl+Enter; focus; radio semantics.
- **Audio:** TTS auth-retry, LRU cache, speaker-label/blank sanitizer (incl. ZWNJ labels),
  autoplay listening, speaker only on target-language blocks.
- **Perf:** entry bundle 186 → 106 kB gzip; lazy locales/routes.
- **Content:** compiler gives dialogue_comprehension its dialogue audio (~1,300 items);
  fa/prs A1+A2 dialogue pointers wired (fresh-reviewed, 0 blockers); 22 nl numeral prompts no
  longer speak the answer; es-b1/de-b1 defects fixed; review ledger updated.

## Next up
### Later on 2026-09-29 (all pushed, CI green on all three jobs)
- Shipped: retention backend (daily-goal picker API, opt-in push scheduler `ENABLE_PUSH_SCHEDULER`,
  quest rotation, Course.recommended; migration 0029), speaking unlocks per-unit, spoken-answer
  tolerance (`input_mode: "spoken"`), grader pronoun-drop + Persian joining equivalence, amber
  "almost" feedback (never blocks progress), voice answers with auto-stop on free-text items,
  tap-to-build word banks (compiler emits `prompt.word_bank` for A1/A2 free text), desktop layout
  (rail + sidebar ≥1024px), Dutch C1 production rewrite, Dari standardized on می‌توانم/نتوانستم.
- **A2 plan** (`docs/A2_REBUILD_PLAN.md` §0 decisions): Blocks A–D first. Spine has the 19
  A–D outcomes. **Wave-0 pilots committed but NOT wired** into the manifest:
  nl `a2_unit78_afgelopen_weekend`, fa `a2_unit19_last_weekend`, prs `a2_unit19_last_weekend`
  (each fresh-reviewed + fixed). Native questions: https://claude.ai/artifact/VuCSx1M3HNB8tbC12awcYa
  — WAITING ON RAMIN. After his answers: apply, freeze the recipe into the A2 authoring template,
  wire the manifest, then author the remaining 18 units/lang in batches of 12 with fresh review.
- Local dev DB (localhost:8020/5180) has all launch courses re-imported with word banks and the
  three pilots appended as unit 11 of each A2 course (local only).

## Next up
1. **Ramin's native answers** on the pilots + new quest strings (nl/fa/prs) → apply → A2 waves.
2. **Deploy to live (192.168.4.4)** — authorized once the verification bar passes. BEFORE
   relying on admin endpoints: run the promote script for the live admin (admin now = DB flag
   only). Migrations 0028+0029 → every user re-logs in once. Import all reviewed tiers
   (09-02 handoff has the import recipe). Server app containers were down at last check.
   Mic answers need HTTPS on the live server (Tailscale or Caddy) — browsers block the mic on http.
3. Remaining dialogue-text gaps (non-launch): pl A1/A2/B1, hi A1/A2/B1, a few es/ar/fr.
4. Roadmap: set `course.recommended` in overlays (needs Ramin's pick, e.g. Farsi A1 vs Foundations),
   'Situations' demotion of A1 scenario units (plan §4), cumulative review lessons / grammar SRS,
   stories / graded listening, prs audio recordings.

## Push gate (learned the hard way)
Run ALL of: `pytest scripts/tests`, backend pytest CI-style (repo mounted), frontend build +
vitest, and `scripts/verify.sh --content-only` before every push.

## Needs Ramin
- Rotate the server SSH password + live admin login (were plaintext in the 09-02 handoff).
- Azure Speech key for Farsi audio in production.

## How work ran
Cloud sessions (claude.ai/code) are launched by the coordinator via the claude-in-chrome MCP
with one-paragraph briefs; each opens a PR into the working branch; coordinator reviews,
merges, runs build/vitest/pytest (CI-style, repo mounted: see below), live-verifies.
CI-style backend run: `docker compose run --rm -v "$HOME/dev/LingoSquared:/repo" -w /repo/backend api ...`
(without the mount, `test_content_answer_shapes` silently skips).
