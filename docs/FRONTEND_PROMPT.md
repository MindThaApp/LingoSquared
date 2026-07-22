# Frontend Build Prompt (Claude-owned)

Building the local web frontend for **Lingo²**, in parallel with Codex's
backend build under `backend/`. This doc exists so Codex can sanity-check
it against the contract and backend design before either side commits to
implementation.

**Scope boundary:** only write inside
`"$LINGO_REPO"/frontend/` (plus possibly proposing
edits to `docs/CONTRACT.md` if a genuine gap is found — flagged, not
silent). Never touch `/Users/raminazizi/dev/portal`.

Not building mobile (Expo) yet — web only, LAN-testable on desktop/iPad/
tablet browsers. This is explicitly a stepping stone: the API contract must
stay clean enough that Expo iOS/Android apps can consume the same backend
later without backend changes.

## Stack

React + TypeScript + Vite. Plain fetch or a thin API client wrapper —
no heavyweight state library needed at this scale (React Query or
equivalent for server-state caching is reasonable; avoid Redux). Talks to
the backend only via the endpoints in `docs/CONTRACT.md`; `VITE_API_BASE_URL`
env var points at it (default `http://localhost:8000` for local dev,
overridable for LAN testing against the Debian server's IP).

## Core screens/flows

- Auth: register / login, store JWT, `GET /auth/me` on load to restore
  session.
- Language/course picker: `GET /languages` → pick source + target (enforce
  source != target client-side too, not just relying on backend), then
  `GET /language-pairs` / `GET /courses` to list available courses for that
  pair.
- Course → units → lessons drill-down (`GET /courses/{id}/units`,
  `GET /units/{id}/lessons`).
- Lesson runner: `GET /lessons/{id}` → `POST /lessons/{id}/start` → render
  exercises one at a time → `POST /exercises/{id}/answer` per exercise →
  `POST /lessons/{id}/complete` at the end. Show immediate right/wrong
  feedback and running XP for the lesson.
- Review/SRS screen: `GET /me/reviews` (due items) → answer flow via
  `POST /reviews/{id}/answer`, similar immediate feedback.
- Profile/dashboard: `GET /me/progress`, `GET /me/streak`, `GET /me/xp`,
  `GET /me/achievements`.

## Exercise renderers (one component per type, matches contract enum)

`multiple_choice`, `translation`, `reverse_translation`, `fill_in_blank`,
`word_order`, `matching_pairs`, `dialogue_response`, `grammar_check`,
`flashcard`, `reading_comprehension`, `writing_prompt` — all get real,
interactive components. `listening_placeholder` and `speaking_placeholder`
render a disabled "coming soon" card (no audio/mic implementation yet) —
this matches the backend, which only defines their schema for now.

## RTL / script handling

Never hardcode which language codes are RTL. Every language object from
`GET /languages` includes `direction: "ltr"|"rtl"` and `script`; the
frontend sets `dir` on the relevant text containers from that field. This
must work correctly for Farsi and Dari specifically, including inside
exercises where RTL and LTR text are mixed (e.g. an en→fa translation
exercise shows both an LTR English prompt and an RTL Farsi answer field in
the same view) — each text block gets its own `dir`, not one global page
direction. Concretely: each exercise prompt's `text_blocks` array (see
`docs/CONTRACT.md`) carries its own `language_code`/`direction` per block —
render each block's container with that block's `dir`, never the lesson's
or course's direction.

## Farsi/Dari as distinct

The course picker must show Farsi and Dari as separate, clearly labeled
entries (native names, not just "Persian variant A/B") in both source and
target position — never merged or presented as dialect variants of a single
option.

## What this build explicitly does NOT do yet

No offline/PWA support. No push notifications. No payments. No admin UI for
content import/export (that's curl/API-only for now, per the backend
prompt's admin endpoints). No Expo/mobile code.

## Resolved (was "open questions for Codex", now settled in docs/CONTRACT.md)

1. Yes — `GET /lessons/{lesson_id}` returns the full lesson with all
   exercises and all type-specific prompt fields (options, word_bank,
   pairs, text_blocks) in one payload. No correct answers are ever included
   client-side; grading is always server-side via the answer endpoints.
2. Flat arrays everywhere except `GET /me/reviews`, which uses simple
   cursor pagination if due-item count could exceed ~200 for a user
   (backend decides the exact threshold, documents it).
3. Access tokens are 24h bearer tokens, no refresh-token flow for this LAN
   MVP. On any 401, do a hard logout (clear stored token, redirect to
   login) rather than attempting silent refresh.

## Integration

Codex owns the final backend+frontend integration pass (see "Integration
ownership decision" in `docs/CONTRACT.md`) — once both builds are done,
Codex wires this frontend against the real backend and Docker Compose.
Claude (whoever builds this) fixes any frontend-specific rendering/UX
defects that surface during that pass.

## When finished, report

1. File tree
2. How to run locally (`npm install`, `npm run dev`, required env vars)
3. Which screens/flows are implemented vs. stubbed
4. Any place a backend response shape didn't match `docs/CONTRACT.md` and
   what was done about it
