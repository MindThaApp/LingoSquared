# Session handoff — written 2026-07-12 ~04:15, before context clear

Read this + `docs/COORDINATOR_HANDBOOK.md` + root `CLAUDE.md` to resume
coordinating. Everything below is committed & pushed (private GitHub:
ramin-azizi/LingoSquared).

## State as of this handoff

- **Live server (192.168.4.4) deployed and verified** for the first time
  ever (2026-07-12): API :8010, web app :8011 (nginx `web` service),
  DB fresh-migrated 0001→0025, 36 courses / 16 languages, TTS
  smoke-verified. Phone URL: `http://192.168.4.4:8011` (LAN).
  Mac dev mirror: `http://192.168.4.13:5180` (Vite, port 5180 also in
  local CORS; local API :8020).
- **Dev-DB sync is hands-free**: `scripts/sync_dev_db.sh` with
  `LINGO_ADMIN_EMAIL=admin@example.com`
  `LINGO_ADMIN_PASSWORD_FILE=~/.lingo_admin_pw` (file exists on this
  Mac, chmod 600). For live: add `LINGO_BACKFILL_SSH=ramin@192.168.4.4`
  and arg `http://192.168.4.4:8010`. Coordinator runs BOTH syncs after
  every content merge, plus `git push` — standing routine.
- **Corpus grading test**: 6 failures remain in the ENTIRE corpus, all
  German-lane (en-de/de-en, another session's files, sitting modified/
  untracked in the main working tree — do not touch without Ramin's
  word that that session is dead).
- **Codex usage**: hit ~6% remaining ~03:30, resets ~06:30. An hourly
  ScheduleWakeup heartbeat is armed to dispatch the queued wave after
  reset (wave list below). Claude weekly budget ~50% — policy:
  authoring/review on Codex gpt-5.5 (5.6 NOT available on ChatGPT
  Codex, tested), Claude for verification/merges/browser/image-reading
  only.
- **All 27 workers from the last session are landed.** No open
  worktrees, no uncommitted coordinator work.

## Queued next wave (dispatch when Codex resets, ~06:30)

1. **X→en B1 overlays units 07–11** (nl-en, fa-en, prs-en) against the
   reviewed en realizations `b1_unit07..11` — closes B1 at 11+ units in
   every launch direction. Codex gpt-5.5 high; STRONG sibling-isolation
   rule in prompt; then fresh-context review; then both syncs.
2. **Feedback-attachments frontend UI** — image picker in
   `FeedbackWidget.tsx` per CONTRACT.md "Feedback attachments" section
   (backend is LIVE on both stacks, migration 0024). Claude Sonnet
   worktree worker (frontend lane), phone-viewport verification, then
   rebuild `--mode production.lan` and rsync `frontend/dist/` to
   `ramin@192.168.4.4:/home/ramin/LingoSquared/backend/web_dist/`.
3. **Practice-pack coverage**: en-nl units 43+, en-fa units 31+ (check
   disk), X→en units 43+ — per `docs/PRACTICE_VARIETY_AUDIT_2026-07-11.md`
   and the depth report; extend the per-direction backfill scripts;
   NEVER two workers in `scripts/_en_target_lexeme_common.py`
   concurrently (documented collision).
4. **Italian + Russian first waves** (adaptation mode): sources verified
   in `docs/content/SOURCES_ALL_LANGUAGES.md` — Italian FSI FAST (clean
   OCR), Russian yojik re-OCR remaster (clean Cyrillic). Standard
   pipeline: author → fresh-context review → import.
5. After (1) lands: re-measure practice/teaching depth (the
   variety-audit harness pattern) to confirm ≥10hr bar formally closed.

## Standing follow-ups (coordinator, not urgent)

- **Wrong-language display bug (Ramin's report)**: investigation found
  data+render layers clean; NEEDS Ramin's specifics (language/lesson/
  screen) to progress. Ask again when he's around.
- **Social login**: backend live both stacks, inert until env vars get
  real IDs (see Ramin list). Frontend buttons NOT built yet — build
  after his Google client ID exists (needs it for testing).
- **ja/ko typing IME decision** (product): jamo composition / kana input
  — present options to Ramin before any ja/ko typing exercises ship.
  Recognition/listen/word_order types are unblocked.
- **fa/prs register flags in locale files** (from the translation task:
  a few Iranian-leaning forms in prs.json, mixed formality in fa.json)
  — queue a small register-normalization pass.
- **§16 matching_pairs retrofit** (~50 undersized legacy exercises per
  big course, now compiler WARNINGS) — content lane backlog.
- **Defect registry Section 4**: append this session's review outcomes
  (nl-en Dutch-left class CLOSED by fixes+test; pack-lane 3 consecutive
  clean reviews → eligible for 1-in-3 sampling; new classes: script-
  constraint-two-layer (DB check + Pydantic literal) for new languages,
  romanized-source trap for ko/ja, Devanagari OCR trap).
- **German lane**: 25 validator-caught bugs (19 distractors + 6 shapes)
  block en-de/de-en imports. Another session's lane; if Ramin declares
  it dead, dispatch fixes.
- **Azure Farsi TTS**: built, needs `AZURE_SPEECH_KEY`/`_REGION` (Ramin).

## RAMIN'S LIST (only you can do these)

1. **Domain + Cloudflare Tunnel** (~$10/yr) — the one decision unlocking
   public HTTPS, OAuth return URLs, CORS origin, and
   `VITE_FEEDBACK_API_URL` in one move. Recommended before any external
   beta invite.
2. **Apple Developer Program** ($99/yr) → hand back bundle ID +
   Services ID. **Google Play Console** ($25) → just confirm. **Google
   OAuth Web client ID** (free, 10 min) → hand back the ID string.
   Full click-paths: `docs/ACCOUNT_SETUP_CHECKLIST.md`.
3. **Azure Speech key** (portal) — activates real Farsi TTS.
4. **Before ANY external beta user**: change live `ADMIN_EMAILS` from
   `admin@example.com` to your real email and register it first
   (documented in backend/CLAUDE.md deploy section).
5. **Your Dutch native review pass** + a phone QA evening on
   `http://192.168.4.4:8011` — the two human quality gates.
6. **Tell the coordinator which lesson/screen showed the
   wrong-language display bug** you reported — investigation is blocked
   on that detail.
7. Optional: decide fate of the German session (its 25 bugs + dirty
   files in the main tree); decide if/when C1/C2 planning starts.

## Key facts future sessions must not relearn

- Deploys to live from ≤0005 history MUST go fresh-DB (0004→0005
  forward-reference crash) — documented in backend/CLAUDE.md.
- Live DB backup exists: `~/lingosquared_backup_20260711_2358.sql.gz`
  (server) — pre-first-deploy state.
- `sync_dev_db.sh` picks the FULLEST course when demo courses share a
  language pair; groups packs per CEFR level (422 otherwise).
- Codex tasks share the MAIN working tree — never two tasks on the same
  file; commit per-task with explicit pathspecs; a "failed" Codex task
  usually died mid-flight platform-side — its partial tree work is real
  and a fresh continuation task finishes it cheaply.
- The safety layer blocks credential writes + live-DB destructive ops:
  compute what's computable, hand Ramin a paste-ready command for the
  rest. He knows the drill and prefers speed — minimize such asks by
  designing around them.

---

## Overnight session log (2026-07-12 ~04:15–10:00, autonomous coordinator)

All queued wave items landed; everything below is merged, reviewed
(fresh-context, full), validated, and pushed:

- **Feedback attachments frontend** shipped + live-browser-verified
  (upload→submit→DB row confirmed; RTL fa pass; Persian-digit counter).
  Production rebuild + rsync to 192.168.4.4 HELD for Ramin (deploy rule).
- **X→en B1 closed at 11 units** in all three launch directions
  (Codex-authored 07-11, Opus-reviewed: nl-en 0 defects, prs-en 0,
  fa-en 1 same-speaker distractor). Manifest wired, dev DB synced.
- **Two new compiler validators** (Codex): overlay matching_pairs
  accepted_answers must mirror realization pairs; listen audio must
  contain tested_text. Zero false positives corpus-wide; caught 4 real
  bugs (en-nl, en-ro ×3) — all fixed same session.
- **Italian + Russian launched as courses**: 12 fully-reviewed A1 units
  each (realizations + en-it/en-ru overlays), manifest-wired, imported
  to dev DB. Sources: FSI Italian FAST Vol 1, FSI Russian FAST (PD).
- **Practice packs**: +90 templates (en-nl 43-48, en-fa 31-36, X-en
  43-48) + backfill lexeme coverage; three Codex fix rounds were needed
  for lesson_categories/gloss gaps — the five-module iter_specs harness
  (see registry) is now the acceptance test for any backfill extension.
- **fa/prs UI locale register normalization** (fa: 102 values → formal
  شما; prs: 2 Dari fixes).
- **Local-model experiment done** (qwen3:14b): verdict in
  COORDINATOR_HANDBOOK — barred from learner-facing content.

### Depth measurement (scripts/measure_content_depth.py, teaching half)
- en→X teaching: en-nl 11.25h, en-fa 13.8h, en-prs 15.3h — all ≥10h OK.
- X→en teaching: nl-en / fa-en / prs-en ≈ 6.78h each (shared English
  realization). **QUESTION FOR RAMIN:** is the ≥10hr teaching bar
  per-direction or per-pair? Per-pair, every launch pair passes
  (18h/20.6h/22h); per-direction, X→en needs ~10 more English units
  (they'd be shared by all three directions — one authoring effort).
- Practice half (measured post-sync6, real lexeme pool, dev DB):
  en-fa ~219h, en-nl ~159h, en-prs ~188h, fa-en ~148h, nl-en ~148h,
  prs-en ~145h — **all six directions clear the ≥10hr practice bar by
  an order of magnitude. The practice-depth launch gap is CLOSED.**
  (Note: 60-90% of templates are "thin" per the measure's variety
  metric — quantity passes; the format-monotony work from the variety
  audit remains the quality follow-up.)

### New footguns learned tonight
- sync_dev_db.sh's admin token can expire mid-run (30-min access token,
  long sync) → later imports 401. Re-run works; a token-refresh in the
  script is Codex backlog.
- Never run sync while a merge is mid-conflict (it read conflict-marker
  YAML from the main tree once — harmless, but sequence syncs after
  merges complete).
- Codex self-reported acceptance ("spec counts OK") missed full-iteration
  failures twice — always run the exact harness yourself before commit.


### X→en teaching depth after units 59-68 (measured ~17:30)
Ten new shared English A1 units (59-68, all reviewed, all three overlay
sets reviewed) moved X→en per-direction teaching from 6.78h to **7.90h**
(6.05 A1 + 0.82 A2 + 1.03 B1). The new 4-lesson topical units are
lighter (~22 cards ≈ 0.11h each) than legacy units, so closing the
remaining ~2.1h purely with more A1 units needs ~19 more. Per-PAIR the
bar passes everywhere already (en↔nl 19.2h, en↔fa 21.7h, en↔prs 23.2h).
**Paused further X→en unit waves pending Ramin's per-direction vs
per-pair ruling** — if per-direction, the efficient path is probably
denser B1/A2 English units (B1 is only 1.03h) rather than more A1.
