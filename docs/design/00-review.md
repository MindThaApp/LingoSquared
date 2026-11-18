# LingoSquared (Auvel) — product, design and architecture review

Date: 2026-11-18. Read at `fix/wsl-handover-followups` @ `06d01fbea`. Code was read, not run.
Paths are relative to the repo root; `f/` is short for `frontend/src/`, `sh/` for `packages/shared/src/`.

Companion files: `01-core-spec.md` (the target app) and `02-platforms.md` (where to ship it).

Related earlier work, which this review builds on and does not repeat:
- `docs/APP_SPEC_FOR_FABLE_REVIEW.md` §9 "Delight / polish" on branch `origin/docs/delight-spec` (not merged). Its ranked gap list (§9.11) is accurate; where I agree I cite it as "D-n".
- `.local/logs/msstore-pwa-readiness.md`, `.local/logs/offline-windows-feasibility.md`, `.local/logs/a11y-2026-11-07.md`.

## 1. Summary

The app is a careful, correct, accessible web client on top of a server that does all the thinking. Its strengths are unusual for a solo project: real WCAG contrast work with a unit test, working RTL for fa/prs, a self-hosted Persian font, honest error states, a typed API boundary shared with a mobile scaffold, and a deep content pipeline.

It does not yet feel like a great app, for three structural reasons and one cosmetic one:

1. **Every tap that matters waits on the network.** Grading, XP, streak and SRS all live on the server, and the app shows a blocking screen when the server is unreachable. No amount of animation makes that feel instant.
2. **A lesson is fragile.** Lesson state lives in component memory. A reload, a phone evicting the tab or a crash throws it away, and the app tells the learner so.
3. **There is no "one thing to do now".** Home is a dashboard of numbers with the main action at the bottom; onboarding ends on a map, not in a lesson.
4. **The surface is unbranded.** Emoji stand in for icons, the most repeated moment (answer feedback) has no motion, loading is the word "Loading…", and spacing and type are ad hoc.

The first two are architecture; fixing them is what unlocks both delight and every store platform. The spec is ordered around that.

## 2. What is already good (keep it)

| Area | Evidence |
|---|---|
| Colour contrast in both themes, measured and tested | `f/index.css:35-72`, `:100-131`; `f/a11yTokens.test.ts` |
| Global focus ring and reduced-motion floor | `f/index.css:163-166`, `:1480-1484` |
| Safe-area insets for installed PWA | `f/index.css:181`, `:197`, `:242-246` |
| Persian font done properly (unicode-ranged, variable weights) | `f/index.css:15-25`, `:83` |
| Direction handled per content block, not globally guessed | `sh/lib/scripts.ts`; `f/components/exercises/ChoiceOptions.tsx:50`; `f/pages/LessonRunnerPage.tsx:362` (`<bdi>`) |
| A failed submit is never shown as a wrong answer; answer kept; Retry | `f/pages/LessonRunnerPage.tsx:295-313`, `:836` |
| Typed API client shared across web and mobile, with injected storage | `sh/api/client.ts`, `sh/api/endpoints.ts:82-422`; `f/main.tsx:36-62` |
| Locales lazy-loaded (only `en` in the entry bundle) | `sh/i18n/index.ts:9-24` |
| Route-level code splitting, measured | `f/App.tsx:26-65` |
| Focus-trapped dialogs with Escape | `f/components/QuitConfirm.tsx:33-63` |
| Push permission asked in context, after a lesson | `f/pages/LessonCompletePage.tsx:212` |
| Audio fallback chain and offline audio cache with range support | `f/api/tts.ts`; `frontend/public/sw.js:152-191` |
| Server-side idempotency key for answers exists | `backend/app/api/router.py:660-676`, `backend/app/schemas/api.py:151` |
| Store-ready manifest basics | `frontend/public/manifest.webmanifest` (id, scope, categories, icon set) |

## 3. Findings, ranked by user impact

Effort: S = up to half a day, M = 1–3 days, L = a week or more. "QW" marks a quick win.

### P0 — changes how the app feels on every session

**R1. The app cannot be used without a live server, and every answer is a round trip. (L)**
- The client never has the correct answer. `LessonApi.answer` posts to `/exercises/{id}/answer` for each exercise (`sh/api/endpoints.ts:216-217`; called at `f/pages/LessonRunnerPage.tsx:291`). Review and practice do the same (`f/pages/ReviewPage.tsx`, `f/pages/PracticeFeedPage.tsx:105-125`).
- The service worker caches the shell only and explicitly excludes the API (`frontend/public/sw.js:1-6`, `:25`).
- When the session cannot be verified, the whole app is replaced by a "session unavailable" screen (`f/components/layout/ProtectedRoute.tsx:96`, screen at `:33-86`). An installed PWA opened on a train shows that screen and nothing else.
- Effect: the "Check" button is as fast as the network. On a phone on mobile data this is the difference between Duolingo-fast and form-submit-slow. It also blocks the Store story ("works offline") and makes the Tauri plan a port rather than a wrapper.
- Fix direction: local grading and a local progress store with an outbox (spec §8). This is the single largest item and everything else is ordered around it.

**R2. Lesson progress is volatile and the app admits it. (M)**
- The runner holds about 25 `useState` values and nothing is persisted (`f/pages/LessonRunnerPage.tsx:124-155`; no `sessionStorage`/IndexedDB use anywhere in `f/`).
- Home says so: "A lesson always restarts from the beginning." (`sh/i18n/locales/en.json:366-368`; button at `f/pages/HomePage.tsx:344-355`).
- On phones the OS discards background tabs routinely. Answer one phone call mid-lesson and the lesson is gone.
- QW version (M): snapshot `{lessonId, queue, completedCount, history ids, totalXp, missedWords}` to IndexedDB on every Continue; restore on mount; change the Home card to "Resume". The server already has per-exercise attempts, so nothing server-side changes.

**R3. The most repeated moment has the least craft: answer feedback. (M) — D-1**
- The banner appears with no transition; option state snaps (`f/index.css` `.feedback-banner`, `.exercise-option`; render at `f/pages/LessonRunnerPage.tsx:383-435`).
- Sound is two sine beeps and one buzz, synthesised (`f/lib/answerCue.ts:5-9`), fired from one place (`f/components/AnswerFeedbackExtras.tsx:38`). There is no completion sound and no "almost" cue.
- The progress bar animates `width` (`f/index.css:425`; `f/pages/LessonRunnerPage.tsx:798`), which is layout work on every answer.
- The feedback banner sits in normal flow under the exercise, so on a small phone with the virtual keyboard open, the verdict and Continue can be below the fold.

**R4. Home has no single next action. (M)**
- Order on screen: error banner, streak-risk card, freeze notice, greeting plus goal bar, four stat tiles, quests, review card, then at the bottom the lesson card (`f/pages/HomePage.tsx:138-361`). The primary button is the last thing on the page and is demoted to secondary whenever reviews are due (`:351`, `:357`).
- Six queries fire on mount (`:32-43`); any one failing raises a page-wide red banner (`:54-60`, `:138-145`).
- Numbers render as "—" then pop in; there are no placeholders (`:234`, `:247`).
- Compare Apple Fitness or Things "Today": one ring, one list, one obvious thing to do.

**R5. Onboarding ends on a map, and the UI language ignores the learner's own language. (M) — D-3**
- Three stages (course → goal → placement/beginning) and then a redirect to the course path (`f/pages/OnboardingPage.tsx:11`, `:108-111`). The first exercise is at least three more taps away.
- The UI language defaults to English unless a stored choice exists (`f/i18n/index.ts:17`); `navigator.languages` is never read. For the X→en half of the product (a Dari speaker learning English) the first screens are in the language they do not yet read. This is a P0 for those learners and a QW (S).
- Guest mode exists but asks for a typed username first (`f/pages/LoginPage.tsx:66`).

### P1 — noticeable friction or a visible quality gap

**R6. Lesson start waits on a review warm-up it may not need. (S, QW)**
`f/pages/LessonRunnerPage.tsx:197-221` runs `ReviewApi.due()` then `ReviewApi.session()` in series, and line `:534` keeps the "Loading…" text up until both return, even when the lesson itself is already loaded. Fetch in parallel with the lesson and never block first paint on it; or move warm-up to the end of the lesson.

**R7. Phone keyboards will "correct" target-language answers. (S, QW)**
The answer inputs set `lang` and `dir` but none of `autoCapitalize`, `autoCorrect`, `autoComplete`, `spellCheck`, `enterKeyHint`, `inputMode` (`f/components/exercises/Translation.tsx:51-61`, `FillInBlank.tsx:35-36`; a repo-wide search for those attributes returns nothing). A Dutch answer typed on an English keyboard gets autocorrected and capitalised, then graded. Add `autoCapitalize="none" autoCorrect="off" autoComplete="off" spellCheck={false} enterKeyHint="done"`.

**R8. Loading states are text, and `.page-loading` has no style. (M) — D-2**
`f/App.tsx:85`, `f/pages/LessonRunnerPage.tsx:508`, `:535`, `f/pages/ReviewPage.tsx:242`, `f/pages/VocabularyPage.tsx:138`, `f/pages/PracticeFeedPage.tsx:448`. There is no `.page-loading` rule in `f/index.css`, so it renders as an unstyled line at the top-left. No skeletons anywhere.

**R9. Emoji are used as icons next to a real icon set. (S–M, QW for the nav)**
`lucide-react` is installed and used on Home (`f/pages/HomePage.tsx:4`), yet the top bar uses 🔥 ⭐ 💎 (`f/components/layout/NavBar.tsx:63`, `:73`, `:83`), hearts are ❤️/🤍 (`f/components/HeartsBadge.tsx:13`), audio is 🔊 (`f/components/SpeakButton.tsx:56`), the mic is 🎙️ (`f/components/VoiceAnswerButton.tsx:81`), and hero states are 🎉 🤔 💪 ✅ 📖 🧭 ⚠️ 📡 (`f/pages/LessonCompletePage.tsx:157`, `CheckpointPage.tsx:200`, `:214`, `ReviewPage.tsx:261`, `:333`, `VocabularyPage.tsx:156`, `NotFoundPage.tsx:8`, `ErrorBoundary.tsx:49`, `ProtectedRoute.tsx:36`). Emoji look different on Windows, Android and Apple, cannot take the theme colour, and read as a prototype. Flags as emoji (`f/pages/CoursePickerPage.tsx:105`) do not render at all on Windows, which shows two letters instead — a real defect for the Store build.

**R10. Keyboard use on desktop is partial. (M) — D-4**
- Options are `role="radio"` buttons without roving tabindex or arrow keys (`f/components/exercises/ChoiceOptions.tsx:50-63`); the ARIA radio pattern promises arrows.
- Only three key handlers exist in the whole app (`QuitConfirm.tsx:63`, `GlossableText.tsx:60`, `WritingPrompt.tsx:56`). No number keys, no audio key, no Escape-to-quit in a lesson, no shortcut sheet. For a Windows Store app this is the main input path.

**R11. No design tokens beyond colour and two radii. (M) — D-5, D-10**
- 517 inline `style={{…}}` objects in `f/` (47 in `VocabularyPage.tsx`, 35 in `LessonRunnerPage.tsx`, 34 in `HomePage.tsx`).
- 22 distinct font sizes between 0.65rem and 2rem in `f/index.css`; 25 distinct spacing values (2–48px, including 5, 7, 9, 13, 15, 17, 22, 26); 11 distinct radii.
- Motion uses raw literals (`f/index.css:369`, `:425`, `:553`, `:717`, `:1653`).
- Text below 13px exists (0.65rem, 0.7rem, 0.72rem, 0.75rem).

**R12. Profile is a single scroll of fourteen cards. (M)**
Account, sign-in methods, password, stats, gamification, skills, achievements, daily goal, vocabulary link, notifications, speech speed, feedback cues, transliteration, voice, crash reports, export, danger zone are all siblings (`f/pages/ProfilePage.tsx:117-265`). Settings are not grouped, not searchable, and the dangerous actions share a page with everyday toggles.

**R13. Navigation has two near-identical destinations and hides one. (S–M)**
Phone tabs are Home, Learn, Practice, Review, Profile; Vocabulary is desktop-only (`f/components/layout/navTabs.ts:16-24`). "Practice" and "Review" are both "do exercises that are not the next lesson"; a learner cannot tell which to open. Between 720 and 1023px a top bar with text links replaces the tab bar (`f/index.css:279`, `:329-341`), a third navigation layout to maintain.

**R14. Dark mode is system-only and browser chrome stays purple. (S, QW) — D-9**
No theme switch (no `data-theme` or `matchMedia` use in `f/`); a single `theme-color` (`frontend/index.html:7`); manifest `background_color` is dark while light mode is the default surface (`frontend/public/manifest.webmanifest`), so light-mode users get a dark splash.

**R15. RTL is sound in structure, with loose ends. (S, QW) — D-12**
- Physical properties in inline styles: `f/pages/HomePage.tsx:238`, `f/components/PushPrompt.tsx:56`, `f/pages/VocabularyPage.tsx:17`, `:50`, `:73`, `f/components/SpeechSpeedSettings.tsx:54`.
- Directional chevrons are not mirrored: `ChevronLeft`/`ChevronRight` in `f/pages/LessonRunnerPage.tsx:663`, `:674`, `:730`, `:794`; `f/index.css` has no mirroring rule.
- Untranslated accessible name: `aria-label={quest.title}` (`f/pages/HomePage.tsx:313`) while the visible title is translated one line above (`:302`).
- `RTL_LANGUAGES` is `fa, prs, ar` (`sh/i18n/index.ts:51`); fine today, but `sh/lib/scripts.ts` also knows `he, ur`. One source of truth is safer.
- The manifest is `lang: en, dir: ltr` only; installed-app name and shortcuts are not localised.
- Known content gap, already logged: fa/prs terminal punctuation cannot be typed on the in-app keyboard (`docs/PROJECT_STATE.md`, open gaps).

### P2 — quality, consistency, and things that will bite later

**R16. Remaining accessibility gaps. (S–M)**
- Lesson progress bar has no `role="progressbar"` or text alternative (`f/pages/LessonRunnerPage.tsx:733-734`, `:797-798`), unlike Home (`f/pages/HomePage.tsx:212`).
- Targets between 24 and 43px remain (`.local/logs/a11y-2026-11-07.md`, "Not done"); 18px icon buttons in the runner header depend on padding (`f/pages/LessonRunnerPage.tsx:553`).
- Top-bar stats use `role="img"` on text that changes (`f/components/layout/NavBar.tsx:57-74`); changes are not announced.
- `min-height: 100vh` (`f/index.css:171`) rather than `100dvh`: on mobile browsers the page is taller than the visible area.
- No text-size setting; rem units are used throughout (good), but layouts have not been checked at 200% text.

**R17. No optimistic updates. (M) — D-7**
Only one `useMutation` exists (`f/components/DailyGoalPicker.tsx:15`) and there is no `onMutate`/`setQueryData` anywhere. Settings and goal changes wait for the server.

**R18. Answer requests do not send the idempotency key the server supports. (S, QW)**
`answerBody()` (`sh/api/endpoints.ts:203-209`) omits `client_operation_id`, though `/exercises/{id}/answer` accepts and de-duplicates on it (`backend/app/api/router.py:660-676`). A timeout followed by Retry (`f/pages/LessonRunnerPage.tsx:311-313`) can record two attempts and award XP twice. It is also the prerequisite for an offline outbox.

**R19. Five runners, one behaviour, copied. (L, do during the R1 work)**
Lesson, lesson warm-up, review, checkpoint, placement and practice each keep their own `result / lastResponse / lastSpoken / submitting / submitError` state and their own result-banner markup: `f/pages/LessonRunnerPage.tsx:124-155`, `:383-435`, `:571-627`; `f/pages/ReviewPage.tsx:66-86`; `f/pages/PracticeFeedPage.tsx:105-111`; `f/pages/CheckpointPage.tsx`; `f/pages/PlacementTestPage.tsx`. A polish change to feedback must be made five times. `LessonRunnerPage.tsx` is 906 lines.

**R20. Session and cache hygiene. (S–M)**
- Access and refresh tokens are in `localStorage` (`f/main.tsx:45-61`). CSP is enforced (`docs/CSP.md`), which limits the exposure; in native shells use the platform keystore (the Expo scaffold already does: `mobile/lib/tokenStorage.ts`).
- Query keys are not user-scoped and rely on a manual clear at logout (`f/queryClient.ts:13-14`). A local database must be keyed by user from day one.

**R21. Three client shells exist; none is the plan. (decision, not code)**
- `frontend/` — the real app.
- `android-shell/` — Capacitor wrapper with `allowMixedContent: true` (`android-shell/capacitor.config.json:9`), which Play review and good practice both reject for production.
- `mobile/` — Expo/React Native scaffold whose home screen is a placeholder (`mobile/app/index.tsx:12-37`), with three CI workflows (`.github/workflows/mobile-*.yml`).
A solo developer cannot carry a React Native rewrite of fourteen exercise types, a virtual keyboard and RTL in parallel with the web app. `02-platforms.md` recommends one web codebase in native shells and freezing `mobile/`.

**R22. Backend shape. (L, not urgent)**
`backend/app/api/router.py` is 3,702 lines; `practice/service.py` 2,441; `review/grading.py` 1,528. Grading is pure and dependency-free (per `offline-windows-feasibility.md`), which is exactly what makes a shared TypeScript core possible. There is no sync endpoint yet; the service worker comment anticipates `POST /sync/batch` (`frontend/public/sw.js:3-4`).

**R23. Content delivery is per-request and per-lesson. (M–L)**
Lessons are fetched one at a time with answers stripped. Compiled course JSON for the launch set is small (39.7 MB raw, 3.0 MB gzip per `offline-windows-feasibility.md` §2), so versioned downloadable course packs are practical. Audio is the heavy part (est. 100–450 MB for nl/fa/prs) and is not rendered yet (`docs/PROJECT_STATE.md`, open gaps) — without audio, listening exercises fall back to browser TTS, which has no Persian or Dari voice on Windows.

**R24. No performance budget is measured. (M) — D-13**
No Lighthouse/INP/CLS check in `.github/workflows/ci.yml` or `scripts/verify.sh`. The Whisper model is about 150 MB on first voice use (`frontend/CLAUDE.md`, STT section) with no size warning or Wi-Fi check in the UI.

**R25. Gamification tone. (product decision)**
Hearts, gems and leaderboard shipped flag-gated and default-off after being listed as rejected scope (`docs/PROJECT_STATE.md:242+`; `origin/docs/delight-spec` §9 note). The spec keeps them off: hearts punish mistakes, which works against a product whose differentiator is careful feedback. Streak, daily goal and quests are enough.

## 4. Quick wins (about one to two weeks in total, no architecture change)

| # | Change | Finding | Effort |
|---|---|---|---|
| 1 | Detect UI language from `navigator.languages` on first run (fa-AF → prs, fa → fa, nl → nl …) | R5 | S |
| 2 | Add `autoCapitalize/autoCorrect/autoComplete/spellCheck/enterKeyHint` to every answer input | R7 | S |
| 3 | Do not block lesson first paint on the review warm-up | R6 | S |
| 4 | Send `client_operation_id` (a UUID per attempt, reused on Retry) with every answer | R18 | S |
| 5 | Persist and restore in-progress lesson state; rename "Restart lesson" to "Resume" | R2 | M |
| 6 | Replace emoji in nav, hearts, speaker, mic with `lucide` icons; SVG flags or language codes for the course picker | R9 | S–M |
| 7 | Motion tokens; banner slide-in, option pulse, wrong-answer shake; progress via `scaleX` | R3 | M |
| 8 | Dock the feedback banner to the bottom of the viewport as a sheet with Continue inside it | R3 | S |
| 9 | Style `.page-loading`; skeletons for Home, course path, lesson | R8 | M |
| 10 | Move "Continue lesson" to the top of Home as the hero; stats below | R4 | S |
| 11 | Logical properties for the six inline physical styles; mirror chevrons under `[dir=rtl]`; translate the quest `aria-label` | R15 | S |
| 12 | `role="progressbar"` + label on the lesson bar; `100dvh` | R16 | S |
| 13 | Light/Dark/System setting; two `theme-color` metas with `media` | R14 | S |
| 14 | Arrow keys in option groups; `1–9`, `Enter`, `Space`, `Esc` in the runner | R10 | M |
| 15 | Onboarding: language → first lesson; goal and placement offered after | R5 | M |

## 5. Deeper rework (ordered; detailed in `01-core-spec.md` §11)

1. **One session engine.** Extract a pure `SessionEngine` (queue, retry rule, history, outcome) from the five runners into `packages/shared`; one `<SessionRunner>` UI. Removes R19 and makes R2/R3 one-place changes.
2. **Design system.** Tokens (colour, type, space, radius, motion, elevation), a dozen primitives, and migration of inline styles file by file. Removes R11, R9, R8.
3. **Local store + outbox.** IndexedDB (later SQLite in shells) holding progress, attempts and settings; writes go to an outbox and sync when online. Removes the "session unavailable" wall for returning users.
4. **Local grading.** Port `review/grading.py` to TypeScript in `packages/shared/core`, with the Python tests as golden vectors (as already proposed in `offline-windows-feasibility.md` §3A). Answers become instant. Server re-grades on sync and stays authoritative.
5. **Course packs.** Versioned, downloadable content and audio packs per course and level; service-worker/Cache Storage on web, files in shells.
6. **Home, onboarding, settings, navigation redesign** on top of the design system.
7. **Shells.** Store PWA (Windows), Capacitor (Android, then iOS), widgets and notifications per platform.

## 6. Things I could not verify by reading

- Real frame rate, INP and layout shift (needs a device).
- Screen-reader announcements in practice (the a11y log reports axe-clean; axe does not test announcements).
- Whether fa/prs users see correct mirroring of every screen (needs a visual pass).
- Audio quality and coverage (audio is not rendered yet).
- The hearts/gems/leaderboard screens with flags on.
