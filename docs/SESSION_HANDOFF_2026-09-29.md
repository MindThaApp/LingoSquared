# Session handoff — 2026-09-29

Repo is now **`~/dev/LingoSquared`** (moved out of iCloud today; the iCloud copy is stale —
see `STALE-DO-NOT-USE.md` there). Branch `fix/launch-gate-content-review-wave1`, pushed,
GitHub CI **green** (first time since 2026-09-01). **Nothing from 09-02 onward is deployed live.**
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
1. **Deploy to live (192.168.4.4)** — authorized once the verification bar passes. BEFORE
   relying on admin endpoints: run the promote script for the live admin (admin now = DB flag
   only). Migration 0028 → every user re-logs in once. Then import all reviewed tiers
   (09-02 handoff has the import recipe). Server app containers were down at last check.
2. Remaining dialogue-text gaps (non-launch): pl A1/A2/B1, hi A1/A2/B1, a few es/ar/fr.
3. Roadmap from the review: tap-to-build word bank for A1/A2, push-reminder cron + goal picker,
   rebuild A2 for launch paths (30+ units), replace C1 "repeat the exact paragraph" items,
   a "recommended course" field (frontend polish item 3 needs it).
4. Native review of new nl/fa/prs UI strings added today (see commit messages).

## Needs Ramin
- Rotate the server SSH password + live admin login (were plaintext in the 09-02 handoff).
- Azure Speech key for Farsi audio in production.

## How work ran
Cloud sessions (claude.ai/code) are launched by the coordinator via the claude-in-chrome MCP
with one-paragraph briefs; each opens a PR into the working branch; coordinator reviews,
merges, runs build/vitest/pytest (CI-style, repo mounted: see below), live-verifies.
CI-style backend run: `docker compose run --rm -v "$HOME/dev/LingoSquared:/repo" -w /repo/backend api ...`
(without the mount, `test_content_answer_shapes` silently skips).
