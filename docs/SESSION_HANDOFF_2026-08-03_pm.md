# Session Handoff — 2026-08-03 (PM continuation)

Branch: `fix/launch-gate-content-review-wave1`. Continues the 2026-08-03 (AM)
handoff. Standing directive: **"don't stop building until I say ready"**; this
session Ramin added **"build the new features to try out"**, **"all of them in
sub-agents"**, and **"lots of codex until its usage is finished."** Feedback
email address confirmed: **[admin email]** (Ramin's app-admin acct).

Local stack up: API 8020 (recreated this session to pick up backend changes),
web 8011, Vite dev server 5173, db healthy. Admin: admin@example.com + ~/.lingo_admin_pw.

## Shipped this session (all committed, NOT pushed, NOT deployed)

**Handoff follow-ups closed:**
- `0478784d` reading-gloss validator tokenizer aligned with frontend (internal
  apostrophes/hyphens); also fixed a latent un-tappable `BSN-nummer` gloss and a
  pre-existing stale test (`9e5ca493`'s validator rewrite left its test red).
- `e8720d29` homograph gloss overrides: nl b2 `eten`→noun "the food",
  `best`→adverb "quite". (Investigated all 9 flagged tokens; other 7 out of scope.)
- `55d7358d` glossed the 2 remaining un-glossed nl B2 reading passages.

**Three new features (Ramin's request), each browser-verified:**
- `bb833832` **Showcase page** `/showcase` (ProtectedRoute, linked from Home) +
  new reusable **`ReadingPassageWithQuestions`** component (passage pinned sticky
  while answering its comprehension questions below — the "combined passage+
  questions" upgrade Ramin approved). Discovers sample lessons via catalog.
- `c5de5519` **Skill-targeted practice**: (a) exercise-`type` filter on the
  practice feed (backend `types` param on POST /practice/{course}/batch; frontend
  chip row); (b) "Drill weak outcomes" — checkpoint result now returns
  `weak_lexeme_ids`, CheckpointPage links into /practice seeded with them. 4 new
  backend tests (`backend/tests/test_practice_skill_targeted.py`), full suite green.
- **Reading comprehension** already existed end-to-end (`reading_comprehension`
  exercise type, authored after every nl reading card) — NOT rebuilt; surfaced in
  the showcase. (Key finding: don't rebuild it.)

**Bonus content (spending the Codex budget):** extending tap-to-gloss to the
entire nl **A1** tier (was 100% un-glossed; ~50 units total have reading cards).
- `00662de8` A1 wave 1 (units 06-15, ~130 glosses, 0-error, reviewed inline).
- Waves 2 (16-23) + 3 (29-38) dispatched to Codex (2 concurrent); a fresh-context
  quality-review agent is checking wave 1.

## Build architecture used (works well — reuse it)
- Fan-out on DISJOINT files: Codex owns backend/`compile_content.py`/content;
  Claude agents own frontend; coordinator defines a frozen contract + verifies +
  commits with explicit pathspecs. App.tsx touched by only ONE builder. Backend
  source is volume-mounted (`.:/app`) so `docker compose up -d --force-recreate api`
  picks up changes for live browser-verify.
- Browser-verify recipe: dev server 5173 (CORS-allowed; 8011 is NOT — its build
  calls 8020 directly and CORS blocks it). Auth by injecting a fresh token into
  localStorage `access_token` (login fetch in page context). Token TTL ~short —
  re-inject when redirected to /login. Unlock practice by completing lessons via
  API (POST /lessons/{id}/start then /complete) — admin had 2 A1 lessons completed
  this session for that.

## Remaining / next
1. **Codex A1 gloss waves** continue until quota exhausted: after 16-23 & 29-38,
   remaining = 39-72. Validate (0 errors + 0 gloss-key warnings) + review + commit
   each wave with explicit pathspecs. Codex glosses were high-quality in waves 1.
2. **Dev-DB re-import** of the new content (B2 + A1 glosses ride in ContentItem
   JSON; A2 BSN-nummer key change; homograph re-backfill) so it's tappable locally.
   Not done yet (deploy blocked regardless). Showcase demos on B2 content already
   in the dev DB, so "try it" works without this.
3. **fa/prs practice-filter labels** were added as English placeholders in the
   fa/prs locale JSONs (minor i18n debt; RTL is the mandated verify target).
4. **Ramin's calls (unchanged):** app name (`docs/APP_NAME_SHORTLIST.md`); live
   deploy (SSH key on 192.168.4.4 + app-admin 401 still blocking).

## Verification status
All features: real backend pytest (isolated `lingosquared_test` DB) green; full
`npm run build` green; live browser play-through of showcase (gloss+comprehension
grading+dictation) and practice type-filter. Drill-weak-outcomes backend-tested;
its UI link is build-verified (not clicked live — needs a wrong-answered checkpoint).

## Update — nl reading + dictation BOTH 100% complete; es reading glosses started

- **nl reading track: 100%** (A1/A2/B1/B2). A1 = 62 units glossed across 7 waves,
  reviewed by 4 agents: 1 defect / 62 units (eruit, fixed) + 1 clarity note (half).
  Registry logged. Commits: 00662de8, 437a79ef, 708d0c66, 57523635, (eruit fix).
- **nl dictation: 100%** (A1/A2/B1/B2). A1 = 62 dictation exercises (pilot 06-10 +
  waves D2-D7), each reusing a single-sentence audio asset, byte-matched,
  orthography_strict. Verified 0 errors + scripted checks: all audio single-sentence
  (no dialogue), all sentences taught in-unit. Commits: (pilot), 0359d510, (D4-D5),
  86de7593.
- **Dev-DB re-import DEFERRED:** the new A1/B2 content is committed but NOT re-imported
  to the dev DB (import is API-only `POST /admin/content/import` from a compiled
  ImportRequest — no one-liner; deploy blocked anyway; showcase already demos on
  B2 content that IS in the dev DB). Re-import when deploying.
- **NEXT / in-flight:** es (Spanish) reading-gloss PILOT dispatched (en-es A1 units
  03-12) — es has 39 reading-card units, fr has 9, both un-glossed and now unparked
  (nl done). This is the cross-language continuation of the reading track; validate +
  review each wave like nl. de/it/ru have NO reading cards (nothing to gloss there).
- Codex used HEAVILY per Ramin's directive: ~19 tasks this session, never quota-erpred.

## Update 2 — es+fr cross-language expansion COMPLETE

Ramin: "do all of it (except stopping codex, continue that!)". Extended BOTH
modalities to es + fr:
- **es reading: 39 units** (A1 13 + A2 10 + B1 16) — reviewed 0 defects.
- **fr reading: 9 units** — reviewed 0 defects.
- **es dictation: 29** (A1 11 + A2 + B1 18; skipped a1_u09/u14 for pre-existing debt).
- **fr dictation: 21** (A1 14 + A2).
All validated 0 gloss-key warnings / 0 NEW errors; dictation byte-matched +
scope-creep audited.
**Codex validator-gaming footgun** (new, added to root CLAUDE.md Codex dispatch
footguns): Codex masked a pre-existing validation error by adding a teaching card
with fake `introduced_tokens`. Caught by diff-audit. Hardened all later dictation
prompts with a STRICT-SCOPE "skip, don't mask" rule → subsequent waves audited clean.
**Pre-existing es/fr realization debt** (flagged, NOT fixed): "token not introduced"
errors in es a1_u09/12/13/14, es b1_u27/36, fr a1_u05 — separate fix needed.
