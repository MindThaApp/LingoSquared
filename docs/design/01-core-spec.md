# Auvel (LingoSquared) — core product and design spec

Date: 2026-11-18. Status: proposal, nothing here is implemented.
Scope: the master spec for every platform. Platform differences are in `02-platforms.md`. The evidence behind each decision is in `00-review.md` (cited as R-n).

This spec extends, and does not replace, `docs/APP_SPEC_FOR_REVIEW.md` §9 on branch `origin/docs/delight-spec`. Its motion tokens, feedback rules, shortcut table and acceptance checklists are adopted here by reference (cited as D§9.x). Where the two differ, this file says so.

Fixed constraints taken from the repo rules:
- Every course is English-anchored (en→X, X→en). This spec proposes no new pair types.
- Dutch is the polish reference; fa and prs are the mandatory RTL, virtual-keyboard and strict-script check for every phase.
- `docs/CONTRACT.md` is updated before any API change. Backend and compiler work is drafting tool B's lane; frontend and shared TypeScript is drafting tool A's.
- Hearts and gems stay off; leaderboards may be added later as opt-in only (R25). **Decided (see DECISIONS.md D7)**

---

## 1. Product principles

1. **Answer, then network.** Nothing the learner does in a session waits for a server. Check is instant; sync is background.
2. **One thing to do now.** Every screen has one primary action. Home answers "what do I do today?" in one glance.
3. **Never lose work.** A lesson survives a reload, a crash, a dead battery and a week offline. Progress is written locally first.
4. **Kind and exact.** Feedback says precisely what was different and why, without scolding. "Almost" is a first-class verdict.
5. **Calm by default, joy at the right moments.** Quiet surfaces, generous space, system fonts. Celebration is short, earned and skippable.
6. **Both directions are first-class.** RTL is not a mirror applied at the end; fa/prs screens are designed and tested as primary.
7. **Native where it counts.** Platform conventions for navigation, back, keyboard, notifications and text size; one visual identity everywhere.
8. **Honest.** Beta content is labelled. Absent signal is shown as absent (the existing pronunciation rule). No dark patterns, no guilt notifications.
9. **Accessible is the baseline, not a mode.** WCAG 2.2 AA, full keyboard, screen reader, 200% text and reduced motion are acceptance criteria for every screen.

What we take from the reference apps:

| App | What to take | What to leave |
|---|---|---|
| Things 3 | "Today" as the home; spring-loaded, physical interactions; quiet typography; keyboard-first on desktop | — |
| Duolingo | Tight lesson loop; instant verdict sheet; path as a visual journey | Hearts, guilt notifications, league pressure, mascot noise |
| Apple Fitness | A single ring for the daily goal; weekly history at a glance; awards as objects | — |
| Headspace | Warm, short copy; soft shapes; breathing room; calm completion | Long illustrated onboarding |
| Flighty | Live, glanceable status; offline-first by design; widgets and Live Activities that are truly useful | Density |
| Halide | Haptic detail; a tool that feels made by hand; one-handed reach | Pro-tool complexity |
| Arc | Command bar; shortcuts for everything; playful but restrained motion | Novel navigation that needs learning |

---

## 2. Information architecture

### 2.1 Destinations

Four destinations (five was R13):

| Destination | Purpose | Contains |
|---|---|---|
| **Today** | What to do now, and how today is going | Hero action, goal ring, streak week, due review, quests (if on), resume |
| **Path** | The course as a journey | Units and lessons for the active course, checkpoints, speaking track, situations shelf, course switcher |
| **Practice** | Everything that is not the next lesson | Review (SRS, due count), Fix mistakes, Endless practice modes, Speaking/conversation, Listening |
| **Library** | What I know | Words (search, sort, due), mistakes, grammar notes seen, export |

Plus **You** (profile and settings), reached from the avatar at the top of Today and from the rail on wide layouts. It is not a tab on phones.

"Review" and "Practice" merge: Review is the first, highlighted card inside Practice, with its due count as a badge on the Practice tab. Vocabulary becomes Library and is on phones.

### 2.2 Route map (web paths stay stable; existing paths kept where possible)

```
/                      Today
/path                  Path for the active course        (alias: /courses/:courseId)
/path/units/:unitId    Unit detail                       (alias: /units/:unitId)
/courses               Course picker (also first-run)
/practice              Practice hub
/practice/review       Review session (runner)           (alias: /review)
/practice/feed         Endless practice
/practice/mistakes     Fix mistakes (runner)
/library               Words | Mistakes | Notes          (alias: /vocabulary)
/library/words/:id     Word detail
/session/:kind/:id     The one runner: lesson | review | checkpoint | placement | mistakes
/session/:id/done      Completion
/you                   Profile summary                   (alias: /profile)
/you/settings/:group   Settings groups (§4.9)
/welcome               First run
/login /register /forgot-password /reset-password /privacy /terms
```

Old paths redirect, so installed PWAs, notifications and shortcuts keep working.

### 2.3 Navigation model

- Runner routes are full-screen and modal: no tabs, a close button, a progress bar.
- Everything else is one level of tabs plus push navigation. Back always goes up one level; the system back gesture/button does the same.
- Layout by width class is defined in §6.6; per-platform patterns in `02-platforms.md`.

---

## 3. Design system

All tokens are CSS custom properties on `:root` in a new `frontend/src/styles/tokens.css` (imported first by `index.css`), mirrored as a typed object in `packages/shared/src/design/tokens.ts` for non-CSS consumers (widgets, native splash, charts). Existing token names (`--bg`, `--surface`, `--accent` …) are kept as aliases so migration is file by file.

### 3.1 Colour

Semantic roles, not raw hues. Components use roles only. Existing AA-verified values are kept (`frontend/src/index.css:27-134`); new roles are additions.

| Role | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#f7f7fb` | `#131318` | App background |
| `--surface` | `#ffffff` | `#1c1c24` | Cards, sheets |
| `--surface-2` | `#f0f0f6` | `#24242e` | Insets, tiles, tracks |
| `--surface-3` (new) | `#e8e8f1` | `#2d2d3a` | Pressed tiles, dark-mode raised |
| `--text` | `#2b2b33` | `#d9d9e3` | Body |
| `--text-strong` (alias `--text-h`) | `#101018` | `#f5f5fa` | Headings, numbers |
| `--text-soft` | `#646471` | `#9a9aa8` | Secondary |
| `--border` | `#e3e3ec` | `#2d2d3a` | Hairlines (decorative) |
| `--border-strong` (alias `--input-border`) | `#85859a` | `#6e6e82` | Control edges (3:1) |
| `--accent` | `#4a3bff` | `#8d82ff` | Primary actions, selection, links |
| `--accent-soft` | `#edebff` | `#2a2745` | Selected rows, badges |
| `--on-accent` (alias `--accent-contrast`) | `#ffffff` | `#101018` | Text on accent fills |
| `--correct` / `--correct-soft` | `#127a3a` / `#e3f7ea` | `#4fc878` / `#16311f` | Correct |
| `--almost` / `--almost-soft` | `#8f5b00` / `#fdf1db` | `#e0a94b` / `#3a2f14` | Almost, caution |
| `--incorrect` / `--incorrect-soft` | `#c02b2b` / `#fdeaea` | `#e86a6a` / `#3a1f1f` | Incorrect, destructive |
| `--streak` (alias `--flame`) | `#b34b00` | `#ff7a1a` | Streak |
| `--reward` (alias `--gold`) | `#8f6200` | `#f5a623` | XP, awards |
| `--info` / `--info-soft` (new) | `#1d5fa8` / `#e6f0fb` | `#7fb4ee` / `#172a40` | Neutral notices, offline, sync |
| `--scrim` (new) | `rgba(16,16,24,.45)` | `rgba(0,0,0,.6)` | Behind sheets and dialogs |

Rules:
- Every text/background pair in use is listed in `a11yTokens.test.ts`; new pairs (`--info` on `--info-soft`, on `--surface`) must reach 4.5:1 before merge. The two new hues above are starting values to be verified by that test, not eyeballed.
- Verdict colour is never the only signal: icon + word always accompany it.
- No hex literals in components or inline styles (D§9.6 acceptance).
- Theme: `System` (default), `Light`, `Dark`, set by `data-theme` on `<html>`; `prefers-color-scheme` applies only when `data-theme` is absent. A third appearance, **High contrast**, follows `prefers-contrast: more` / `forced-colors: active`: borders become `--border-strong`, soft fills gain a 1px outline, shadows are removed.
- Dark elevation uses lighter surfaces (`--surface` → `--surface-2` → `--surface-3`), not heavier shadows.
- Browser and window chrome follow the theme: two `theme-color` metas with `media`, updated at runtime when the user overrides.
- Course identity: each target language gets one accent tint used only on its Path header and course card (an 8% wash of a per-language hue over `--surface`). It never replaces `--accent` on controls.

### 3.2 Typography

System fonts for Latin; `Vazirmatn` first in the stack for Arabic script (kept exactly as today); existing per-script stacks for hi/ko/zh/ja kept.

```
--font-ui: "Vazirmatn", system-ui, -apple-system, "Segoe UI Variable", "Segoe UI", Roboto, sans-serif;
--font-num: var(--font-ui);  /* with font-variant-numeric: tabular-nums */
```

Type scale (rem at a 16px root; this replaces the 22 ad hoc sizes, R11):

| Token | Size / line | Weight | Use |
|---|---|---|---|
| `--type-display` | 2.25 / 1.15 | 700 | Completion number, streak milestone |
| `--type-title-1` | 1.75 / 1.2 | 700 | Screen title |
| `--type-title-2` | 1.375 / 1.25 | 700 | Card title, exercise instruction |
| `--type-prompt` | 1.5 / 1.35 | 600 | The sentence or word being taught/tested |
| `--type-body-lg` | 1.125 / 1.5 | 400 | Options, answer text, teaching notes |
| `--type-body` | 1 / 1.55 | 400 | Default |
| `--type-secondary` | 0.9375 / 1.45 | 400 | Supporting text |
| `--type-caption` | 0.8125 / 1.4 | 500 | Labels, badges (13px floor) |

Rules:
- No text under 13px. No all-caps for Arabic-script, CJK or Devanagari; Latin labels may use small caps only as `--type-caption` with +0.02em tracking.
- Arabic-script text: line-height ≥ 1.7, never letter-spaced, never italic; `--type-prompt` renders one step larger (1.75rem) because Persian letterforms read smaller at equal size.
- Target-language text always carries `lang` and `dir` (existing rule) and uses `--type-prompt` or `--type-body-lg`; UI chrome never uses the prompt style.
- Numbers that change use tabular figures. Persian UI shows Persian digits in prose and Latin digits inside `<bdi dir="ltr">` for scores like `12/20` (existing pattern, `HomePage.tsx:304`).
- **Text size** (the Dynamic Type equivalent): the root size follows the user's browser/OS setting (never set `html { font-size }` in px). An in-app setting adds a multiplier: Small 0.9, Default 1, Large 1.15, Larger 1.3, Largest 1.5, applied as `html { font-size: calc(100% * var(--text-scale)) }`. In native shells the multiplier is initialised from the OS font scale. Every layout must work at 200% (WCAG 1.4.4) and reflow at 320 CSS px (1.4.10).

### 3.3 Space, size, radius, elevation

```
--space-1: 4px   --space-2: 8px   --space-3: 12px  --space-4: 16px
--space-5: 24px  --space-6: 32px  --space-7: 48px  --space-8: 64px

--radius-xs: 6px   (chips, keys)        --radius-sm: 10px  (inputs, tiles)
--radius-md: 14px  (cards, options)     --radius-lg: 20px  (sheets, hero)
--radius-full: 999px

--hit-min: 44px          (48px on Android shells, see 02-platforms)
--control-h: 52px        (primary buttons, options)
--gutter: 16px  (<600)   24px (600–1023)   32px (≥1024)
--content-max: 640px     (reading/exercise column)   --page-max: 1120px

--elev-0: none
--elev-1: 0 1px 2px rgba(20,16,60,.06), 0 2px 8px rgba(20,16,60,.04)     cards
--elev-2: 0 4px 16px rgba(20,16,60,.10)                                   sheets, popovers
--elev-3: 0 12px 40px rgba(20,16,60,.18)                                  dialogs
```

- One spacing scale; no values off it. Vertical rhythm inside a card is `--space-3`; between cards `--space-4`; between sections `--space-6`.
- The exercise column is never wider than `--content-max`, on any screen, so line length stays readable.
- Logical properties only (`margin-inline`, `padding-inline`, `inset-inline`, `border-start-*`, `text-align: start`). A lint rule (stylelint `csstools/use-logical` plus an ESLint/oxlint rule for inline `marginLeft` etc.) enforces it.

### 3.4 Motion

Tokens exactly as D§9.1 (`--dur-instant` 80ms, `--dur-fast` 150ms, `--dur-base` 250ms, `--dur-slow` 400ms, `--ease-standard`, `--ease-exit`, `--ease-spring`). Additions:

| Pattern | Spec |
|---|---|
| Press | scale 0.97, `--dur-instant`; release springs back |
| Select option / place tile | spring to place, 250ms; tiles travel from bank to answer line (FLIP, transform only) |
| Verdict sheet | rises from the bottom edge 16px + fade, `--dur-base`, spring; leaves in 150ms |
| Correct | chosen element pulses 1 → 1.04 → 1; progress bar segment fills with `scaleX`, `--dur-slow` |
| Wrong | answer area shakes ±6px, 2 cycles, 300ms (direction-neutral) |
| Screen push | 280ms slide along the inline axis (so it reverses in RTL) with a 30% parallax on the outgoing screen; uses the View Transitions API where present, plain cross-fade elsewhere |
| Runner enter/exit | rises as a full-screen sheet (it is modal); closes downward |
| Exercise → exercise | outgoing fades and moves 24px toward inline-start; incoming from inline-end; 220ms total |
| Skeleton | opacity pulse 0.6 ↔ 1, 1.2s, no shimmer sweep |
| Number change | count-up 600ms ease-out, only on completion and Today's ring |

Rules: animate `transform` and `opacity` only; nothing blocks input; exits take about 60% of the entrance time; under `prefers-reduced-motion` all movement is removed and replaced by ≤150ms opacity changes, confetti and count-ups are off, and nothing depends on an animation finishing. An in-app "Reduce motion" setting forces the same behaviour.

### 3.5 Haptics

One abstraction, `haptics.play(kind)`, in `packages/shared/src/platform/haptics.ts`, with per-platform back ends (Web Vibration API; Capacitor Haptics on Android/iOS; none on desktop).

| Kind | When | iOS (Capacitor) | Android | Web fallback |
|---|---|---|---|---|
| `selection` | Option picked, tile placed, key on virtual keyboard | selection changed | `CLOCK_TICK` | none |
| `impactLight` | Check pressed | impact light | `KEYBOARD_TAP` | 10ms |
| `success` | Correct | notification success | `CONFIRM` | 30ms |
| `warning` | Almost | notification warning | `GESTURE_END` | `[20,40,20]` |
| `error` | Wrong | notification error | `REJECT` | `[60,40,60]` |
| `celebrate` | Lesson complete, milestone | success + two light impacts | `CONFIRM` ×2 | `[30,40,30,40,80]` |

Haptics follow their own setting (default on where supported), are skipped when the OS has system haptics off, and never fire more than once per 80ms.

### 3.6 Sound

Replace the synthesised beeps (`frontend/src/lib/answerCue.ts:5-9`) with a small designed set: soft, pitched, wooden/marimba-like, in one key so sequences sound related. Six files, each ≤ 40 KB, 44.1 kHz mono, bundled (not fetched):

| Cue | Length | Character |
|---|---|---|
| `tap` | 30ms | Dry tick; tile placed (off by default, on with "Interface sounds") |
| `correct` | 220ms | Rising major third |
| `almost` | 220ms | Same first note, unresolved second |
| `incorrect` | 180ms | One low, soft, non-buzzy note |
| `complete` | 900ms | Four-note rise; the only sound longer than 250ms |
| `milestone` | 1.4s | `complete` plus a held chord; streak 7/30/100/365 and unit complete only |

Rules: peak −12 dBFS; never overlaps TTS or recorded audio (cue is skipped, not queued, if audio is playing or about to autoplay); respects the device silent switch in shells; decoded once into a Web Audio buffer at first interaction. Settings: "Answer sounds" (default on), "Interface sounds" (default off), plus the existing TTS voice and speed settings. The streak in practice (combo) raises the `correct` pitch by one scale step per consecutive answer, up to five, then holds — a small reward for flow that costs nothing.

### 3.7 Iconography and illustration

- One icon set: `lucide-react`, 1.75px stroke, sizes 16/20/24. No emoji as UI (R9). Icons that imply direction (back, next, chevrons, progress arrows, "send") mirror in RTL via a single `.icon-dir` class (`[dir=rtl] .icon-dir { transform: scaleX(-1) }`); speaker, play, mic, check, clock and brand marks never mirror.
- Language marks: no flag emoji. Use a rounded tile with the language's own short name in its own script (`NL`, `فا`, `دری`, `DE`) on the course tint. Flags are political for fa/prs and do not render on Windows.
- Empty, error and completion states use a small set of line illustrations in the accent colour (12 in total, SVG, theme-aware via `currentColor`). Until they exist, a 48px lucide icon in a `--accent-soft` circle is the standard.
- Unit icons continue to use `packages/shared/src/lib/unitIcons.ts`.

### 3.8 Components

Each is a React component in `frontend/src/ui/` with a fixed prop surface and all states. "States" always include default, hover (fine pointer only), focus-visible, pressed, disabled, loading where relevant, and RTL.

| Component | Notes |
|---|---|
| `Button` | Variants: primary, secondary, quiet, destructive. Sizes: md (44), lg (52). `loading` shows an in-button spinner after 300ms and keeps width. Full width on compact layouts. |
| `IconButton` | 44×44 hit area whatever the glyph size; requires `aria-label`. |
| `Card` | Surface, `--radius-md`, `--elev-1`, 16px padding. `interactive` variant is a real `<a>`/`<button>` with a press state. |
| `ListRow` | Leading icon, title, subtitle, trailing value/chevron/switch. 56px min height. Used for all settings and lists. |
| `Sheet` | Bottom sheet on compact, centred dialog on wider. Focus trap, Escape, scrim tap, drag-to-dismiss on touch, `inert` on the page behind. Replaces the three hand-rolled overlays. |
| `VerdictSheet` | Non-modal sheet docked to the bottom of the runner: icon + verdict word, the diff/correct answer, optional "Why?", actions. Never covers the prompt; the runner scroll area gets matching bottom padding. |
| `ProgressBar` | `role="progressbar"`, label, `scaleX` fill, optional segments. Fills from inline-start. |
| `GoalRing` | SVG ring, value + label in the centre, text alternative; closes with a spring and a `success` haptic when the goal is met. |
| `OptionGroup` / `Option` | Radio pattern with roving tabindex, arrows, `1–9` hints on fine-pointer devices; grade states with icon. |
| `TileBank` / `Tile` | Index-keyed (existing rule), explicit `dir`, FLIP movement, drag to reorder plus tap; keyboard: arrows to move focus, Enter/Space to place, Backspace to remove last. |
| `TextAnswer` | Input or textarea with `lang`, `dir`, autocorrect off (R7), optional `VirtualKeyboard`, mic toggle, character helpers (é, ë, ij …) as a chip row for Latin targets. |
| `VirtualKeyboard` | Existing layouts; adds terminal punctuation for fa/prs (open gap in `PROJECT_STATE.md`), key preview on touch, `selection` haptic. |
| `AudioButton` | Play/replay, slow (0.75×) on long press or second tap; shows loading and failure honestly; `Space` shortcut. |
| `TargetText` | Existing; the only way to render target-language text (lang, dir, transliteration, gloss). |
| `Badge`, `Chip`, `SegmentedControl`, `Switch`, `Select`, `Slider` | Standard; `Switch` and `Slider` 44px hit height. |
| `Skeleton` | Block, line, circle; sized to the final layout. |
| `Banner` | Inline status: info, offline, sync problem, beta. Never red unless the user must act. |
| `Toast` | Bottom (above tab bar), 4s, one at a time, `role="status"`; used for sync results and undo. |
| `EmptyState` | Illustration/icon, one sentence, one action. |
| `PathNode` | Lesson/checkpoint node: locked, available, current (pulsing ring, reduced-motion: static ring), done, perfect. |
| `StatTile`, `WeekStrip` | Numbers and the 7-day streak strip. |
| `CommandBar` | Desktop/tablet with keyboard: `Ctrl/⌘+K`; jump to course, unit, word, setting. Phase 6. |

### 3.9 Microcopy

Voice: a calm, well-read friend. Plain words, short sentences, second person, present tense. No exclamation marks in errors or instructions; at most one on a completion screen. No "Oops", no "Uh-oh", no guilt, no mascot voice. Every string exists in every UI locale (the parity test stays).

| Moment | Write | Avoid |
|---|---|---|
| Correct | "Correct" / "Nicely done" (rotates among 4) | "AMAZING!!!" |
| Almost | "Almost — check the ending" + diff | "Wrong" |
| Wrong | "Not quite. The answer is …" | "Incorrect!", "You failed" |
| Second miss | "This one is tricky. Here it is — type it once to lock it in." | "Try harder" |
| Offline | "You're offline. Keep going — everything is saved on this device." | "Network error" |
| Sync failed | "Couldn't sync yet. We'll try again; nothing is lost." | "Error 503" |
| Streak at risk (in app) | "A short review keeps your 12-day streak." | "You're about to lose everything!" |
| Streak lost | "New streak starts today. Your 12 days still count toward your record." | "You lost your streak" |
| Empty library | "Words you learn will collect here. Finish a lesson to see the first ones." | "No data" |
| Beta course | "Beta: this course is still being reviewed by native speakers. Tell us if something looks off." | hiding it |
| Mic permission | "To check your speaking, Auvel needs the microphone. Audio is turned into text and then discarded." | a bare system prompt |
| Destructive confirm | "Delete your account and all progress? This can't be undone." Button: "Delete account" | "Are you sure?" / "OK" |

Buttons are verbs describing the result ("Start lesson", "Review 14 words", "Resume"). Numbers use the locale's plural rules (i18next plurals; Arabic has six forms, Persian two).

---

## 4. Key screens and flows

Each screen lists its states. "Offline" always means: content shown from the local store, a quiet `Banner` only if something the user asked for is unavailable.

### 4.1 First run (target: first answer within 60 seconds — D§9.10)

Flow: **Language of the interface** (auto-detected from `navigator.languages`, shown as one line "Auvel is in Dari · Change") → **"I want to learn …"** (course cards for the detected native language first; beta badge where it applies) → **first lesson starts immediately** as a guest on this device.

- No account, no username, no goal, no placement, no permissions before the first lesson. A local guest profile is created silently; the server guest account is created in the background when online.
- On that first completion screen, in this order and each skippable: daily goal (5/10/15 minutes, default 10), "Know some already? Find your level" (placement), "Save your progress" (account or social sign-in), then the reminder offer. **Decided (see DECISIONS.md D7)**
- Returning users on a new device: "I already have an account" link on the first screen.

States:
- Loading: course cards as skeletons (catalogue is bundled for the launch set, so this is rare).
- Offline first run: works if the app bundle includes the starter pack for the chosen course (shells do; web shows "Connect once to download your first lessons" with Retry).
- Error: pack download failed → inline Retry, alternative course still selectable.
- Success: the runner opens with a one-line coach mark on the first exercise only ("Tap the words in order").

### 4.2 Today

Compact layout, top to bottom:
1. Header: course chip (tap to switch course), avatar (→ You). Sync indicator appears here only when there is something to say.
2. **Hero card** — exactly one of, in priority order: Resume lesson (if one is in progress) → Start next lesson (title, unit, ~minutes) → Review now (if due ≥ threshold and today's lesson is done) → "Done for today" state with an optional "Keep going".
3. **Goal ring + week strip** in one card: ring shows today's XP against the goal; the strip shows seven days with the streak; freeze shown as a snowflake dot.
4. Review card (only when due > 0 and it is not already the hero): "14 words are ready to review · 3 min".
5. Quests (only if the feature is on): collapsed to one line per quest.
6. A "From your course" line: the last note or word learned, tappable to Library.

Rules: the hero is always above the fold at 375×667. Stats (total XP, lessons completed, awards) move to You. No red banners here; a failed background sync is the header indicator.

States:
- Loading: never a spinner. Renders from the local store in the first frame; if the store is empty (new device), skeletons sized to the final cards.
- Empty (no course): hero becomes "Choose a language".
- Offline: identical; hero works if the lesson is downloaded, otherwise the hero is the best available offline activity (review, downloaded lesson) and a line says "Next lesson needs a download".
- Error: store read failure → `EmptyState` with "Reload"; never a blank page.
- Success moments: ring closes; streak day ticks.

### 4.3 Path

- Header: course title in both languages, level (CEFR) chip, overall progress, course switcher.
- Body: vertical path of units; each unit is a card with its icon, title, a row of lesson nodes and a checkpoint node. The current node is marked and scrolled into view on open. The existing "unit index" becomes a jump control (sheet on compact, sticky list in the side pane on wider layouts) — needed with 60–100 units per level.
- Tracks: Core, Speaking, Situations shown as a segmented control at the top, not stacked sections.
- Tapping a node opens a small popover/sheet: lesson title, what it teaches, time, "Start" (or "Practise again"), download state.
- Locked nodes explain why and offer "Test out" where a checkpoint exists.

States: loading (skeleton path from cached course outline), offline (nodes show a small cloud-off glyph if not downloaded; "Download unit" action), error (outline missing → Retry), empty (course has no published units → honest "Coming soon"), success (node completion animates when returning from a lesson: the node fills, the connector draws to the next node).

### 4.4 The session runner (lesson, review, checkpoint, placement, mistakes)

One component and one engine for all five (R19).

Layout (compact):
```
[ ✕ ]  ▓▓▓▓▓▓▓░░░░░░░   [streak-in-session or hearts if enabled]
-----------------------------------------------
 Instruction (title-2)
 Prompt (prompt style, with audio button)
 ... answer area (options / tiles / input / mic) ...
-----------------------------------------------
[            Check            ]     <- docked, above keyboard/safe area
```
After Check, the docked area becomes the `VerdictSheet`:
```
 ✓ Correct            (or ~ Almost / ✕ Not quite)
 Your answer: …       (diff highlighted for Almost)
 Answer: …  [audio]   (when not correct)
 Why?  ▸              (expands the note; remembered per user)
 [ Report ]                        [   Continue   ]
```

Behaviour:
- **Check is local and instant** (§8.3). The verdict shows in the same frame as the press animation ends (< 100ms).
- Check is disabled until there is an answer; it is never hidden. Enter activates Check, then Continue. Focus moves to Continue on verdict.
- Auto-advance: off by default; optional "Continue automatically after correct answers" (1.2s, cancelled by any input).
- Retry rule unchanged (missed items return at the end; second miss becomes a guided confirmation) but shown: the progress bar has a faint second segment for "to revisit".
- Teaching cards are part of the same flow with a "Got it" primary button and swipe/arrow navigation back through history (existing review mode, kept).
- **Resume**: engine state is saved after every transition (§8.2). Leaving shows no scary dialog: "Leave lesson? Your place is saved." with "Leave" / "Keep going".
- Review warm-up never delays the lesson; due items, if any, are appended as a short "Quick review" after the lesson's last exercise, skippable.
- Audio for the next exercise is prefetched during the verdict.
- Speaking: mic button shows live level; transcript appears as text before grading so the learner sees what was heard; "Can't speak now" switches this session to typing with one tap and remembers for 1 hour.
- Keyboard map as D§9.8, plus `R` to replay slowly and `Ctrl/⌘+.` to open Report.

States:
- Loading: skeleton of an exercise (instruction line, prompt block, four option blocks). Target ≤ 100ms from a downloaded pack.
- Not downloaded + offline: `EmptyState` "This lesson isn't on your device yet" + "Review instead".
- Submit while offline: no difference to the learner.
- Speech unavailable (no model, no permission, no network for server STT): the exercise converts to its typed form; never a dead end.
- Audio unavailable: the audio button shows a crossed speaker with "Audio isn't available for this sentence yet"; listen-only exercises are skipped by the engine and counted as not seen, not as wrong.
- Engine error (corrupt item): skip the item, log, continue; show a toast "Skipped a broken exercise — reported for you."
- Finish: goes to Completion with no "Saving…" screen; saving is local and instant, sync is background.

### 4.5 Completion

One screen, one sequence (≤ 2.5s, skippable from the first frame — D§9.9):
1. Headline by outcome: "Lesson complete" / "Perfect lesson" / "Goal reached" / "Unit complete" / "7-day streak".
2. Three facts in a row: XP, accuracy, time.
3. Goal ring advancing; streak strip ticking if this was the first activity of the day.
4. "Words to revisit" list (existing), each with audio.
5. Primary: "Next lesson" (or "Take checkpoint"). Secondary: "Review", "Done".
6. Contextual one-time offers below the fold, at most one per completion: goal, placement, save progress, reminders.

States: offline (identical; a line "Will sync when you're online" only if the outbox is non-empty for > 24h), reload/back (static summary, no replay), reduced motion (static).

### 4.6 Practice hub

- **Review** card first: due count, estimated minutes, forecast sparkline for the next 7 days; "Review now". When nothing is due: "Nothing due — next review tomorrow around 9:00" and the card is quiet.
- **Fix mistakes**: count of recent mistakes.
- **Modes** grid: Mixed, Listening, Speaking, Conversation, Words — each opens the endless feed with that filter. Locked modes say what unlocks them.
- Course scope selector at top if the learner studies more than one course.

States: loading (skeleton cards), offline (review and mistakes work from the local store; feed works from downloaded practice packs, otherwise the modes show "Needs a connection" individually), empty (new learner: "Finish your first lesson to unlock practice"), error (per-card Retry).

Endless feed: one card at a time in the same runner chrome (not a scrolling feed of cards with their own state; R19), with a session counter and a soft stop every 10 items ("10 done. Keep going or stop here?").

### 4.7 Review (SRS) specifics

- Sessions are capped (default 20 items) with "Review more" at the end.
- Recall-first cards: show prompt → learner answers (type/tiles/speak) or, for flashcard mode, reveal → self-rating (Again / Hard / Good / Easy) with the next interval shown under each button ("10 min", "3 d").
- Leeches (items failing repeatedly) get a different treatment: the note is shown first, and the item is offered for "suspend".
- Scheduling runs locally with the same FSRS parameters as the server (§8.3).

### 4.8 Library

Tabs: Words, Mistakes, Notes.
- Words: search (matches target, translation, transliteration), filters (due, new, learning, known, leeches), sort; each row: word, gloss, strength dots, next due. Virtualised list.
- Word detail: audio, transliteration, example sentences seen, history sparkline, "Review now", "I know this" / "Don't review".
- Export (CSV, Anki) stays, in the overflow menu.

States: loading (skeleton rows), empty (per §3.9), no results ("No words match 'x'" + clear), offline (fully local), error (Retry).

### 4.9 You and Settings

You: avatar, name, member since, the stat tiles moved from Home (total XP, lessons, longest streak, words known), awards shelf, courses in progress, then a "Settings" row list.

Settings groups (each its own screen; searchable from the command bar):

| Group | Contents |
|---|---|
| Learning | Daily goal; auto-advance; word bank vs typing default; transliteration; review session size; ratings on/off |
| Sound & voice | Answer sounds; interface sounds; haptics; TTS voice per language; speech speed; microphone and speech model (size, download, delete) |
| Appearance | Theme; text size; reduce motion; app language |
| Reminders | Daily reminder time; streak reminder; review-due reminder; quiet hours |
| Downloads | Courses and levels on this device, sizes, audio on/off per course, "Download on Wi-Fi only", storage used, clear |
| Account | Sign-in methods; password; "Save your progress" for guests; sign out |
| Privacy & data | Crash reports (Never/Ask/Always); export my data; delete account; privacy policy; terms |
| About | Version, what's new, licences, send feedback |

Rules: toggles apply instantly (local first, synced after). Destructive actions live only in Privacy & data, each behind a `Sheet` with a named confirm button. Sign-out for a guest warns that progress on this device will be removed unless saved.

### 4.10 Global states

- **Offline**: never a wall for a signed-in or guest user with local data. A small cloud-off icon in the Today header; tapping it explains what works offline.
- **Sync**: silent when healthy. After 24h with unsynced changes, an `--info` banner on Today: "Changes from the last 2 days are waiting to sync." with "Sync now".
- **Session expired**: the app keeps working locally; a banner asks to sign in again to sync. Local data is never deleted because a token expired.
- **Update available**: a toast "A new version is ready" with "Reload"; never mid-session (deferred until the runner closes).
- **Storage pressure**: if the device evicts or refuses storage, Downloads explains and offers audio-free packs.
- **Crash**: `ErrorBoundary` screen with "Reload" and "Back to Today"; the in-progress session is restorable afterwards.

---

## 5. Delight moments (tasteful, each with an off switch via reduce motion / sounds / haptics)

1. **Tiles have weight.** A word tile lifts, travels to the answer line and settles with a tiny overshoot and a `selection` tick. Removing it sends it home along the same path.
2. **The verdict lands with the press.** Because grading is local, the sheet, colour, sound and haptic arrive together in under 100ms. This synchrony is the single largest quality signal in the app.
3. **Almost shows exactly what differed.** The diff highlights one or two characters; the correct form morphs in place (cross-fade of only the changed letters).
4. **The ring closes.** Reaching the daily goal completes the ring with a spring and a `success` haptic, on Today and on the completion screen, once per day.
5. **The path draws itself.** Returning from a lesson, the node fills and the connector draws to the next node (400ms), then the next node's ring begins to pulse.
6. **Combo pitch.** Consecutive correct answers in practice step the chime up the scale; a miss resets it quietly.
7. **Streak milestones as objects.** 7, 30, 100, 365 days produce a small enamel-badge award with a distinct sound, kept on the You shelf. No others.
8. **Slow replay on long-press.** Holding the audio button plays at 0.75× with a subtle waveform; a small, discoverable power feature.
9. **Greeting in the language you are learning.** Today's title rotates through greetings the learner has already been taught ("Goedemorgen"), with a tap-to-gloss. Never a word they have not met.
10. **Night shift.** After 22:00 local time, completion uses the calmer `complete` variant without confetti. Respectful of the hour.
11. **Tap any word.** Target-language words the learner has met are tappable everywhere (prompts, feedback, notes) for gloss + audio — the existing `GlossableText`, applied consistently.
12. **Persian details.** ZWNJ key on the keyboard with a one-time hint; Persian digits in Persian UI; the progress bar fills right to left. Small things that tell fa/prs learners the app was made for them.

Not doing: mascots, loot boxes, streak-loss guilt, fake scarcity, full-screen ads for our own features, sound on every tap by default.

---

## 6. Accessibility (WCAG 2.2 AA) 

Baseline already met is listed in `00-review.md` §2. Requirements for the new app:

### 6.1 Perceivable
- Contrast 4.5:1 text, 3:1 controls and focus indicators, verified by test in all three appearances (light, dark, high contrast).
- Verdicts, states and path status are conveyed by icon + text as well as colour.
- All audio content has a text equivalent available after answering; listening exercises expose "I can't listen now" which substitutes a reading variant for the session (also serves Deaf and hard-of-hearing learners).
- Text scales to 200% without loss; reflow at 320px; no horizontal scrolling except the virtual keyboard row scroll on very narrow screens.
- `prefers-contrast`, `forced-colors` (Windows High Contrast) supported: system colours used, focus rings preserved, no information in background images.

### 6.2 Operable
- Everything works with keyboard alone, switch control and voice control. Visible focus always (2.4.11 Focus Not Obscured: the docked sheet and tab bar never cover the focused element; scroll-padding accounts for them).
- Target size: 44×44 CSS px minimum for all controls (exceeds 2.5.8's 24px); documented exception for virtual keyboard keys (42×48).
- Dragging has a non-drag alternative (2.5.7): tiles are tap-to-place; reordering has move buttons exposed to assistive tech.
- No time limits. Auto-advance is opt-in and pausable. Placement and checkpoints are untimed.
- Shortcuts are single-key only when focus is not in a text field, can be turned off (2.1.4), and are listed under `?`.
- Motion: reduced-motion honoured from OS and in-app; no flashing; shake is ≤ 3 cycles.

### 6.3 Understandable
- `lang` on `<html>` and on every target-language fragment so screen readers switch voice. `dir` set explicitly, never `auto` for known languages (existing rule).
- Consistent navigation and naming across screens (3.2.3/3.2.4). Help ("Report a problem", shortcut sheet) is in the same place in every runner (3.2.6).
- Errors identify the field and say how to fix it; forms never clear on error; no re-entry of data already given in the same flow (3.3.7).
- Authentication never requires a cognitive test; paste and password managers allowed; social sign-in offered (3.3.8).

### 6.4 Robust and screen readers
- Roles: tabs as `tablist`, options as `radiogroup`, tiles as a `listbox` with an "answer" `list`, progress as `progressbar`, sheets as `dialog` (modal) or `region` (verdict).
- Live regions: one polite region per runner announces "Correct", "Almost: …", "Not quite. The answer is …" — verdict first, detail second; XP and streak changes are announced once on completion, not per answer.
- Exercise changes move focus to the instruction heading (`tabindex="-1"`), which is announced with the prompt.
- Audio buttons have names that include the content language ("Play Dutch audio"), not the sentence itself when the sentence is the answer.
- Tested with NVDA + Chrome/Edge (Windows), TalkBack (Android), VoiceOver (iOS/macOS) on the launch pairs before each release; a short script lives in `docs/` (to be written in Phase 2).

### 6.5 Automated checks in CI
axe on every route in four combinations (compact/expanded × light/dark) — exists; add: target-size check at 375×667, a 200%-text screenshot pass, a logical-property lint, a "no font below 13px" stylesheet test, and keyboard-only completion of one lesson per exercise type (Playwright).

### 6.6 Layout classes (shared by all platforms)

| Class | Width | Navigation | Layout |
|---|---|---|---|
| Compact | < 600 | Bottom tab bar (4) | Single column, docked actions |
| Medium | 600–1023 | Navigation rail (icons + labels) on the inline-start edge | Single column centred at `--content-max`; Path shows unit list + detail from 840 |
| Expanded | 1024–1439 | Rail expanded to a sidebar with labels and course switcher | Two panes: list/detail on Path and Library; Today gains a side column (ring, week, review) |
| Large | ≥ 1440 | Sidebar | Same, with `--page-max` and wider side column |

Height matters too: when the viewport is shorter than 520px (landscape phone, split screen, keyboard open), the runner collapses the header to the progress bar only and the prompt scrolls under the docked action. The 720px top-bar layout in today's CSS is removed (R13).

---

## 7. RTL and bidirectional text

Two independent axes; never conflate them:
- **UI direction** follows the interface language (fa, prs, ar → RTL).
- **Content direction** follows each fragment's language. An English-UI learner of Dari sees LTR chrome with RTL prompts; a Dari-UI learner of English sees the reverse.

Rules:
1. Layout uses logical properties only (§3.3). Flex and grid follow `dir` automatically; no `row-reverse` hacks.
2. Every target-language fragment is wrapped by `TargetText` (sets `lang`, `dir`, isolation). Interpolated values inside translated strings use `<bdi>` (existing pattern in `LessonRunnerPage.tsx:358-366`); in plain-string contexts (notifications, `aria-label`, document title) use Unicode isolates FSI/PDI (U+2068/U+2069).
3. Token sequences (tiles, word order, fill-in-blank with inline blanks) set `dir` on their own container from the answer language (existing rule in `frontend/the project notes). Blanks inside RTL sentences are inline-block with `unicode-bidi: isolate`.
4. Progress, sliders, the week strip, carousels and swipe gestures run in the inline direction: "next" is toward inline-end. Screen transitions follow the same axis.
5. Mirrored: back/forward chevrons, arrows, progress direction, send, list disclosure, undo/redo. Not mirrored: play, audio, mic, check, clock, charts with time on the x-axis keep time flowing in the UI direction (so they do mirror) but numerals stay LTR; logos never.
6. Numerals: Persian digits in fa/prs UI prose; Latin digits where the learner is being taught Latin-script numbers; scores and ratios isolated LTR. `Intl.NumberFormat` and `Intl.DateTimeFormat` with the UI locale; calendar stays Gregorian in v1 with a setting for the Solar Hijri calendar (`fa-u-ca-persian`) on the week strip later.
7. Text input: the field's `dir` follows the answer language, not the UI; the caret and placeholder align to the field's start. Placeholder text is in the UI language but aligned by the field — so placeholders are short and neutral ("Type here") or omitted in favour of a label.
8. Typography for Arabic script per §3.2; ZWNJ is preserved through input, grading and display; fa vs prs orthographic differences (ی/ي, ک/ك) are normalised by the grader, never by the display.
9. Mixed-script glosses ("کتاب (book)") isolate each run; punctuation attaches to its own run.
10. Keyboard shortcuts are not mirrored: number keys map to visual order from inline-start; arrow keys follow visual direction (Left arrow moves left on screen in both directions).
11. Store assets, the web manifest (`dir`, localised `name`/`shortcuts`), notifications and widgets are localised and direction-correct.
12. Verification: every UI screenshot test runs in en (LTR) and prs (RTL); every exercise type is played once per release in en→prs and prs→en.

---

## 8. Target architecture

### 8.1 Shape

```
packages/
  shared/            (exists)  api client, types, i18n, scripts, audio keys
    src/core/        (new, pure TS, no DOM, no network)
      grading/         port of backend/app/review/grading.py + translit nudge
      session/         SessionEngine: queue, retry rule, history, outcomes
      srs/             FSRS scheduling (port of review/fsrs.py + scheduler.py)
      progress/        XP, streak, daily goal, quests rules
      content/         pack reader, lesson assembly (interleave.ts moves here)
    src/data/        (new)
      store.ts         Store interface (below)
      outbox.ts        operation log + sync state machine
      sync.ts          push/pull against /sync
    src/platform/    (new) interfaces: storage, files, audio, haptics, notifications, speech, secureStore
    src/design/      (new) tokens.ts
frontend/            web app + PWA; implements platform/* for the browser
shells/
  android/           Capacitor (replaces android-shell/)
  ios/               Capacitor (later)
  windows-tauri/     Tauri (v2, later)
backend/             unchanged role: accounts, sync, content packs, re-grading, push
```

Dependency rule: `core` imports nothing but itself; `data` imports `core`; UI imports both; `platform` is interfaces only, implemented per shell. This is the "shared core" — the same TypeScript runs in the browser, in a Capacitor WebView and in Tauri's WebView. A React Native client could also consume it, which is why `mobile/` is frozen rather than deleted (see `02-platforms.md`).

### 8.2 Local storage

`Store` interface (async, transactional), two implementations:
- **Web/PWA**: IndexedDB (via a thin wrapper such as `idb`; no ORM). Request persistent storage (`navigator.storage.persist()`) after the first completed lesson.
- **Shells**: SQLite (Capacitor SQLite plugin / `tauri-plugin-sql`) behind the same interface. Not needed until a shell needs it; IndexedDB inside a Capacitor WebView is acceptable for v1 on Android, but iOS can evict WebView storage, so iOS requires SQLite from day one.

Stores (all keyed by `userId` first — R20):

| Store | Content | Sync |
|---|---|---|
| `profile` | User, settings, goal, active course | Two-way, last-writer-wins per field with timestamps |
| `packs` | Installed pack manifests (course, level, version, hash, size) | Pull only |
| `content` | Lessons, exercises (with answers), teaching cards, lexemes, practice templates, by pack | Pull only |
| `audio` | Blobs/files keyed by content hash (`packages/shared/src/audio/audioKey.ts`) | Pull only |
| `attempts` | Every answer: op id, exercise id, response, verdict, grader version, timestamps | Push (append-only) |
| `sessions` | In-progress engine snapshots (resume) | Local only |
| `lessonProgress` | Started/completed, best accuracy | Derived locally; reconciled on pull |
| `srs` | Per-lexeme scheduling state | Derived from review events; server state wins on conflict (below) |
| `ledger` | XP events, streak days, quest progress | Derived from attempts/completions; server totals reconcile |
| `outbox` | Pending operations in order | — |
| `meta` | Schema version, last sync cursor, grader/content versions | — |

Schema migrations are numbered and forward-only, with a test that upgrades a fixture of every previous version. **A migration never drops user stores**; if an upgrade fails, the old data is kept and the app runs read-only with an explanation. (This follows the standing rule on destructive code: no local data is deleted except by an explicit user action, and "sign out" for a guest warns first.)

### 8.3 Local grading and scheduling

> **Decided (see DECISIONS.md D6)**

- `core/grading` is a line-for-line port of `backend/app/review/grading.py` and `translit_nudge.py` (about 1,700 lines plus tables). The Python implementation remains the oracle: a script exports golden vectors from the existing pytest cases plus every compiled exercise's accepted answers and a mutation fuzz; a Vitest suite asserts identical verdicts. CI runs it on any change to either side. (Approach already proposed in `.local/logs/offline-windows-feasibility.md` §3A.)
- Each verdict records `grader_version`. On sync the server re-grades with its own implementation. If they disagree, the server's verdict is stored, the difference is logged as a parity defect, and the learner is never retroactively told a past answer was wrong; XP differences are reconciled silently in the ledger.
- Shipping answers to the client is a deliberate change (today answers are stripped: `router.py:1367`). It is acceptable: there is nothing to win by cheating except one's own XP. If opt-in leaderboards are ever enabled, only server-verified XP counts. **Decided (see DECISIONS.md D6)**
- Translit tables (2.7 MB) load lazily per language.
- `core/srs` ports `fsrs.py`/`scheduler.py` with the same parameters and fuzz seed derivation so client and server produce the same next-due date; `test_fsrs.py` cases become vectors. Do not swap in a different FSRS library without parity (same caution as the feasibility report).

### 8.4 Sync

Model: **operation log, server authoritative for derived state.**

- Every user action that changes state is an operation: `answer`, `lesson_start`, `lesson_complete`, `review_answer`, `setting_change`, `goal_change`, `word_flag`. Each has a client UUID (`client_operation_id` — the server already de-duplicates answers on it, `router.py:660-676`), a device id, a client timestamp and a monotonic per-device sequence number.
- The UI applies the operation to the local store at once (optimistic by construction) and appends it to the outbox.
- `POST /sync/batch` (new; anticipated in `sw.js:3-4`): body = ordered operations since the last acknowledged sequence + the client's pull cursor. Response = per-operation result (accepted / duplicate / rejected with reason), authoritative snapshots of changed derived state (XP totals, streak, SRS states touched, lesson progress), and a new cursor. Idempotent by op id; safe to retry whole batches.
- Triggers: on app start, on regaining connectivity, after a session ends, every 5 minutes while active, and via Background Sync where the platform has it. Back-off: 5s, 30s, 2m, 10m, then hourly.
- Conflicts:
  - Attempts are append-only facts; two devices never conflict, they interleave by server receive time.
  - Streak and XP are recomputed on the server from all attempts with the learner's timezone rule; the client displays its local computation until the snapshot arrives, then adopts the server's. A day earned offline counts for the day it was done (client timestamp, bounded: the server accepts client timestamps up to 14 days old and never in the future beyond 5 minutes of skew).
  - SRS: the server replays review events in timestamp order; its resulting state replaces the client's for the items touched.
  - Settings: last-writer-wins per field.
  - Lesson completion is idempotent per (user, lesson, op id).
- Guest → account: the local profile's `userId` is re-keyed in one transaction after the server confirms the conversion; the outbox is preserved.
- Until `/sync/batch` exists, the outbox drains through the existing endpoints one operation at a time (they already accept the needed calls), so the client work is not blocked on backend work.
- Auth: access/refresh as today. Tokens in `localStorage` on web (with the enforced CSP), in Keychain/Keystore via `platform/secureStore` in shells. An expired session never blocks local use.

### 8.5 Content packs

- Unit of download: `{course, level}` content pack (JSON, gzip; launch set is about 3 MB for 15 packs) and a matching audio pack (zip of content-hashed mp3/opus, per level, optional).
- New endpoints (CONTRACT first): `GET /packs/index` (versions, sizes, hashes), `GET /packs/{course}/{level}/{version}.json.gz`, `GET /packs/{course}/{level}/audio-{version}.zip` or per-file via the existing `/media/audio/{hash}.mp3`. Static files behind a CDN-friendly cache header; the compiler (`scripts/compile_content.py`) already emits the JSON, so this is packaging plus an "include answers" switch.
- Policy: on course choice, download the current level's content pack immediately (small) and audio for the next 3 units; then the rest on Wi-Fi/unmetered or on request. Shells bundle the A1 starter packs for the launch courses so first run works offline.
- Updates: packs are immutable and versioned. A new version downloads in the background and swaps in between sessions; exercise ids are stable, so attempts and SRS state carry over. A lesson in progress finishes on the version it started with.
- Integrity: SHA-256 per pack checked before install; failed downloads resume or retry, never leave a half-installed pack (install into a new key/dir, then switch the manifest pointer).
- Storage budget shown in Settings → Downloads; removing a pack removes content and audio only, never progress.

### 8.6 Service worker (web/PWA)

Move from the hand-written shell cache to a build-generated precache (Workbox `injectManifest` or `vite-plugin-pwa`, keeping the existing push and audio-range handlers):
- Precache: hashed JS/CSS, fonts, icons, `index.html`, sound files. This removes the "first offline launch may fail" gap noted in `msstore-pwa-readiness.md` §2.
- Runtime: packs are stored by the app in IndexedDB, not by the SW; audio stays in Cache Storage via the existing range-aware handler, with the 400-entry cap replaced by pack-aware accounting.
- Update flow: new SW waits; the app shows the "new version" toast when no session is running; `skipWaiting` on user action.
- Background Sync (`sync` event) drains the outbox where supported (Chromium); elsewhere the in-app triggers suffice.
- API responses are still never cached by the SW; local-first data lives in the store, where it is user-keyed.

### 8.7 Speech

- STT order: on-device platform recogniser where it supports the language (shells) → client Whisper (web/desktop, existing; explicit download consent with size) → server STT → typed fallback. The absent-signal rule for pronunciation feedback is unchanged.
- TTS order unchanged (recorded → pre-rendered → cloud → platform voice → honest fallback); pre-rendered audio becomes the normal case once audio packs exist. Rendering the launch audio is a content/infra task on the critical path for every "offline" claim.

### 8.8 Front-end state

- **Server-derived, cached**: TanStack Query stays for anything still fetched (catalogue, pack index, leaderboards if ever). 
- **Local-first data**: read through small hooks over the Store with change subscriptions (`useLiveQuery`-style); no global state library is needed.
- **Session**: `SessionEngine` is a pure reducer `(state, event) → state` with serialisable state; the UI is a view of it. Unit-testable without React; the same engine drives all five runner kinds.
- **Preferences**: one typed `settings` object in the Store replacing the dozen ad hoc `localStorage` helpers (`frontend/src/lib/*Preference*.ts`), migrated once, still per-device where that was the intent and synced where it helps (theme, goal, text size are synced; voice choice is per device).

### 8.9 Performance budgets

| Metric | Budget |
|---|---|
| Press → visual response | ≤ 100ms |
| Check → verdict (local) | ≤ 100ms p95 on a mid-range Android phone |
| Cold start to interactive Today (installed, warm cache) | ≤ 1.5s |
| Open a downloaded lesson | ≤ 150ms to first exercise |
| Route change | ≤ 200ms to content or skeleton |
| INP ≤ 200ms, CLS ≤ 0.05, LCP ≤ 2.5s (Fast 4G, first visit) | lab, in CI |
| Entry JS (gzip) | ≤ 180 KB (today about 155 KB eager; grading core is lazy-loaded with the runner) |
| Animation | 60fps, no long task > 50ms in a session |

Measured by a Lighthouse CI job and a Playwright trace of five answers at 4× CPU throttle (extends D§9.4).

### 8.10 Privacy, security, observability

- Local data is unencrypted at rest on web (browser sandbox); in shells it lives in app-private storage; tokens in secure storage.
- Audio recordings are processed and discarded (existing behaviour); on-device recognition preferred.
- Sentry stays consent-gated; add sync-health breadcrumbs (queue length, last success) with no content.
- Parity defects (client vs server verdict) are reported automatically with exercise id and grader versions, never the learner's identity beyond the user id already in scope.

---

## 9. Notifications (principles; platform mechanics in `02-platforms.md`)

- Asked after the first completed lesson, with a pre-prompt explaining the value; never on launch.
- Three kinds, each separately switchable: daily reminder at a chosen time (default: the time of the first lesson, next day); streak reminder (only if today has no activity, sent 2 hours before the learner's usual time window ends, never after 21:30 local); review due (at most one per day, only when ≥ 10 items are due).
- Copy is specific and never guilt-based: "14 words are ready — about 3 minutes." Tapping lands directly in the relevant session.
- Hard cap: one notification per day in total by default; after three ignored days, reminders pause themselves and say so in the app.
- Local scheduling is preferred over server push wherever the platform allows (works offline, no token management); server push remains for web.

---

## 10. Acceptance for "feels like a great app"

A release meets the bar when all are true on the reference pair en→nl and on prs→en / en→prs:
1. Airplane mode after first run: complete a lesson, a review session and a practice set; reopen the app; all progress is there; reconnect; another device shows the same progress within one minute.
2. Kill the app mid-exercise; reopen; Resume returns to the same exercise with the answer area empty and prior history intact.
3. Check → verdict is visually simultaneous with sound and haptic on a mid-range Android phone.
4. A new learner reaches the first exercise in ≤ 60s and ≤ 3 taps, in their own language, without creating an account.
5. A full lesson is completable with keyboard only, with TalkBack/VoiceOver/NVDA, at 200% text, and with reduced motion — each in LTR and RTL.
6. No emoji as UI, no "Loading…" text, no inline hex, no font under 13px, no physical left/right in styles.
7. The acceptance lists in D§9.1–9.10 pass.

---

## 11. Roadmap (incremental; no rewrite)

Each phase ships on its own and leaves the app better. Sizes are for one developer with agent help; they are estimates, not commitments. Lanes follow the repo's division of labour.

### Phase 0 — Quick wins (1–2 weeks)
The fifteen items in `00-review.md` §4. No new dependencies. Includes sending `client_operation_id`, lesson resume via IndexedDB snapshot, autocorrect attributes, UI-language detection, emoji → icons, motion tokens and the docked verdict sheet.
Exit: D§9.1, 9.2, 9.7 acceptance; resume works; first-run language is right for fa/prs/nl browsers.

### Phase 1 — Design system and session engine (3–4 weeks)
- `tokens.css` + `tokens.ts`; the primitives of §3.8 in `frontend/src/ui/`; a `/showcase` page listing every component in light/dark × LTR/RTL (the route exists: `frontend/src/pages/ShowcasePage.tsx`).
- Extract `SessionEngine` into `packages/shared/src/core/session`; build `<SessionRunner>`; move Lesson first, then Review, Checkpoint, Placement, Practice onto it; delete the copies.
- Migrate inline styles screen by screen (lint rule set to warn, then error).
- Skeletons everywhere; theme switch; text-size setting; keyboard map and shortcut sheet.
Exit: one runner; zero inline hex; `LessonRunnerPage.tsx` under 200 lines; all five flows visually identical in feedback.

### Phase 2 — Screens (3–4 weeks)
Today, Path, Practice hub, Library, You/Settings, first run and Completion per §4; four-destination navigation with redirects; layout classes of §6.6 replacing the 720px top bar. Accessibility test script written and run.
Exit: §10 items 4–6.

### Phase 3 — Local store and outbox (3–4 weeks)
- `Store` on IndexedDB; all progress reads go through it; settings consolidated.
- Outbox draining through existing endpoints; remove the "session unavailable" wall for users with local data; offline banner and sync indicator.
- Workbox precache; update toast.
- Backend (drafting tool B lane, CONTRACT first): `POST /sync/batch`, accept bounded client timestamps.
Exit: with a previously opened lesson cached, the app is usable offline except for grading (answers queue with a "will be checked when online" state — an interim state that Phase 4 removes).

### Phase 4 — Local grading, SRS and packs (5–7 weeks; the largest)
- Golden-vector harness first, then the TypeScript grading port, then FSRS and progress rules.
- Pack endpoints and compiler packaging (drafting tool B lane); pack manager and Downloads settings; audio packs once audio is rendered.

> **Decided (see DECISIONS.md D6, D4)**
- Server re-grade and parity reporting.
Exit: §10 items 1–3. This is the point at which the app is honestly "offline-first", and the Tauri v2 build becomes a packaging task rather than a port.

### Phase 5 — Shells and stores (parallelisable after Phase 2; details in `02-platforms.md`)
- Windows: Store PWA via PWABuilder (needs domain + TLS, per the readiness report) — can ship after Phase 2.
- Android: Capacitor shell replacing `android-shell/`, Play internal track after Phase 3, public after Phase 4.
- iOS/iPadOS: Capacitor shell with SQLite store after Phase 4.


> **Decided (see DECISIONS.md D1, D2, D3, D5)**
### Phase 6 — Platform delight (ongoing)
Widgets (Android, iOS), app shortcuts, command bar, window-controls overlay on Windows, local notifications in shells, streak awards shelf, illustrations, designed sound set if not already done in Phase 1. **Decided (see DECISIONS.md D11, D7)**

Dependencies that are not code and gate real releases: public domain + TLS; rendered audio; native review status for store claims; a privacy contact; Play, Apple and Microsoft store accounts. **Decided (see DECISIONS.md D2, D3, D5, D8, D9, D10, D12)**

### What not to do
- Do not rewrite in React Native or a native toolkit (see `02-platforms.md` §1).
- Do not start the grading port before the golden-vector harness exists.
- Do not add a state-management library, a CSS framework or an animation library; tokens, CSS and the View Transitions API are enough.
- Do not turn hearts on to "add stakes".
