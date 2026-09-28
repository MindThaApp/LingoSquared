# Session handoff — 2026-09-28

Read this first. It supersedes the 2026-09-02 handoff for "what next" (that doc is still
the reference for the 14-tier content sweep and the live-deploy recipe). **This file
contains no credentials — keep it that way.**

## What this session did

1. **Four-way app review** (frontend code, backend + grading, product/curriculum, live
   play-through). Consolidated ranked fix list (private artifact):
   https://claude.ai/artifact/7xcm4p4jNeqEogF3Kp4Qpk
2. **Fixed + committed + pushed:**
   - `fix(grading)`: NFC + quote folding; non-dictation free text ignores punctuation
     (opt-in `punctuation_strict`); multi-accepted-answer items get typo tolerance;
     string fill_in_blank gets typo tolerance. Corpus harness in
     `scripts/grading_harness/` (`harness2.py --grading <grading.py> --compiled-dir <dir>`;
     compile the corpus first with `compile_all.py <repo> <outdir>`).
     Result on ~10.8k items: punctuation / smart-apostrophe / NFD perturbations now 0
     incorrect; Latin one-letter typos on multi-answer items 6,426 incorrect → 4.
     Full backend pytest green (isolated DB).
   - `fix(frontend)`: lesson MCQ options + word-order tiles shuffled (display only; payload
     unchanged). Was: correct answer = option 1 in 100% of lesson MCQ items. Full build +
     vitest 61/61 + live play-through verified.
3. **Cloud briefs** for frontend fixes: `iCloudDrive/dev/cloud-briefs/FRONTEND_BRIEFS.md`
   (A lesson-runner robustness, B stale data, D RTL/a11y/input, C next-lesson). Brief D is
   now UNBLOCKED (shuffle fix is pushed). C after A+B merge. Cloud sessions open PRs into
   `fix/launch-gate-content-review-wave1`; the coordinator reviews, merges, live-verifies.
4. Local stack is running on the old Mac (API :8020, SPA :8011, Vite :5180) — irrelevant
   on the new machine.

## Next up (in order)

1. **Arabic hamza "almost" (Ramin APPROVED 2026-09-28, ar ONLY, never fa/prs).** Codex
   stopped honestly: `grade()` receives `script` but not the target language code, so it
   can't tell ar from fa/prs. Needs the language code threaded from `router.py` answer /
   practice / checkpoint call sites into `grade()`. Brief is in the old session scratchpad;
   re-write: fold أ إ آ → ا for ar only, verdict "almost" with a spelling note; tests: ar
   "اهلا بك" vs "أهلا بك" → almost; fa "ادرس" vs "آدرس" → incorrect.
   Same change should wire `punctuation_strict` from feedback_meta in router.py.
2. **Backend (Codex lane)** — from the backend audit, all VERIFIED:
   - `/lessons/{id}/start` 500 on duplicate insert (race) → upsert / ON CONFLICT. Shows up
     in browsers as a CORS error.
   - Refresh/logout argon2-verify EVERY refresh token ever issued (49 ms each, never
     purged) → sha256 + unique index + purge.
   - `GET /me/quests` awards XP + streak when nothing is due (clear_reviews quest) → require a
     review answered today; don't mutate in a GET.
   - Auto-admin on self-registration by email + default JWT secret accepted → promote via
     CLI only; refuse to boot on defaults.
   - Removed content never retired (import) → `retired_at` column + filters.
   - Lesson completable with zero answers; answers not idempotent (use existing
     `client_operation_id`); lost XP updates (atomic increment); stale streak on read.
3. **Content/audio:** dialogue_comprehension items have no audio_text (298 in nl A1);
   🔊 on digit prompts speaks the answer (18 nl A1 items).
4. **Roadmap (product review):** next-lesson path (brief C), fa/prs audio (needs Azure key
   from Ramin), interleave teaching cards with exercises, working push reminders + goal
   picker, tap-to-build word bank for A1/A2, rebuild A2 for launch paths (30+ units), replace
   C1 "repeat the exact paragraph" production. Pause new tiers for non-launch languages.

## Needs Ramin

- Rotate the server SSH password and the live admin login (both were in plaintext in the
  untracked 2026-09-02 handoff); change the admin email off the default.
- Azure Speech key for Farsi audio.
- Live server 192.168.4.4: host is up but app containers are down; nothing from 09-02 or
  this session is deployed yet. Deploy is authorized once the verification bar passes.

## Branch state

`fix/launch-gate-content-review-wave1`, pushed to origin (MindThaApp/LingoSquared). Unmerged
to master.
