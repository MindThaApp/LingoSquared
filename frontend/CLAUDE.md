# Frontend — rules for `frontend/**`

This file auto-loads when you work under `frontend/`. `frontend/src/**` is
**Claude's lane** (see root `CLAUDE.md` → POLICIES → Division of labor).
Root `CLAUDE.md` still governs cross-cutting footguns (git/worktree/agent,
the npm-install-in-worktree rule, the shared-browser-page rule) and the
non-negotiable verification bar.

## Build & verification

- **Frontend build: the FULL `npm run build`, never just `tsc --noEmit`**,
  and live-browser-verify anything user-facing — the verbatim rule (and
  why) is the non-negotiable Verification Bar in root `CLAUDE.md`.

## Answer-payload-shape contract (grading correctness)

- **Whenever an exercise component's answer payload isn't
  string/string[], read what `accepted_answers` actually looks like across
  the REAL corpus before trusting either end, and make `grade()`
  canonicalize every authored shape** — a single successful live test with
  one exercise does not rule out a content-shape-dependent bug. Confirmed
  twice:
  - `matching_pairs` — `MatchingPairs.tsx` submitted a flat
    `Record<left,right>` but content authors an array of `{left,right}`;
    every matching_pairs exercise scored wrong and rendered `[object
    Object]`. Fixed frontend submit + shared `formatAnswer.ts`; and
    `grade()` canonicalizes flat-dict OR `{left,right}[]` (Endless
    Practice's `derive_answer()` emits the flat dict). Detail: BUILD_LOG 2026-07-05.
  - `word_order`/`listen_order` — `WordOrder.tsx` always submits a list,
    but 146/173 (~84%) exercises author a space-joined string;
    list-vs-string never compared equal. New `canonical_order_tokens()`
    canonicalizes either shape. Detail: BUILD_LOG 2026-07-07.
- **Never key or disable a click-to-match / click-to-build option tile by
  its TEXT VALUE — always by its INDEX.** Content legitimately maps many
  lefts onto one right (nl A1 unit13: 3 items → `lekker`, 3 → `leuk`), so
  value-keying disabled every tile sharing that text on the first match;
  the remaining lefts became unmatchable, Check never enabled, and the
  lesson was **impossible to complete** (a hard block in the en-nl launch
  pair, found live 2026-07-12 — the compiler cannot see this, only playing
  it can). Corollary: once you index-key, `0` is a falsy index, so every
  "is this matched" test must be `!== undefined`, never a truthiness
  check. Applies to `MatchingPairs.tsx` and any future tile/bank UI.
- **Exercise-type registration must be checked exhaustively: `comm`-diff
  every `type:` in `docs/content/realizations/` against every `case` in
  `ExerciseRenderer.tsx` after any content or exercise-type change** — a
  mismatch compiles clean and only crashes a real lesson in the browser.
  Detail: BUILD_LOG.

## RTL / script direction

- **Any frontend component that assembles a raw token array into a
  click-built sequence (word_bank, future letter/tile banks) needs an
  EXPLICIT `dir` on its own render container — it inherits direction from
  nowhere.** Farsi/Dari tiles assembled LTR on screen (grading was always
  correct; pure display bug); fixed via `answerDirectionForExercise()` on
  `WordOrder.tsx`'s containers. Applies to ANY future RTL/non-LTR
  language. `MatchingPairs.tsx` does NOT have this (two fixed columns,
  not a sequence). Detail: BUILD_LOG 2026-07-09.

## Audio / TTS / STT (client side)

- **`speak()`/`SpeakButton` priority chain: recorded asset → Google TTS →
  browser speechSynthesis → honest fallback** (never silently dead). Wired
  into the listen-type exercise components via each prompt's
  `media_asset_key`. Detail: BUILD_LOG Phase D.
- **STT: client-side Whisper must run `dtype: "fp32"`** (~150MB, cached)
  — every quantized dtype throws an onnxruntime-web session-creation bug
  at the pinned `@huggingface/transformers` version; heavily commented in
  `whisperWorker.ts` so it isn't "optimized" back to a quantized dtype.
  Whisper may transcribe number words as digits ("zeven"→"7"), missing
  word-form `accepted_answers` — accepted caveat, don't chase with digit
  tables. fa/prs UI strings for voice-answer not yet translated. Detail: BUILD_LOG 2026-07-06.

## Speaking features (2026-07-13)

- **`conversation` is deliberately NOT in `ExerciseType`.** It is a
  practice-feed-only, MULTI-TURN item (`mode=conversation`) whose prompt
  carries a node graph, rendered by `ConversationRunner.tsx` — `PracticeCard`
  branches on `item.type === "conversation"`, bypassing the one-shot
  `ExerciseRenderer`. It lives in `PracticeItemType = ExerciseType |
  "conversation"`; `asExerciseType()` narrows (and throws) for the review/
  checkpoint/lesson runners, which can never receive one. **Adding it to
  `ExerciseType` breaks the exhaustive exercise-type-registration check —
  that guard exists because six unregistered types once shipped and only
  crashed in a real lesson. Do not "simplify" this.**
- **Pronunciation feedback is a CLARITY signal, never an accent score.**
  `POST /stt/transcribe` with `detail=words` returns per-word
  `probability` (the model's confidence it heard that word). Low confidence
  means the word was unclear — it does NOT mean the learner is wrong, and the
  UI must never label it "wrong pronunciation" (`PronunciationFeedback.tsx`).
- **Only the SERVER STT path returns word confidences** — the client WASM
  Whisper model does not expose token probabilities. So absent feedback means
  "no signal", NEVER "you were perfect": the component renders nothing at all
  rather than an all-clear it can't justify.

## Per-device `localStorage` preference patterns

Several user preferences are per-device `localStorage` values (not
account/backend fields), because `/tts` never caches synthesized audio
across users/requests so there's no shared-cache-correctness reason to
push them server-side. Follow this precedent for future preferences:

- Per-language TTS voice preference.
- Per-language TTS speech-speed (`ttsSpeedPreferences.ts`; `/tts`'s
  `speaking_rate` baked in server-side for cloud TTS,
  `utterance.rate`/`HTMLMediaElement.playbackRate` client-side for the
  fallbacks). Wired via `api/tts.ts`'s `speak()` chokepoint.
- STT mic/keyboard toggle.

## Where the frontend runs

- **Frontend (dev):** `cd frontend && npm run dev`. Port 5173 is often
  taken; Vite falls back to 5174 — check terminal output. `.env`'s
  `VITE_API_BASE_URL` points at localhost or 192.168.4.4:8010. (The
  backend's `CORS_ORIGINS` must list whatever port you actually run on —
  see `backend/CLAUDE.md`.)

## Feedback/issue-report collection (2026-07-09)

`POST /feedback` (unauthenticated, works from logged-out screens), a
`page_path` column on `ContentIssueReport`, and an every-page
`FeedbackWidget.tsx`. The multi-deployment fix: the frontend submits
feedback via a separate configurable base URL `VITE_FEEDBACK_API_URL`
(falls back to `VITE_API_BASE_URL` when unset), so a published
"clone-and-run-locally" build can point every install at one central
collector by default. REST-only, mobile-ready. Full spec: CONTRACT.md.

**Standing gap: `VITE_FEEDBACK_API_URL` has no real value set yet** — it
needs ONE stable internet-reachable collector URL. An infra/deployment
decision for Ramin (tunnel/DDNS/hosted domain), not for a Claude session
to invent unilaterally. **Flag this again before ever publishing a
"run-locally" distribution** — until then local-install feedback only
reaches whatever backend that install happens to run against.
