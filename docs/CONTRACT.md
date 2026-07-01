# Lingo² Shared Contract (source of truth)

This file is the single source of truth that both the backend (Codex) and
frontend (Claude) must agree on. Any change here requires updating both
sides. Do not duplicate these definitions elsewhere — reference this file.

## Supported languages (fixed set, ISO 639-1/639-3 where applicable)

| code | name (en) | script | direction |
|------|-----------|--------|-----------|
| en   | English   | latin  | ltr |
| nl   | Dutch     | latin  | ltr |
| fr   | French    | latin  | ltr |
| de   | German    | latin  | ltr |
| it   | Italian   | latin  | ltr |
| es   | Spanish   | latin  | ltr |
| ru   | Russian   | cyrillic | ltr |
| zh   | Chinese (Mandarin, Simplified) | han | ltr |
| fa   | Farsi (Persian) | arabic | rtl |
| prs  | Dari      | arabic | rtl |

The `script` field is one of exactly: `latin`, `cyrillic`, `han`, `arabic`
(machine-readable, lowercase — this is what the API returns, not a display
label; the display label like "Perso-Arabic" is prose only, never a field
value).

Farsi (`fa`) and Dari (`prs`) are **distinct language records** — separate
vocab, grammar notes, cultural notes, pronunciation notes, and courses in
both directions. They may share cognate terms but nothing is auto-merged.

Language codes are the stable identifiers used in the DB and API. Never
hardcode "en" as an assumed source language anywhere in backend or frontend
logic — source_language and target_language are always explicit, independent
fields, and source != target is enforced.

## Language metadata returned by `GET /languages`

```json
{
  "code": "fa",
  "name": "Farsi",
  "native_name": "فارسی",
  "script": "arabic",
  "direction": "rtl"
}
```

Frontend uses `direction` to set `dir="rtl"|"ltr"` on exercise/vocab text
elements. Do not infer direction from language code client-side — always use
the API-provided field.

## Exercise type enum (shared, exact string values)

`multiple_choice`, `translation`, `reverse_translation`, `fill_in_blank`,
`word_order`, `matching_pairs`, `listening_placeholder`,
`speaking_placeholder`, `dialogue_response`, `grammar_check`, `flashcard`,
`reading_comprehension`, `writing_prompt`

Placeholder types (`listening_placeholder`, `speaking_placeholder`) render
as "coming soon" in the frontend — backend still defines the schema/fields
now so no migration is needed later.

## Core API endpoints (exact paths)

Auth: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`

Languages/courses: `GET /languages`, `GET /language-pairs`, `GET /courses`,
`GET /courses/{course_id}`, `GET /courses/{course_id}/units`,
`GET /units/{unit_id}/lessons`

Lessons: `GET /lessons/{lesson_id}`, `POST /lessons/{lesson_id}/start`,
`POST /exercises/{exercise_id}/answer`, `POST /lessons/{lesson_id}/complete`

Progress/review: `GET /me/progress`, `GET /me/reviews`,
`POST /reviews/{review_item_id}/answer`, `GET /me/streak`, `GET /me/xp`,
`GET /me/achievements`

Admin: `POST /admin/content/import`, `GET /admin/content/export`,
`POST /admin/content/validate`, `GET /admin/content/missing-report`

There is deliberately **no public `POST /courses`**. Course/unit/lesson
content is created only via the admin content-import path (or the seed
command), never via a user-facing create endpoint — this app is a content
consumer, not a course-authoring tool, for this phase. Anywhere the spec
says "course creation" as a test target (see BACKEND_PROMPT.md minimum
tests), that means exercising the import/seed path end-to-end and asserting
the resulting course/units/lessons are queryable via the GET endpoints
above — not a REST create endpoint.

## Request/response schemas (illustrative — field names are authoritative, exact types are the implementer's call within reason)

These are intentionally not exhaustive OpenAPI specs (the backend's
auto-generated `/docs` is authoritative for full detail) but every field
named here must exist with this name and this general shape, since both
sides are built independently against this doc.

**Auth**

`POST /auth/register` and `POST /auth/login` request:
```json
{ "email": "string", "password": "string", "display_name": "string (register only, optional)" }
```
response (both):
```json
{
  "access_token": "jwt-string",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": { "id": "uuid", "email": "string", "display_name": "string" }
}
```
Access tokens are short-lived-ish (24h) bearer tokens. No refresh-token
flow for this LAN-testing MVP — on 401, frontend does a hard logout
(clears token, redirects to login). Revisit refresh tokens when this goes
beyond LAN testing.

`GET /auth/me` response: `{ "id", "email", "display_name", "created_at" }`.

**Languages/courses**

`GET /languages` → array of the language objects shown above.

`GET /language-pairs` → flat array, no pagination (only ~90 possible rows):
```json
[ { "source_language": "en", "target_language": "fa", "course_count": 1 } ]
```

`GET /courses?source=en&target=fa` → flat array:
```json
[ { "id": "uuid", "source_language": "en", "target_language": "fa", "title": "string", "level": "string", "unit_count": 1 } ]
```

`GET /courses/{course_id}` → same shape as one list item, plus
`"description"`. Does not inline units (fetch those separately) — avoids two
sources of truth for unit ordering.

`GET /courses/{course_id}/units` and `GET /units/{unit_id}/lessons` → flat
arrays of `{ "id", "title", "order", "lesson_count" }` /
`{ "id", "title", "order", "exercise_count" }`.

**Lessons**

`GET /lessons/{lesson_id}` returns the full lesson **including all of its
exercises in one payload** (frontend should not need N+1 calls per
exercise). Each exercise's `prompt` object contains only what's needed to
render and answer it — **never the correct answer** (grading is always
server-side, in the `POST /exercises/{id}/answer` call). Any exercise with
mixed-language text (e.g. an English prompt + a Farsi answer field) exposes
each piece of text as its own `text_block` with its own `language_code` and
`direction`, rather than one lesson- or exercise-level direction:

```json
{
  "id": "uuid",
  "unit_id": "uuid",
  "title": "string",
  "exercises": [
    {
      "id": "uuid",
      "type": "translation",
      "order": 1,
      "prompt": {
        "text_blocks": [
          { "text": "Where is the station?", "language_code": "en", "direction": "ltr" }
        ],
        "options": ["...multiple_choice only..."],
        "word_bank": ["...word_order only..."],
        "pairs": ["...matching_pairs only (left/right items, shuffled, no answer key)..."]
      }
    }
  ]
}
```

`POST /exercises/{id}/answer` request: `{ "response": <shape depends on
exercise type — string, string[], or pair-mapping> }`. Response:
```json
{ "correct": true, "correct_response": "...", "xp_awarded": 10, "feedback": "string (optional)" }
```

`POST /lessons/{id}/start` and `POST /lessons/{id}/complete` just need to
return enough to update client state (e.g. `{ "started_at" }` /
`{ "completed_at", "xp_awarded", "accuracy" }`) — no strict shape mandated
beyond that.

**Progress/review**

`GET /me/reviews` — due review items. Flat array is fine for LAN-scale
testing; if item count could plausibly exceed ~200 for a single active
user, use simple cursor pagination (`?cursor=...`, response includes
`next_cursor`). Backend's call which threshold applies once real usage
data exists; document the choice made.

`POST /reviews/{id}/answer` — same response shape as the exercise-answer
endpoint, plus `next_due_at`.

## Auth mechanism

JWT bearer token, returned from `/auth/login` and `/auth/register` as
`access_token`. Frontend stores it and sends `Authorization: Bearer <token>`.
See the schema section above for token lifetime and the no-refresh-token
decision for this phase.

## Error shape (consistent across all endpoints)

```json
{ "error": { "code": "string_machine_code", "message": "human readable" } }
```

## Environment / ports (LAN dev)

- Backend API: container port 8000, host port configurable via `.env`
  (`API_PORT`, default 8000), bound to `0.0.0.0` inside Docker.
- Postgres: internal only, not exposed to host by default.
- Frontend dev server: port 5173 (Vite default), configurable via `.env`.
- Backend base URL is injected into frontend via `VITE_API_BASE_URL`.

## Ownership for this file

Either side may propose changes, but changes must be reflected in both the
backend and frontend prompts before implementation starts. This file is
the tiebreaker in any integration conflict.

## Integration ownership decision

Codex owns the final backend+frontend integration pass (wiring the real
frontend against the real running backend, Docker Compose bring-up,
resolving any drift from this contract) — Codex is the one holding the
authoritative OpenAPI/auth/error contract, so defects are less likely to
fall into a no-man's-land between the two builds. Claude fixes any
frontend-specific rendering/UX defects surfaced during that integration
pass. Decided after a Codex cross-review of this doc and both build
prompts (see docs/ review notes) — revisit if it stops working in
practice.
