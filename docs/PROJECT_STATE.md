# Project state — what exists today

**Reference, not rules.** This file is deliberately NOT auto-loaded (root
`CLAUDE.md` is, and stays rules-only so every worker in every lane doesn't pay
for state they don't need — see "How this documentation set works" there).
Read this when you need to know WHAT EXISTS. Full chronological history is in
`docs/BUILD_LOG.md`; the current session's state is in the latest
`docs/SESSION_HANDOFF_*.md`.

## What's shipped (all live-verified; full detail per phase in BUILD_LOG)

Phases A–F all shipped and live-verified. One line each; the *Invariants*
are standing rules, not history:

- **Phase A (lexeme-level SRS)** — SRS schedules lexemes not exercise
  instances; `user_lexeme_srs`, `GET /me/reviews/due`,
  `POST /reviews/session`, `POST /reviews/items/{id}/retry`; adaptive
  recognition→structured→production ladder by mastery. *Invariant:* every
  migration after 0001 must be fresh-migrate-safe (see backend/CLAUDE.md).
- **Phase B (in-lesson error recycling)** — `LessonRunnerPage` recycles
  misses to queue end; 2 misses → non-blocking "copy it" pass; ≤2 due
  reviews prepend when `courseId` is known (via route `state`). Frontend-only.
- **Phase E1 (HomePage review CTA)** — primary CTA "Review — N due" when
  due; `ReviewPage.tsx` moved off dead `/me/reviews` onto `/reviews/session`.
- **Phase C (typo tolerance + feedback_by_option)** —
  `result: correct|almost|incorrect`, Damerau-Levenshtein distance-1,
  per-language strictness via `Language.script`, `orthography_strict`
  override, Arabic/Persian script-confusion never forgiven;
  `feedback_by_option` JSON-encoded into `Exercise.feedback`.
- **Phase C follow-up (`case_sensitive` flag)** — default `False` sibling
  of `orthography_strict`; a case-only mismatch is hard-blocked to
  `incorrect`, never the "almost" path (else it counts correct for
  XP/SRS). Exercise-level only, not yet in Endless Practice.
- **Phase E2 (timezone-aware streaks)** — `User.timezone` (migration
  0009); `record_activity()`/`activity_day_bounds()` take a
  `user_timezone` param (UTC fallback). *Invariant:* grading success is
  `quality >= 3`, never a truthiness check on `correct` (now can be the
  string `"incorrect"`).
- **Phase E3 (streak freeze + daily quests)** — one earned/auto-consumed
  freeze (migration 0010); `GET /me/quests` = 3 live-computed quests,
  `QuestCompletion` (migration 0011) pays XP once per user/quest/day.
- **Phase D (recorded audio)** — `POST /admin/media/upload` +
  `GET /media/{key}` serving `backend/media_assets/{key}.mp3` (404 for
  unrecorded keys is expected); compiler rejects NEW embedded-"Name:"
  dialogue cards (`TextBlock.speaker` for splits); `speak()`/`SpeakButton`
  chain (see frontend/CLAUDE.md). *Not done:* re-authoring existing
  dialogue cards (CONTENT lane).
- **Phase F (unit checkpoint / test-out)** — `POST /units/{id}/checkpoint`
  = 12–15 items (not gated on completion), `orthography_strict` forced
  `True`, never touch per-item SRS; `.../checkpoint/result` scores once
  (≥80% passes), consolidates SRS only for untracked lexemes (0.5, +3d),
  idempotent, 1-hr retake delay (advisory lock + `429`);
  `GET /courses/{id}/units` returns `checkpoint_passed`. Migration 0012.
- **Phase H (dictation exercise type)** — 2026-08-03 (migration 0027): hear a
  TTS target-language sentence (no source text) → type it, graded
  **orthography-strict by type** (a 1-char typo is wrong, unlike tolerant
  `listen_type`; author `orthography_strict:false` overrides). Reuses
  `Translation.tsx` (no new component); registered across all 9 sites
  (enum/DB-constraint/compiler/grading/shared-union/renderer/PROMPTS-test/
  CONTRACT). Course-content only (not Endless Practice); TTS-only languages
  (nl now; fa once Azure key set; NOT prs). Verified: strict grading end-to-end
  + full pytest + PROMPTS guardrail. **Live across nl A2 (10 units, 20 ex) +
  all 11 en-nl B1 units (22 ex) = 42 dictation exercises**, each reusing an
  already-taught sentence + existing audio, orthography stripped of terminal
  punctuation for consistent strict grading (fresh-context reviewed per tier).
  Spec:
  `docs/DICTATION_EXERCISE_SPEC.md`; authoring: AUTHORING_GUIDE §14a.
- **E4 (web push)** — 2026-07-07 (`784da03`, migration 0016): VAPID
  subscribe/unsubscribe + admin-triggerable notify-due-reviews. No cron.
- **Mic-based speaking + STT** — `speak_response`/`speak_repeat` capture +
  STT via the free-text path; client-side WASM Whisper primary (zero audio
  leaves device), self-hosted `faster-whisper` (`POST /stt/transcribe`)
  fallback, never a cloud STT API. *Invariant:* Whisper runs
  `dtype: "fp32"` (see frontend/CLAUDE.md).
- **Per-language TTS speech-speed** — `/tts` optional `speaking_rate`
  (1.0, 0.25–2.0); per-device per-language `localStorage` pref (see
  frontend/CLAUDE.md). *Open:* a live-tab slider click-through was never
  done — visual close-out next live browser session.

- **Speaking suite (2026-07-13)** — pronunciation feedback (`/stt/transcribe`
  `detail=words` → per-word confidence; clarity heuristic, NOT accent scoring;
  server path only), **endless pronunciation practice** (`mode=speaking`,
  weakest-SRS-lexeme-first `speak_*` items) and **endless conversation
  practice** (`mode=conversation`, branching node graph, re-prompts instead of
  dead-ending). All zero-runtime-LLM. *Invariant:* `conversation` stays OUT of
  `ExerciseType` (see frontend/CLAUDE.md). **Live-played 2026-07-14** on
  en→nl with a fresh account (typed path): speaking batch renders + grades,
  conversation advances/re-prompts/terminates, server STT `detail=words`
  verified with real TTS audio. Live-play also found the modes were
  UNREACHABLE (no UI ever sent `mode`) — fixed: the practice feed now has a
  Mixed/Speaking/Conversation selector (per-device preference), plus a
  `speak_response` instruction fix ("Say it in Dutch." over the English cue).
  Still not verified: real-mic capture + `PronunciationFeedback` rendering
  in-browser (needs a human with a microphone — Ramin, with the APK test).
- **Android APK (2026-07-13)** — `android-shell/` (Capacitor wrapper around the
  real web build) + `.github/workflows/android-apk.yml`. Debug-signed, LAN-only,
  deployed to `/home/ramin/shared/lingo.apk`. **Installed and working
  2026-07-14** after two stacked fixes found by Ramin's first real install:
  live `CORS_ORIGINS` needed the WebView origin `https://localhost`
  (server-side env fix + `--force-recreate`, no rebuild), and the
  https-origin WebView blocked mixed-content calls to the http:// LAN API
  (`allowMixedContent: true`, rebuilt + redeployed, checksum-verified;
  flagged as a release-gate item — a store build needs real TLS instead).
  Guest session confirmed working by Ramin. Full lesson + real-mic
  speaking play-through still pending.

*Still remaining from the upgrade program:* D2's dialogue-content
re-authoring and C1's feedback_by_option content pass (both CONTENT
lane). The mechanism is fully built across every phase; the real
remaining path to launch is full-depth content for en-nl/en-fa/en-prs.

## Landed 2026-07-22 — NOT yet live-browser-verified

Separate from the list above precisely because none of it has been played
through in a live browser yet:

- **Perso-Arabic formatting normalization in grading** — grading normalizes
  ZWNJ (U+200C) and harakat before comparison, so an answer differing from the
  expected string only in those grades `correct`, never `almost`.
  Script-confusion (ي/ی, ك/ک, ة/ه, ۀ/ه, ى/ی) is still never forgiven.
- **Demo courses are no longer seeded by default** — `python -m
  app.content.seed` bootstraps languages + achievements only; the four demo
  courses need `--with-demo-courses` (or `LINGO_SEED_DEMO_COURSES=1`). They
  were shadowing the real launch courses in the picker.
  `backend/scripts/remove_demo_courses.sql` removes the 4 already present in
  the dev and live databases. In-process callers (`backend/tests/conftest.py`)
  keep the old default, so no test/e2e fixture changed.
- **`scripts/compile_content.py` hard-errors** on an invalid teaching-card
  `kind`, an invalid exercise `type`, and over-length titles/`content_key`s
  (previously accepted or warned).
- **Auth has an explicit "backend unreachable" state** — a signed-in user is no
  longer bounced to the login screen when the backend can't be reached. Guest
  logout now requires an explicit confirmation.
- **New docs/tooling** — `docs/content/PRACTICE_PACK_RECIPE.md` (practice-pack
  authoring recipe) and `scripts/check_dari_register.py` (Dari-vs-Iranian-
  Persian dialect/register checker, defect-registry class 1.28).

## Scope & publish-gate decisions (2026-07-05)

- **End goal is genuine fluency (full CEFR A1→C2), but publish is a much
  earlier, separate gate.** Publish-gate language set: **en↔nl and
  en↔fa/prs only** (6 directed paths) — the languages Ramin can
  personally verify. The other 15 paths keep building as post-launch
  drip content, not blocked.
- **Publish-gate quality bar: "very usable, minimum bugs," not a phase
  checklist.** Beta users on the 3 launch pairs must hit essentially no
  functional breakage. The Claude session earns this via the full
  VERIFICATION BAR (below) on the actual lesson/review/practice flows
  BEFORE any user sees it — the report-button → triage loop is the next
  layer, not a substitute for pre-launch verification.
- **Publish-gate content depth: ≥10 hrs new teaching + ≥10 hrs practice
  + working scored module checkpoints, per launch pair.** Practice hours
  come from the Endless Practice engine (built for all 6 launch
  directions — en-fa 124, en-nl 240, en-prs 36, fa-en 86, nl-en 327,
  prs-en 86 templates per `scripts/practice_manifest.txt`); actual
  hour-depth vs the bar hasn't been separately measured. Phase F unit
  checkpoints are a hard publish-gate requirement. Detail:
  APP_SPEC_FOR_FABLE_REVIEW.md §1 + `project-lingosquared-roadmap` memory.

## What's built and verified live

Auth; all 10 languages (fa/prs fully separate, correct RTL + script
metadata); courses → units → lessons → all 20 exercise types (dictation added
2026-08-03); SM-2 review
(being replaced by lexeme-level SRS); gamification (XP/streak/achievements);
reading/writing vs. speaking sections with server-enforced unlock; CEFR
A1–C2; teaching phase before exercises; in-app content-issue reporting +
admin triage + coverage dashboard; Endless Practice generative feed (all 6
launch directions, zero runtime LLM calls); on-screen virtual keyboard for
non-Latin scripts; self-reported level check with recommended-unit badge
(not a placement system — rejected); mic-based speaking with client-side
WASM Whisper STT.

(Area-specific known limitations live in each area's CLAUDE.md:
seeded-course counts + content limits → content; deploy/backend →
backend; STT/frontend → frontend.)

### Cross-cutting known limitations & rejected scope

- No SELF-SERVE password reset or email verification. **Admin user
  management IS built** (2026-07-12, migration 0026): admin can create a
  user with a server-generated one-time temp password, reset a password,
  list/search, deactivate/delete, promote/demote admins, and unlock
  lessons — which is how beta testers get logins without an email service.
  `is_admin` is a persisted column OR'd with `ADMIN_EMAILS` (the env var
  still bootstraps); demoting/deactivating the LAST active admin is
  refused. *No admin UI yet — API only.*
- **Refresh tokens ARE built**
  (2026-07-10, `565f66c`, migration 0021): 30-min access + rotating
  refresh tokens with reuse-detection revocation, `POST /auth/refresh`/`logout`.
- No functional mobile app yet; an Expo scaffold exists (`mobile/`,
  2026-07-10, Phase 0 proof-of-concept only — proves Metro resolves
  `@lingo/shared` through the monorepo). Reuses the existing JWT/JSON API.
- **Rejected, don't re-propose without a strong new reason:** hearts/lives,
  leagues/leaderboards, gems/currency, runtime-LLM content generation, a
  placement-quiz enrollment system (self-report + checkpoint test-out is
  the accepted alternative).
