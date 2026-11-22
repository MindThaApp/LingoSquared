# Lingo² — app spec & build methodology (for external reviewer review)

Written 2026-07-05 by the executing drafting tool A session, for external reviewer to review
against the architecture external reviewer itself designed. This is a snapshot
document — what the app IS, and HOW it's being built — not the
chronological build log. For full session-by-session detail, see
the project notes at the repo root. For the exact API/schema contract, see
`docs/CONTRACT.md`. For the canonical phased roadmap and locked scope
decisions, see the `project-lingosquared-roadmap` memory file.

## 1. What this app is

Lingo² is a Duolingo/Babbel-caliber language-learning app covering
**18 directed learning paths**: English to/from each of nl, fr, de, it,
es, ru, zh, fa, prs (hub-based — no non-English↔non-English pairs).
The owner (the product owner) is personally the primary user for the
en↔fa/prs paths; the app is intended for real public use beyond that.

**"Complete" is defined as**: genuine fluency per language, full CEFR
A1→C2 — not just A1/A2 as this section originally said. Content
build-out order is still basics (A1 across all 18 paths, then a
usage-prioritized A2 wave) → intermediate (B1/B2) → advanced (C1/C2),
repeated per language, expect many incremental releases within each
tier rather than one big drop per tier.

**Publish is a separate, much earlier gate (decision, 2026-07-05):**
The owner does not want to wait for the above breadth before shipping.
Publish as soon as the core runtime (the upgrade program in
`docs/BUILD_PLAN_UPGRADES.md`) is solid and the first
lesson(s)/unit(s) actually shipped are genuinely good — not gated on
a full A1 pass across all 18 paths. The in-app content-issue report
button + admin triage queue (§3) is the load-bearing feedback loop
that makes this viable: real user reports after launch feed back into
what drafting tool B/drafting tool A prioritize next, so quality compounds via live usage
rather than requiring near-perfect content pre-launch.

**Publish-gate language set, decided 2026-07-05: en↔nl and en↔fa/prs
only** (6 directed paths). These are exactly the languages the owner can
personally verify — nl natively (the designated native-review
language), fa/prs as his personally relevant pair, shipped as a bundle
since they share ~100% of the RTL/script tooling from Phase 1/2. The
other 15 directed paths (Latin cohort, ru, zh) keep building toward A1
per the existing phase order but are NOT required to be launch-quality
before shipping — they continue as post-launch drip content.

**Publish-gate quality bar, decided 2026-07-05: "very usable, minimum
bugs," not a phase checklist.** Real beta users on en-nl/en-fa/prs need
to hit essentially no functional breakage, so their feedback is about
content/pedagogy/UX quality, not bug reports. **The executing drafting tool A
session does this verification BEFORE any user sees it** — the
existing non-negotiable verification bar (compiler + backend pytest +
full frontend build + live browser verification with a fresh account,
run against the actual lesson/review/practice flows these three
languages will be used through) is what earns "minimum bugs." The
report-button → triage-queue loop is the NEXT layer, for once the app
is already solid — not a substitute for pre-launch verification.

**Publish-gate content depth, decided 2026-07-05: ≥10 hours new
teaching content + ≥10 hours practice + working scored module
checkpoints, per launch language pair.** Enough to get someone by
day-to-day in-country, not a demo. The ≥10 practice hours are meant to
come from the Endless Practice engine — now extended to all 6 launch
paths (see §6 for current template counts), not hand-authored drills — and
"module tests with scores" means Phase F (unit checkpoint tests, see
`docs/BUILD_PLAN_UPGRADES.md`) is now a hard publish-gate
requirement, not deferred post-launch polish. See the
`project-lingosquared-roadmap` memory file's "Ship-early,
drip-content strategy" section for the full note.

**Platform**: PWA first (installable on iPhone/iPad/Android/desktop,
offline-capable, web push) — one codebase, no app-store dependency to
ship. Native Expo/React Native apps are a deliberately deferred later
phase, reusing the same JSON API. Per-language-audience app variants
(e.g. a Dari-focused build) are supported as build-config flavors of
the same codebase, not separate forks.

**In scope: hearts, gems and the weekly leaderboard.** They were once
listed here as rejected scope, but they shipped flag-gated (default-off
in code) in PR #329 and have been enabled on the live server since
2026-11-17 (`docs/CONTRACT.md` →
"Gamification"). The leaderboard has a per-user opt-out. The §9.2 polish
rules apply to all three. Also accepted: daily quests, one earned streak
freeze, light recurring dialogue characters, and an endless AI-assisted
practice feed (§6).

**Still rejected scope** (don't re-propose without a strong new
reason): an elaborate mascot cast.

## 2. Content architecture (the actual hard part of this product)

Four layers, in order of authoring:

1. **Universal competency spine** (`docs/content/universal_spine.yaml`)
   — language-agnostic communicative *outcomes* with stable IDs (e.g.
   `universal.a1.greetings.open_close_exchange`). The spine defines
   outcomes only, not ordering — each language's realization may
   prepend its own script/phonology "module 0" (Persian/Dari alphabet,
   Chinese pinyin+tones) and reorder/split/reweight spine nodes freely.
   **28 outcomes currently defined: 24 A1 + 4 A2** (A1: greetings,
   introductions, numbers, dates, time, family, food, shopping, places,
   directions, routines, plans, past events, preferences, comparisons,
   travel, health, work, housing, weather, clothing, emotions,
   communication, money/payments — the last 5 added 2026-07-05, verified
   compiling clean; A2: bureaucracy, opinions, banking, and a second
   health outcome, added since — verified against
   `docs/content/universal_spine.yaml` at 2026-07-06 19:53 BST).
   **This count is moving fast this session** — content authoring is
   actively adding outcomes in parallel; re-grep the spine file rather
   than trust this number if it matters. Extensible, not a hard-capped
   list.
2. **Target-language realization** (`docs/content/realizations/<lang>/`)
   — one set per target language, reused across every X→that-language
   path (English's realization is reused across all 9 X→en paths).
   Authored **target-language-first**: the realization owns scenario,
   character names, food, register, and culture — structurally
   identical dialogues across two languages for the same spine node is
   a validation *failure*, not efficiency, because it produces
   translated-feeling content instead of a lesson that actually belongs
   to that language's world.
3. **Source-language overlay** (`docs/content/overlays/<src>-<tgt>/`) —
   one per direction (18 total once complete): explanations, glosses,
   contrastive grammar, interference-error distractors tailored to that
   specific source-language speaker (a Russian learning English needs
   article-error distractors; a Chinese speaker needs tense-mapping
   ones — this is exercise data, not just prose).
4. **Versioned course-release assembly** — `scripts/compile_content.py`
   turns spine + realization(s) + overlay(s) into the JSON the API
   imports, with global content-key uniqueness, cross-file consistency
   checks, and machine-checkable validators (script-purity codepoint
   checks for e.g. Arabic ي/ك vs Persian ی/ک, YAML boolean-coercion
   traps, answer-key sanity). Content keys are stable and independent
   of DB UUIDs.

**Current real coverage** (not aspirational — checked directly against
`docs/content/realizations/`/`overlays/` at 2026-07-06 19:53 BST; this
was actively changing minute-to-minute while this document was being
audited, so treat exact unit counts as a snapshot, not a fixed fact):
8 of 18 paths exist as content, totaling ~131 units — en→es (3 units,
A1 only), en→fr (3 units, A1 only), en→fa (11 units: 9 A1 + 2 A2),
en→prs (11 units: 9 A1 + 2 A2), en→nl (25 units: 23 A1 + 2 A2), fa→en
(26 units: 24 A1 + 2 A2), nl→en (26 units, same), prs→en (26 units,
same, same underlying English realization as fa→en, an
independently-authored Dari overlay). The English realization (shared
by all three X→en directions) currently covers 26 of the spine's 28
outcomes — it hasn't caught up to the newest `banking`/second-`health`
A2 outcomes yet. See §5 for why depth-first on fa/prs came before
breadth.

## 3. Review methodology (the actual quality-control mechanism)

There is **no native-speaker reviewer network** — this was an accepted
risk tradeoff from the start, replaced by an AI cross-review process:

- **Fresh-context review, mandatory**: every piece of learner-facing
  content is reviewed by a *separate* AI session with zero access to
  the authoring reasoning — a reviewer that saw the generation context
  tends to rubber-stamp it. This has caught real, specific defects
  every single time it's been run this project (not theoretical):
  wrong grammar, a lesson that drifted off its declared learning
  outcome into an unrelated scenario, ambiguous pronoun exercises with
  no grammatical basis, an instruction/answer-key mismatch that would
  mark a correct answer wrong, internal authoring jargon leaking into
  learner-facing text, Dari content that was grammatically distinct
  but structurally templated from the Farsi version (same scenario,
  swapped names) rather than genuinely independently authored.
- **Deterministic validators for everything checkable by code**:
  content-key uniqueness, script-purity, YAML footguns, answer-key
  presence — models only judge what code provably can't.
- **In-app error reporting**: every exercise has a report-an-issue
  button feeding an admin triage queue — the intentional other half of
  the "AI review only" tradeoff, since "fix errors as noticed" requires
  a notice mechanism.

**Division of labor** (revised 2026-07-05, same day this doc was
written — drafting tool B's original exclusive content mandate has since been
widened, not reversed): drafting tool B authors all backend code, schema
migrations, and generation-service logic, unchanged. Language content
is now authored by **both** drafting tool B (from-scratch generation, still all
languages) **and** drafting tool A (adapting public-domain FSI/Peace Corps
source material into spine-compliant drafts — see
`docs/content/AUTHORING_GUIDE.md` §10) — the owner has drafting tool A Max headroom
to spare and wants it used for this. Both routes go through the
identical fresh-context review + compiler validation pipeline. The
executing drafting tool A/drafting tool A session also still owns frontend code,
orchestration of drafting tool B's output (extract → validate → apply), and
end-to-end verification.

**Verification bar, non-negotiable**: compiler validation green;
backend test suite green (96 tests currently, real Postgres via
docker compose, not sqlite/mocked); frontend `npm run build` — the
*full* build, not just `tsc --noEmit` (this has caught real type
errors twice that `--noEmit` alone missed); and live browser
verification with a fresh test account for anything user-facing —
reading a diff is not considered sufficient. This project has a
documented habit of finding real bugs specifically at the live-browser
step that code review missed (a deleted logout button, exercise
components silently never wired to the current design system, a
generation-service distractor bug only visible with a real narrow
just-unlocked vocabulary).

## 4. Technical shape

- **Backend**: Python/FastAPI, SQLAlchemy, Postgres. 12 migrations so
  far, additive-only policy (never delete/reassign exercise UUIDs;
  users are pinned to content releases; seeds are idempotent
  create-missing-only — a destructive delete-and-recreate-on-import bug
  was found and fixed early, since the naive version would have wiped
  user progress on every deploy).
- **Frontend**: React, TypeScript, i18next. Full RTL support for
  fa/prs. Every exercise type renders through one `ExerciseRenderer`
  dispatch, which is why new exercise-shaped features (like the
  practice feed, §6) can reuse it unchanged.
- **TTS**: Google Cloud TTS for live audio synthesis, with a browser
  speechSynthesis fallback. **Real, confirmed gap**: Google Cloud TTS
  has zero Farsi/Dari voices, and most browsers/OSes have none either
  (verified directly this session: one real browser had 199 voices
  across ~50 languages, zero Farsi). This is currently the single
  biggest audio-quality gap for the two highest-priority languages.
  Self-hosted TTS (Piper/XTTS) is the identified fix, not yet built.
  Where a device *does* have a working voice, live synthesis works and
  is presented honestly (a real "no voice available" message replaces
  what used to be a silent dead button).
- **Custom on-screen keyboard** for non-Latin scripts (currently
  Perso-Arabic), since relying on the OS's own keyboard switcher proved
  unreliable in practice; shows on focus, has a "use my own keyboard
  instead" dismiss for when the learner wants their device's native
  input (e.g. for Latin/numeric answers).

## 5. Why fa/prs first, not breadth

This was the owner's own most personally relevant and self-reviewable
pair, and the phased plan deliberately goes deep on it before fanning
out: Phase 1 (en↔fa) and Phase 2 (en↔prs) exist specifically to prove
the whole pipeline — content architecture, review process, compiler,
generation service — against the two hardest languages in the set
(RTL, non-Latin script, and for Dari specifically zero TTS coverage
anywhere) before replicating the pattern across the easier Latin-script
cohort (es/fr/it/de/nl), then Russian, then Chinese last (heaviest
tooling lift: pinyin/tone-aware audio, IME-aware grading, no
whitespace segmentation).

## 6. New this session: "Endless Practice" — a generative feed, not a generative curriculum

The owner asked about accelerating content production via AI generation and
free/open-source material, and separately proposed a live-generative
lesson feed. The load-bearing decision made in response, which external reviewer
should specifically sanity-check:

**Rejected**: generating core lesson content live via an LLM call per
scroll/click. Reason: it would ship completely unreviewed content
straight to beginners who by definition can't self-correct an AI
error — the entire review methodology in §3 exists because of exactly
this risk. It also breaks spaced-repetition (nothing stable to
re-test), breaks trustworthy grading (a live-generated exercise needs a
live-generated answer key, unreviewed), and re-introduces a live
LLM-token cost the owner explicitly does not want (confirmed: he cannot
have per-use AI token spend in the running app).

**Built instead**: a bounded, **procedural** generation engine.
drafting tool B authors reviewed *sentence-frame templates* (slotted, tagged,
fresh-context reviewed exactly like lesson content) plus a lexeme pool
promoted from each lesson's already-taught vocabulary. At runtime, a
deterministic seeded sampler recombines them — zero LLM calls, zero
per-use token cost, server-authoritative answer keys, so XP can't be
gamed. Eligibility is gated to vocabulary the learner has actually
completed lessons for. **Since extended past the original fa→en pilot
to all 6 launch-gate directions** (checked directly against
`docs/content/practice/`/`scripts/practice_manifest.txt` as of
2026-07-06): en-fa (124 templates), en-nl (240), en-prs (36), fa-en
(86, up from the original pilot's 72), nl-en (327), prs-en (86).
Mechanism unchanged: infinite-scroll feed, reuses the existing
`ExerciseRenderer` unchanged, smaller diminishing-returns XP so it
supplements rather than replaces real lessons. Listening-card
generation is gated on `tts_actually_configured()` (`app/services/
tts.py`, fixed 2026-07-07 to check real per-provider credentials, not
just static language membership) rather than a fa/prs-specific
exclusion — prs still has zero coverage from either TTS provider and
is permanently excluded either way; fa is technically eligible via
Azure but stays excluded in practice until a real `AZURE_SPEECH_KEY`
is provisioned (not yet done as of this writing — see the project notes'
Secrets section). The gap is respected rather than papered over
either way.

**Free/open material research** (informational, not yet incorporated
into the pipeline): public-domain FSI language courses and the
CC-BY-licensed Tatoeba sentence corpus exist and are usable, but their
value is as *pedagogical reference* fed into drafting tool B's authoring
prompts (proven lesson sequencing, natural example sentences) — not as
directly-imported content, and explicitly not anything from
Duolingo/Babbel, which is proprietary. Not yet built into the actual
authoring workflow; flagged here as a real, low-risk lever if content
velocity becomes the bottleneck again.

## 7. Known real gaps, as of this writing

- TTS has zero Farsi/Dari voice coverage anywhere in the current stack
  (§4) — the single highest-impact unfixed gap for the top-priority
  languages.
- Practice-feature migrations and content exist only in local dev, not
  deployed to the live server yet.
- 8 of 18 paths have real content now (see §2), 3 of them (fa→en,
  nl→en, prs→en) covering 26 of the spine's current 28 outcomes — but
  10 paths still have zero content and none has gone past A2. Still a
  genuinely multi-month build at current velocity to reach full A1→C2
  breadth across all 18 paths; no finish date should be inferred from
  anything in this document.
- No admin UI for content authoring (curl/API-only) — an intentional
  scope trim, not an oversight, given drafting tool B authors via files.
- No native-speaker review network — an accepted, explicit risk
  tradeoff, not a gap anyone is trying to hide.

## 8. Specific questions for external reviewer

1. Does the procedural-not-generative decision in §6 hold up, or is
   there a bounded generative-content design that preserves the review
   guarantee we're missing?
2. Is depth-first on fa/prs (§5) still the right call given TTS remains
   unsolved for exactly those two languages, or should a Latin-script
   path be pulled forward to get a fully-working (audio included)
   reference path sooner?
3. Any red flags in the free/open-source-material-as-reference idea in
   §6 — licensing, quality, or otherwise — before it's built into the
   actual authoring pipeline?

## 9. Delight / polish (Apple-quality feel)

Added 2026-11-17 (the owner: "make the app delightful to use, like macOS /
iOS apps"). This is a product requirement, not a nice-to-have: the app
should feel calm, fast and physical, the way a good native iOS/macOS app
does. Every rule below is written so a reviewer can check it in a
browser. "Delight" never overrides correctness, accessibility (WCAG AA,
the 2026-07/09 a11y passes) or the RTL rules in `frontend/the project notes.

Scope: the web/PWA frontend (`frontend/src/**`). All tokens live in
`frontend/src/index.css` `:root`; no animation library is required (CSS
`linear()` springs or hand-tuned `cubic-bezier` are enough).

Note on §1: hearts, gems and the weekly leaderboard are in scope. They
shipped flag-gated in PR #329 and are enabled on the server since
2026-11-17 (`docs/CONTRACT.md` → "Gamification"). The rules
in §9.2 apply to them wherever the flags are on.

### 9.1 Motion

- **Tokens, not literals.** Durations and easings come from CSS custom
  properties; no raw `0.12s ease` in component rules.

  | Token | Value | Use |
  |---|---|---|
  | `--dur-instant` | 80ms | press/active state |
  | `--dur-fast` | 150ms | hover, focus, colour, selection |
  | `--dur-base` | 250ms | banners, cards, sheets entering |
  | `--dur-slow` | 400ms | progress bar, page-level moves |
  | `--dur-celebrate` | 600–2400ms | lesson-complete only |
  | `--ease-standard` | `cubic-bezier(0.2, 0, 0, 1)` | most transitions |
  | `--ease-exit` | `cubic-bezier(0.4, 0, 1, 1)` | things leaving |
  | `--ease-spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` (or a `linear()` spring, ~0.55 damping, one overshoot ≤ 8%) | pops, tiles, sheets, banners |

- **Springs for things the user moved or earned** (tile placed in a
  word bank, option selected, feedback banner rising, XP/gem counters,
  path node completing). Plain `--ease-standard` for colour and opacity.
- **Animate only `transform` and `opacity`.** The one existing exception,
  the progress bar's `width`, moves to `transform: scaleX()`.
- **Exits are faster than entrances** (exit ≈ 60% of the enter duration).
- **Nothing blocks input.** No animation longer than 250ms may delay the
  next tap; Continue is usable the moment feedback appears.
- **Reduced motion.** With `prefers-reduced-motion: reduce`: no
  translate/scale/rotate, no confetti, no count-up (final value shown at
  once). Opacity cross-fades ≤ 150ms may stay so state changes are still
  visible. The existing global `* { animation: none; transition: none }`
  rule is an acceptable floor; nothing may rely on an animation finishing
  to become visible or usable.

Acceptance:
- [ ] `grep -nE 'transition|animation' frontend/src/index.css` shows only token-based durations/easings.
- [ ] Selecting an option, placing a tile and the feedback banner each visibly ease (no instant jump), and none uses layout properties (DevTools Performance: no Layout in the animation frames).
- [ ] With reduced motion emulated, a full lesson plus the complete screen shows zero movement and every element is visible and usable.
- [ ] Continue responds to a tap made while the feedback banner is still animating in.

### 9.2 Feedback and micro-interactions

- **Answer check.** Pressing Check gives a press state within 100ms. If
  grading takes longer than 300ms the button shows a quiet in-button
  spinner; it never looks dead.
- **Correct.** Chosen option/tiles pulse once (scale 1 → 1.04 → 1,
  `--ease-spring`, 250ms) in `--correct`; the banner slides up 12px and
  fades in (`--dur-base`); the progress bar advances with `--dur-slow`.
- **Wrong.** The answer area does one short horizontal shake (±6px, 2
  cycles, 300ms; opacity-only under reduced motion). Colour is never the
  only signal: icon + text stay as today. The correct answer is readable
  without scrolling on a 375×667 screen.
- **Almost.** Amber banner, no shake, no negative sound.
- **Streak.** When today's first lesson extends the streak, the flame
  and number pop once on the complete screen and the home streak card.
  A streak at risk is stated calmly, never with alarm styling.
- **Hearts (when enabled).** Losing a heart animates the header badge
  (pop + count change) at the moment of the wrong answer, with a polite
  live-region announcement. Reaching 0 leads to the existing
  `OutOfHearts` screen, never a dead end.
- **Gems (when enabled).** A gem award counts up on the complete screen
  and the nav balance updates without a reload. Spending shows the new
  balance immediately.
- **Sound and haptics are optional and never required.** One setting
  ("Sound and vibration on answers", exists today) covers both; default
  on; stored per device. Sounds are short (≤ 250ms), quiet (peak gain ≤
  0.15) and never play over TTS audio. Haptics use `navigator.vibrate`
  where available (Android; iOS Safari has no vibrate API, so iOS stays
  silent-safe): correct 30ms, wrong `[60, 40, 60]`, lesson complete
  `[30, 40, 30, 40, 80]`. All calls are feature-detected and wrapped so
  they can never throw.

Acceptance:
- [ ] Correct, almost and wrong are each distinguishable with sound off, with colour removed (greyscale) and with reduced motion on.
- [ ] Wrong answer: shake plays once, correct answer visible without scrolling at 375×667, focus lands on Continue.
- [ ] With hearts on, a wrong answer changes the badge within 300ms and a screen reader announces the new count.
- [ ] Turning the setting off silences sound and vibration everywhere (lesson, review, practice, checkpoint, placement).
- [ ] On an Android phone the three vibration patterns fire; on iOS and desktop nothing errors in the console.

### 9.3 Typography and spacing rhythm

- **System fonts.** Latin UI uses the platform face: `system-ui,
  -apple-system, "Segoe UI", Roboto, sans-serif` (San Francisco on
  Apple devices). `"Vazirmatn"` stays first in the root stack (it is
  unicode-ranged to Arabic script, so Latin never renders in it). Per
  script stacks for hi/ko/zh/ja stay as they are.
- **Type scale** (rem, 16px root): 0.8125 caption · 0.9375 secondary ·
  1 body · 1.125 emphasised · 1.375 title · 1.75 large title · 2.25
  display. No text below 13px. Body line-height 1.5–1.6; headings
  1.2–1.3. Numbers that change (XP, timers, counts) use
  `font-variant-numeric: tabular-nums`.
- **Spacing scale.** 4px base: 4, 8, 12, 16, 24, 32, 48. Tokens
  `--space-1` … `--space-7`. New code uses tokens; inline `style={{
  margin: … }}` literals are migrated when a file is touched.
- **Rhythm.** Page gutter 16px on phones, 24px from 600px. Cards use
  `--radius` (14px) and 16px inner padding; one primary button per
  screen, full width on phones.
- **RTL (fa/prs UI and content).** `dir`/`lang` are set on `<html>` from
  the UI language and explicitly on every target-language container (the
  existing rule). Layout uses logical properties (`margin-inline`,
  `padding-inline`, `inset-inline`, `text-align: start`). Directional
  icons (back, next, progress direction) mirror in RTL; brand marks,
  media controls and digits do not. Arabic-script text is never
  letter-spaced, never italic, and gets line-height ≥ 1.7. Mixed
  Latin/Persian runs are bidi-isolated.

Acceptance:
- [ ] On macOS/iOS the Latin UI renders in San Francisco; on Windows Segoe UI; on Android Roboto. No web font is downloaded for Latin.
- [ ] No computed font-size below 13px on any page (DevTools audit or a unit test over the stylesheet).
- [ ] With UI language fa and prs: no physical `left`/`right` layout bugs on Home, lesson runner, complete screen and Profile; back/next icons point the right way; the progress bar fills right-to-left.
- [ ] Persian text shows true bold (Vazirmatn variable weights), no letter-spacing, no clipped diacritics.

### 9.4 Perceived performance

- **Budgets.** Tap/key → visible press state ≤ 100ms. Check → verdict
  shown ≤ 400ms at p95 on the LAN/live server; beyond 300ms a pending
  state shows. Route change → meaningful content or skeleton ≤ 200ms.
  Animations hold 60fps (frame time ≤ 16.7ms) on a mid-range Android
  phone; no long task > 50ms during a lesson. Lab targets on the lesson
  route: INP ≤ 200ms, CLS ≤ 0.05, LCP ≤ 2.5s on Fast 4G.
- **Optimistic UI for user-owned, reversible state:** daily goal,
  settings toggles, quest claims, gem spends, marking a word. The UI
  changes at once and rolls back with a short, friendly message if the
  server refuses. Answer grading is **not** optimistic: the verdict
  always comes from the grader.
- **Skeletons, not text spinners,** for anything that loads in more
  than 200ms: Home stat cards, course path, unit lessons, vocabulary
  list, leaderboard, lesson first paint. Skeletons match the final
  box size.
- **No layout shift.** Stat cards, nav balance, hearts badge, feedback
  banner and virtual keyboard reserve their space before data arrives.
  The feedback banner never pushes the answer off screen. Fonts use
  `font-display: swap` with metric-compatible fallbacks.
- **Prefetch the next step.** The next exercise's audio and the next
  lesson's data are warmed while the learner reads feedback.

Acceptance:
- [ ] Lighthouse (mobile, lesson route, logged in): CLS ≤ 0.05, INP/TBT within budget.
- [ ] DevTools Performance recording of 5 answers at 4× CPU throttle: no dropped-frame run longer than 2 frames during animations, no long task > 50ms.
- [ ] On Slow 4G, Home, course path, lesson and vocabulary show a skeleton (not blank, not "Loading…" text) and nothing jumps when data lands.
- [ ] Changing the daily goal and toggling a setting update instantly; with the network blocked they roll back with a message.

### 9.5 Empty, error and loading states

- Every data view has all four states designed: loading (skeleton),
  empty, error, content. No blank areas and no raw error codes.
- **Copy rules.** Say what happened in plain words, then the one thing
  to do next. No blame, no jargon, no "Oops", no exclamation marks in
  errors. Empty states point forward ("No words yet. Finish a lesson
  and they will show up here." + a Start lesson button). All strings
  are in every UI locale (the locale-parity test stays green).
- **Errors are recoverable in place:** a Retry button, the learner's
  typed answer preserved, and offline detected and named ("You're
  offline. Your progress is saved; we'll retry when you're back.").
- **A failed submit never reads as a wrong answer** (the existing
  neutral `.feedback-banner.error` style is the model).
- The crash screen (`ErrorBoundary`) and 404 follow the same rules and
  always offer a way home.

Acceptance:
- [ ] For Home, Courses, Unit, Lesson, Review, Practice, Vocabulary, Leaderboard, Profile: each of loading / empty / error is reachable (throttle, fresh account, blocked request) and has copy plus a next action.
- [ ] Blocking the answer request keeps the typed answer and shows Retry; unblocking and retrying succeeds without a reload.
- [ ] No user-visible string contains a status code, exception name or "undefined".
- [ ] fa and prs show translated state copy, right-aligned.

### 9.6 Dark mode parity

- Dark mode follows the system (`prefers-color-scheme`); a manual
  Light / Dark / System choice in Profile is the target.
- Every colour comes from a token with a dark value; no hard-coded hex
  in components or inline styles. Contrast meets WCAG AA in both themes
  (`frontend/src/a11yTokens.test.ts` covers the token pairs; new tokens
  are added to it).
- Elevation in dark mode comes from lighter surfaces, not heavier
  shadows. Confetti, badges (including the Beta badge), charts and
  illustrations are checked in both themes.
- The browser chrome matches: `theme-color` and the PWA manifest have a
  dark variant; `color-scheme` is set so form controls and scrollbars
  follow.

Acceptance:
- [ ] Side-by-side screenshots of every route in light and dark: no unreadable text, no white flashes on navigation, no light-only borders or shadows.
- [ ] `a11yTokens.test.ts` passes and covers every foreground/background token pair in use.
- [ ] `grep -rnE '#[0-9a-fA-F]{3,6}' frontend/src --include=*.tsx` returns no colour literals outside tests.
- [ ] On a phone in dark mode the status bar / title bar is dark, not `#4a3bff`.

### 9.7 Touch targets

- Every interactive element has a hit area of at least 44×44 CSS px
  (Apple's 44pt), with ≥ 8px between adjacent targets. Small glyphs
  (speaker, report flag, gloss words, close ×) get padding or a
  pseudo-element to reach it.
- Documented exception: virtual-keyboard keys are 42px wide × 48px high
  so 7 keys fit a 375px line (see the comment in `index.css`).
- No hover-only affordances; `:active` gives a visible press state on
  touch. The 300ms tap delay and double-tap zoom are off on controls
  (`touch-action: manipulation`).

Acceptance:
- [ ] An automated check (Playwright, 375×667) finds no visible button/link/input smaller than 44×44 except the listed exception.
- [ ] Words-tab search/sort controls (40px today) and range sliders (24px) meet 44px.
- [ ] Every control shows a press state on a real phone.

### 9.8 Keyboard shortcuts (desktop)

| Key | Action |
|---|---|
| `Enter` | Check answer; when feedback is showing, Continue |
| `1`–`9` | Pick option n (multiple choice, matching, word-bank tile n) |
| `Backspace` | Remove last word-bank tile |
| `Space` | Play / replay audio (when focus is not in a text field) |
| `Ctrl/⌘ + Enter` | Submit a multi-line writing answer (exists) |
| `Esc` | Close a popover or dialog; in a lesson, open the quit confirm |
| `?` | Show the shortcut sheet |

- Shortcuts never fire while a text input, the virtual keyboard or an
  IME composition has focus, and never with modifier keys unless listed.
- Number hints show on options only on devices with a fine pointer and
  a hardware keyboard (`(hover: hover) and (pointer: fine)`).
- Focus is always visible (`:focus-visible` ring) and moves sensibly:
  to the answer field on a new exercise, to Continue after a verdict.
- `aria-keyshortcuts` is set on the controls that have one.

Acceptance:
- [ ] A full lesson with every exercise type can be completed on desktop without the mouse.
- [ ] Typing digits or space in a text answer types them and triggers nothing.
- [ ] `?` opens a sheet listing exactly the table above; `Esc` closes it.
- [ ] Shortcuts work the same with UI language fa (RTL) and are inactive during IME composition (ja/ko/zh).

### 9.9 Lesson-complete celebration

- Plays once, only after a real completion (the existing route-state
  gate), never on refresh or back.
- Sequence, ≤ 2.5s in total and skippable at any moment by pressing
  Continue: confetti burst → XP counts up (700ms) → gems (if any) →
  streak flame pop if the streak grew → daily-goal bar fills. One short
  success sound and the completion haptic at the start, under the
  feedback setting.
- Continue is focused and tappable from the first frame. The screen
  shows what was achieved (XP, accuracy, words to revisit) and one
  clear next step.
- Reduced motion: no confetti, no count-up, same information.
- Bigger moments scale up modestly: a perfect lesson, a daily goal met,
  a unit finished and streak milestones (7, 30, 100, 365) get a distinct
  headline and colour, not a longer animation.

Acceptance:
- [ ] Completing a lesson shows the sequence once; refreshing the page shows the static summary.
- [ ] Pressing Enter at any point during the celebration continues immediately.
- [ ] Reduced motion: static screen, all numbers present.
- [ ] Sound/haptic respect the setting; nothing plays when it is off.
- [ ] A perfect lesson and a met daily goal each show their distinct headline, in light and dark, LTR and RTL.

### 9.10 Onboarding: first exercise fast

- **Target: a new learner answers a first exercise within 60 seconds
  and at most 3 taps after choosing a language**, with no typing beyond
  what sign-up needs.
- Order: pick language → first lesson starts. The daily goal defaults
  to a sensible value and is offered after the first lesson, when it
  means something. The placement test is an offer ("Know some already?
  Find my level"), not a gate.
- No permission prompts (push, microphone) before the first lesson is
  done; each is asked in context, the first time it is useful.
- Progress made before any interruption is kept; leaving and returning
  resumes at the same step (the per-device onboarding state does this).
- First-run screens have one decision each and one primary button.
- fa/prs courses keep the Beta badge and note visible at the choice
  point, without adding a step.

Acceptance:
- [ ] Fresh account, stopwatch: registered → first exercise on screen in ≤ 60s and ≤ 3 taps after language choice, on a phone.
- [ ] No browser permission prompt appears before the first lesson-complete screen.
- [ ] Skipping, reloading mid-onboarding and returning all land somewhere sensible, never on an empty Home.
- [ ] The same flow passes with UI language fa.

### 9.11 Current gaps (2026-11-17, ranked by user impact)

From a read of `frontend/src` at `fix/wsl-handover-followups`
(ac3d97671). Effort: S ≤ ½ day, M 1–2 days, L 3+ days. Nothing here is
implemented by this section.

What already meets the bar: WCAG-AA colour tokens in both themes with a
unit test, a global reduced-motion rule, safe-area insets, 44px
buttons, self-hosted Vazirmatn with correct unicode-range, sound +
vibration cues with a setting (`lib/answerCue.ts`), confetti + XP
count-up on completion, a neutral submit-error banner with Retry,
`:focus-visible` rings, Enter-to-submit on typed exercises.

| # | Gap | Effort | Files |
|---|---|---|---|
| 1 | Answer feedback is static: the banner appears with no motion, no correct pulse, no wrong shake; option state changes snap. The most repeated moment in the app has the least polish. | M | `frontend/src/index.css` (`.feedback-banner`, `.exercise-option`), `components/AnswerFeedbackExtras.tsx`, `components/exercises/ChoiceOptions.tsx`, `WordBankInput.tsx`, `WordOrder.tsx`, `MatchingPairs.tsx`, `pages/LessonRunnerPage.tsx` |
| 2 | Loading is plain "Loading…" text (`.page-loading` has no style rule) or nothing at all: Home, course path and unit pages render without placeholders, so numbers and cards pop in and shift. No skeletons anywhere. | M | `App.tsx` (Suspense fallback), `pages/HomePage.tsx`, `CourseUnitsPage.tsx`, `UnitLessonsPage.tsx`, `VocabularyPage.tsx`, `ReviewPage.tsx`, `LeaderboardPage.tsx`, `LessonRunnerPage.tsx`, `index.css` |
| 3 | Onboarding is 3 stages (course → goal → start/placement) and then drops the learner on the course page; first exercise is several screens away. | M | `pages/OnboardingPage.tsx`, `lib/onboarding.ts`, `lib/nextLesson.ts`, `pages/CoursePickerPage.tsx`, `components/DailyGoalPicker.tsx` |
| 4 | Desktop shortcuts are minimal: Enter (form submit), Ctrl/⌘+Enter in writing, Esc in two components. No number keys for options or tiles, no audio key, no shortcut sheet. | M | new `lib/useLessonShortcuts.ts`, `components/exercises/ChoiceOptions.tsx`, `WordBankInput.tsx`, `MatchingPairs.tsx`, `components/SpeakButton.tsx`, `pages/LessonRunnerPage.tsx`, `ReviewPage.tsx`, `PracticeFeedPage.tsx` |
| 5 | No motion tokens: hand-written durations/easings (`0.05s`–`0.45s`, `ease`, one bounce bezier) and the progress bar animates `width`. No spring system. | S | `frontend/src/index.css` |
| 6 | Hearts and gems have no "moment": `HeartsBadge` is a static emoji + number, losing a heart is silent, gems on the complete screen are a plain line, the nav balance just changes. | S–M | `components/HeartsBadge.tsx`, `OutOfHearts.tsx`, `components/layout/NavBar.tsx`, `pages/LessonCompletePage.tsx`, `lib/gamification.ts`, `index.css` |
| 7 | No optimistic updates: there is no `onMutate`/`setQueryData` in app code; goal changes, gem spends and settings wait on the server (buttons go `busy`). | M | `components/DailyGoalPicker.tsx`, `GamificationSettings.tsx`, `OutOfHearts.tsx`, `pages/ProfilePage.tsx`, `queryClient.ts` |
| 8 | Lesson-complete has confetti and count-up but no sound or haptic, no perfect-lesson / goal-met / milestone variants, and gems do not count up. | S | `pages/LessonCompletePage.tsx`, `lib/answerCue.ts`, `index.css` |
| 9 | Dark mode is system-only (no in-app choice) and `theme-color` is a single `#4a3bff`, so phone chrome stays purple in dark mode. | S | `frontend/index.html`, `public/manifest.webmanifest`, `index.css`, `pages/ProfilePage.tsx` |
| 10 | Spacing and type are ad hoc: no spacing or type-scale tokens and many inline `style={{ margin… }}` literals. | M | `frontend/src/index.css`, most `pages/*.tsx` and `components/*.tsx` (migrate on touch) |
| 11 | Touch targets below 44px remain: Words-tab controls (40px), range inputs (24px); small icon buttons need an audit. No automated size check. | S | `frontend/src/index.css`, `pages/VocabularyPage.tsx`, new check in `e2e/` |
| 12 | RTL polish not audited against logical properties and icon mirroring (direction handling itself is solid). | M | `frontend/src/index.css`, `components/layout/NavIcon.tsx`, `NavBar.tsx`, `pages/LessonRunnerPage.tsx` |
| 13 | No performance budget is measured: no Lighthouse/INP/CLS check in CI or `scripts/verify.sh`. | M | `e2e/`, `.github/workflows/ci.yml`, `scripts/verify.sh` |
