# Auvel end-to-end suite (Playwright)

Built by Session 3 (INFRA) per `docs/SONNET_BUILD_PROMPT_UPGRADES.md` to
convert flows that have already been manually verified in a live browser
(per `CLAUDE.md`/`docs/BUILD_LOG.md`) into a repeatable one-command
check, instead of re-driving the browser interactively for every
regression pass.

## Preconditions (this suite does NOT provision these)

1. The local Docker stack is up and seeded: start Docker (Docker Desktop / `sudo service docker start` on
   WSL / `colima start` on macOS), then `cd ../backend && docker compose up -d`, migrations applied, content
   imported per `scripts/content_manifest.txt`. Per the ownership map
   in `docs/SONNET_BUILD_PROMPT_UPGRADES.md`, the Docker stack has ONE
   owner at a time -- this suite assumes someone else (or you, in a
   different terminal) already brought it up correctly. It will not
   start Docker, run migrations, or import content itself.
2. `frontend/.env`'s `VITE_API_BASE_URL` points at that backend.
3. The demo courses exist -- several specs navigate to "Farsi Foundations"
   and "Dari Foundations" by name. Since 2026-07-22 the seed CLI no longer
   creates them by default, so seed them explicitly on the test stack:
   `cd ../backend && docker compose exec api python -m app.content.seed --with-demo-courses`
   (or `LINGO_SEED_DEMO_COURSES=1`). Never do this on a real deployment.
   If the seed data changes shape, update `tests/helpers.ts`'s
   `goToFarsiFoundationsUnits` accordingly.
4. The target backend's registration rate limit is raised. This suite
   registers a fresh account per test, serially, from one IP --
   `register_rate_limit_max` (`backend/app/core/config.py`, default 5)
   blows past its window well before the suite finishes and every
   subsequent test fails on `register_rate_limited` 429s, poisoning
   further runs for ~an hour. Set `REGISTER_RATE_LIMIT_MAX=1000` and
   `LOGIN_RATE_LIMIT_MAX=1000` in the target backend's `backend/.env`
   (local dev only -- never raise these in a prod-facing env) before
   running.

## Running

```bash
cd e2e
npm install
npx playwright install --with-deps chromium   # first time only
npm test
```

`playwright.config.ts` starts `npm run dev` in `../frontend` on a
dedicated port (5175 -- must stay inside the backend's `CORS_ORIGINS`
allowlist, currently `5173-5176`, or every request gets silently
CORS-blocked) if `PLAYWRIGHT_BASE_URL` isn't set, deliberately avoiding
5173/5174 so it never fights a human's interactive dev-server tab. Set
`PLAYWRIGHT_BASE_URL` to point at an already-running frontend instead
(e.g. the live server, or someone else's dev session) if you'd rather
not spin up a second one.

**Verified live, 2026-07-05** (Session 3/INFRA): ran the full suite
against the actual local stack (backend already up on :8000, seeded
en-fa content). First run failed all 8 specs on `waitForURL` after
register -- root cause: the dedicated e2e port wasn't in the backend's
`CORS_ORIGINS` allowlist, the exact "confusing CORS false-lead"
CLAUDE.md warns about. Fixed by moving to port 5175 (already
whitelisted). Second run: 5/8 passed, 3 failed on `strict mode
violation: getByRole('link', ...) resolved to 2 elements` -- the NavBar
renders both a desktop topbar nav and a mobile tabbar nav, so every nav
link matches twice; fixed by adding `.first()` everywhere a nav link is
targeted. Third run: **8/8 passed** in ~9s.

**Re-run live, 2026-07-06**, against a genuinely fresh isolated stack,
after a full night of unrelated backend changes (Phases A-F, rate
limiting, FastAPI/Starlette CVE bump, Azure TTS, Whisper STT,
`content_key` admin-import) had landed with the suite never re-run.
**10/10 passed.** One real, generic gotcha for any future run: this
suite registers one fresh account per spec, serially, all from the
same IP -- **this now collides with the `REGISTER_RATE_LIMIT` (5
registrations/hour/IP) added 2026-07-06** past the 5th spec (`curl`
loop confirmed: attempts 1-5 got `201`, 6th+ got `429
register_rate_limited`). `backend/app/core/config.py`'s
`register_rate_limit_max`/`login_rate_limit_max` (defaults unchanged,
5/10) are now `Settings`-configurable specifically so an isolated test
stack's own `.env` can raise them without touching production. If a
future run against a *shared* stack hits `register_rate_limited`
partway through, this is why -- run against your own isolated stack
with these raised, or space runs out. Full root-cause, plus an
unrelated mid-run migration race this pass also hit (a concurrent
session landed `0013_content_keys.py` while this stack was already
migrated to 0012 -- fixed with a second `alembic upgrade head`, no
rebuild needed since the compose file bind-mounts the repo), are in
`docs/BUILD_LOG.md`'s matching entry.

## What's covered

- `auth.spec.ts` -- register, logout, wrong-password error message
  (regression guard for the fixed "Session expired" bug), guest login.
- `course-picker.spec.ts` -- two-step language picker reaching a real
  seeded course's unit path (en-fa "Farsi Foundations").
- `dari-course.spec.ts` -- the same coverage for en-prs "Dari
  Foundations" (fa and prs are separate content/RTL/script/keyboard
  code paths, per the publish-gate scope in CLAUDE.md; fa passing
  doesn't prove prs works).
- `lesson-teaching.spec.ts` -- opening a lesson, advancing through
  teaching cards into the exercise phase.
- `practice-feed-locked.spec.ts` -- a brand-new user sees the locked
  state, not a crash or empty feed.
- `nav.spec.ts` -- every bottom-tab route renders without an error
  boundary swallowing it.
- `account-deletion.spec.ts` -- the DELETE /me flow through the real
  ProfilePage UI: typed-email confirmation gate (disabled until the
  exact email is typed), redirect to /login with the one-time deleted
  notice, and the deleted account's credentials failing with a real
  auth error. Deliberately one test, one freshly-registered throwaway
  account created inside the test itself -- it deletes the account it
  runs on, so it must never be pointed at a shared/reused account.
- `refresh-tokens.spec.ts` -- the refresh-token flow shipped 2026-07-10
  (30-min access tokens + rotating refresh tokens, `POST
  /auth/refresh`): register returns both tokens and both genuinely
  work; refresh rotates the pair; a rotated-out token is rejected with
  `refresh_token_reused` AND its reuse revokes every refresh token the
  user has (reuse = possible theft). API-only via Playwright's
  `request` fixture -- no browser -- because the web frontend's
  auto-refresh-on-401 integration hadn't landed when this was written
  (that half is a `test.skip` placeholder in the file with the
  suggested approach for whoever lands it). Targets `E2E_API_BASE_URL`
  if set, else `frontend/.env`'s `VITE_API_BASE_URL`, else
  localhost:8000; a `beforeAll` guard fails fast with a real
  explanation if the target backend predates the feature (the usual
  cause is the documented "bind mount syncs code but uvicorn doesn't
  reload" footgun -- force-recreate the api container and run
  migration 0021). Registers 2 fresh accounts, so it draws from the
  same `REGISTER_RATE_LIMIT` budget as the rest of the suite.

- `word-bank.spec.ts` -- beginner tap-to-build word bank on A1
  `translation` and `writing_prompt` items carrying `prompt.word_bank`:
  tiles are picked by text (display order is shuffled), a placed tile is
  tapped back out and reappears in the bank, and Check POSTs
  `/exercises/{id}/answer` with exactly `{"response": "<space-joined
  tiles>"}` (the typed-answer string shape; no `input_mode`), then the
  correct banner and lesson completion.
- `almost-feedback.spec.ts` -- an `AnswerResult.result: "almost"` verdict
  renders the amber `.feedback-banner.almost` (headline, correct form, the
  learner's attempt, `--almost-soft` background, not the red incorrect
  style), Continue is enabled and advances to the next item, the almost
  item is never re-queued, and the lesson completes.
- `desktop-layout.spec.ts` -- at 1280x800 the left side rail ("Main
  navigation") and the right "Your progress" sidebar are visible and laid
  out side by side on Home and the course map, the tab bar is hidden, and
  nothing scrolls horizontally; at 390x844 the tab bar shows, the desktop
  chrome is hidden, and nothing scrolls horizontally. Both widths also
  check a lesson screen (word-bank item) for horizontal overflow.
- `situations-shelf.spec.ts` -- a course whose units include one
  `track: "situation"` unit shows a "Situations" shelf collapsed by default
  (`aria-expanded="false"`, unit not rendered); expanding it reveals the
  unit unlocked (even though the server sent `locked: true`) and opening
  it works; the "Recommended for you" badge and the sidebar's "Next
  lesson"/Continue both point at the first CORE unit even though the
  situation unit comes first in the payload. An all-core course (including
  a unit with no `track` field, as older servers send) has no shelf.

## Route-mocked specs (no backend needed)

The four specs above (`word-bank`, `almost-feedback`, `desktop-layout`,
`situations-shelf`) never touch a real backend. `tests/mocks.ts` installs
one `page.route` that intercepts every `fetch`/XHR to any origin other
than the SPA's own (so it works whatever `VITE_API_BASE_URL` is), serves
contract-shaped fixtures (types from `packages/shared/src/api/types.ts`),
answers anything unhandled with a 404 in the app's `{"error": {code,
message}}` envelope and logs it as `[mock-api] UNMOCKED ...`, and seeds a
logged-in session by writing `access_token`/`refresh_token`/`user` to
localStorage via `addInitScript` (`GET /auth/me` is mocked). No Docker, no
seeded content, no registration rate limit -- only the frontend dev
server (which `playwright.config.ts` starts, or point
`PLAYWRIGHT_BASE_URL` at one already running). Run them alone with:

```bash
cd e2e
npx playwright test tests/word-bank.spec.ts tests/almost-feedback.spec.ts \
  tests/desktop-layout.spec.ts tests/situations-shelf.spec.ts
```

If the Chromium that matches the pinned `@playwright/test` isn't
installed (and can't be downloaded), set `PLAYWRIGHT_CHROMIUM_PATH` to an
existing Chromium/Chrome binary; the config passes it as
`launchOptions.executablePath`. Unset, Playwright uses its own browser.

To extend: build on `mockedApp(page, baseURL, {units, lessons, storage})`
and override single endpoints with `api.on(method, "/path/:param", fn)`
(later registrations win). Lessons are opened through the real course map
-> unit -> lesson links (`openLessonViaCourseMap`) because the runner reads
the course (and so its CEFR level, which gates the word bank) from router
state, not the URL.

## Resolved flakiness in `goToCourseUnits` (2026-07-05) -- two real bugs, one Playwright API trap

Building `dari-course.spec.ts` (extending coverage from en-fa-only to
the en-prs launch pair) surfaced a genuinely difficult debugging
session. Three distinct problems compounded, and clearing each one
revealed the next:

**1. Stale-DOM race (real, fixed).** The original level-check handling
did `if (url ends in /level) { click "first button" }`. For a
single-unit course (auto-skips via an effect, no button ever renders),
the "first button" match could land on the *next* page's first
element after the auto-redirect fired mid-check, silently navigating
into the wrong place. Fixed by scoping to a class specific to the
level-choice cards rather than a bare `getByRole("button")`.

**2. `.continue-card` class collision (real, fixed).** That same class
turned out to also be used by the course-picker page's own course
list -- the page this flow navigates *from*. `waitForURL` resolves the
instant the URL changes, which can fire a tick before React finishes
swapping the component tree, so a check running immediately after
could transiently match the *previous* page's still-mounted card, not
a real level-choice button. Fixed by first confirming
`LevelCheckPage` had actually mounted, via its own unique heading text.

**3. The actual root cause (found via explicit timestamped console
logging, after both fixes above still didn't work): `locator.isVisible({ timeout })` does NOT poll or retry for that duration.**
It's a single, near-instant check of current state; `timeout` barely
affects it. Confirmed live: the heading-visibility check returned
`false` within **3 milliseconds** of the URL changing, every time --
not because it waited and gave up, but because it checked once, immediately,
before React Query's `unitsQuery` had resolved. This meant the code
always took the "skip" branch, for every course, regardless of whether
it actually had one unit or several. It only ever looked correct for
the single-unit Dari course because skipping the click is the *right*
behavior there anyway -- the multi-unit Farsi course exposed it
immediately, hanging forever waiting for a level choice that was never
made. (`locator.waitFor({ state: "visible" })` is the one that actually
polls -- that's the fix, racing it against the alternative "already
auto-skipped" outcome via `Promise.race`, since which of the two
happens isn't knowable in advance.)

A fourth, real but separate problem surfaced mid-investigation:
polling the shared dev stack's course list showed the `en-prs`
course's ID changing on every single check within an ~8-second window
-- another session actively re-importing/recreating it concurrently.
That's a genuine finding (now in
`docs/SONNET_BUILD_PROMPT_UPGRADES.md`'s ownership map as a new rule:
don't destructively reimport a course while another session might be
verifying against the shared stack), but it was a *second*, independent
issue layered on top of bug #3 above -- confirmed by reproducing bug #3
on a fully isolated, single-user Docker Compose project (separate
project name, separate port, separate volume, seeded fresh) where no
other session could possibly interfere. The isolated stack ruled out
concurrency as bug #3's cause and made the true root cause visible.

**Current state, verified**: all 10 specs pass consistently -- three
full runs against the isolated stack (10/10 each) and one against the
shared stack (10/10) once the transient content churn there had
settled. `goToCourseUnits` in `helpers.ts` now correctly handles both
the single-unit auto-skip and multi-unit real-choice cases for any
course, not just the two currently in `LAUNCH_COURSES`.

## What's deliberately NOT covered (known gap, not an oversight)

**Answering exercises through to lesson completion.** Grading is real
server-side truth (`grade()` in `backend/app/api/router.py`) -- a
generic bot has no way to know the correct answer for arbitrary
content without either hardcoding per-unit answers (brittle, breaks
the moment content changes) or the backend exposing a test-only
"reveal answer" endpoint (doesn't exist). This means the suite proves
navigation, teaching-card flow, and locked/unlocked states, but NOT
that a real exercise grades correctly end-to-end -- that still needs a
human in the browser, exactly per the project's existing verification
bar. If full-lesson e2e completion becomes worth the investment,
whoever owns the backend (Session 1/Codex) would need to add a
dev-only endpoint that returns an exercise's accepted answer for a
test account; flagging here rather than building it unilaterally since
it's a backend/security-surface decision, not an INFRA one.

Also not covered: RTL rendering correctness, virtual-keyboard
interaction, TTS audio playback, and anything requiring visual
judgment -- Playwright can click the dismiss/use-device-keyboard button
and assert DOM state, but "does this look right in Farsi" is still a
human check.

## Fitting into `scripts/verify.sh`

Wired in as an opt-in fourth stage: `scripts/verify.sh --e2e` runs this
suite alongside the other three; `--e2e-only` runs just this. Not part
of the default (no-flags) run -- it needs a live seeded backend plus a
one-time `npm install`/browser install, so it's slower and more
environment-dependent than the other three stages, and a missing
Playwright install should never fail the fast checks sessions run
constantly.
