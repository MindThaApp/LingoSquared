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
`reading_comprehension`, `writing_prompt`, `listen_select`, `listen_type`,
`dictation`, `speak_response`, `listen_order`, `dialogue_comprehension`,
`speak_repeat`

Placeholder types (`listening_placeholder`, `speaking_placeholder`) render
as "coming soon" in the frontend — no audio/mic pipeline exists for those
two. **`speak_repeat` was mistakenly grouped with them until 2026-07-06**:
real shipped content (e.g.
`fr.a1.unit01.lesson03.exercise07_read_liaison`) proves it DOES compile
with a genuine `correct_response`/`accepted_answers`, same as any other
free-text exercise — the claim above that it "has no checkable answer"
was simply wrong, not a description of a real constraint. It now has a
real component (`SpeakRepeat.tsx`, mic + typed-fallback) — see "Speech-to-
text" below. The six `listen_*`/`speak_*`/`dialogue_comprehension` types
added after the original MVP reuse existing frontend components by prompt
shape (`listen_select`≈`multiple_choice`, `listen_type`≈`translation`,
`listen_order`≈`word_order`, `dialogue_comprehension`≈`multiple_choice`,
`speak_response`/`dialogue_response` share a component) — see
`ExerciseRenderer.tsx` for the exact dispatch table, which is the
authoritative mapping.

`dictation` (added 2026-08-02) ≈ `listen_type` (learner hears a
target-language sentence via `audio_text`/`media_asset_key` and types what
they heard, no source text shown — authored with `target_blocks: []`, so it
renders through the `Translation` component like `listen_type`) but is graded
**orthography-strict by type**: the backend forces strict spelling grading for
`dictation` regardless of the Latin-script typo-tolerance default, so a
single-letter misspelling grades incorrect. **Boundary-punctuation exception
(approved 2026-08-04):** for `dictation` only, the learner's answer and the
accepted answers are compared after trimming whitespace and stripping
leading/trailing boundary punctuation (`. ? ! … ¿ ¡ ؟ । ۔ ،` — the final
constant lives in `backend/app/review/grading.py`); internal punctuation,
case, diacritics, and script remain byte-strict. The pre-existing
invisible-formatting-only forgiveness (e.g. ZWNJ and Arabic harakat, which
no keyboard emits) continues to apply to `dictation` ahead of this strict
comparison, exactly as it does for every other strict grading path —
"diacritics remain byte-strict" above covers visible diacritics (e.g. é
vs e), not the invisible-formatting marks forgiven by that function. See
`docs/DICTATION_EXERCISE_SPEC.md`.

`ExercisePrompt` additionally carries (all optional, additive): `audio_text`
+ `audio_language_code` (a target-language phrase to synthesize/play for
`listen_*` types — the learner hears this before answering, it is not
necessarily identical to any visible `text_block`), and
`answer_language_code` (the language the learner's answer should be
written in — drives which virtual keyboard, if any, the frontend shows;
falls back to scanning `text_blocks` for older content compiled before
this field existed).

## Core API endpoints (exact paths)

`/v1` is the canonical API prefix for new clients, including the future
mobile app. The unprefixed root paths remain available indefinitely as a
backward-compatible alias for the existing web frontend.

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

### `POST /admin/content/import` — content_key-based update-in-place, 2026-07-06

Every `UnitImport`/`LessonImport`/`ExerciseImport`/`TeachingCard` (via
`TeachingImport`) gains an **optional, additive** `content_key: str |
None` field (a stable authoring key, e.g.
`"prs.a1.unit01.lesson01.exercise04.match_final_group"` — globally
unique by construction, matching `PracticeTemplateImport.content_key`'s
existing shape). `scripts/compile_content.py` now emits it on every
unit/lesson/exercise/teaching-card in the compiled payload.

**What changed, semantically:** re-importing into an already-existing
course used to only ever *append* units whose `order` wasn't already
present, silently leaving every previously-imported row exactly as it
was forever — there was no way to ship a fix to already-shipped
content. Now, for any incoming unit/lesson/exercise/teaching-card whose
`content_key` matches an already-shipped row's `content_key`, that row
is **updated in place** (same primary key — every `ExerciseAttempt`/
`ContentIssueReport`/`ReviewItem`/`LessonProgress` that references it
is completely unaffected, since none of those snapshot or re-derive
from the row's content). Anything with no content_key match falls back
to the original behavior unchanged: create if its `order` is free,
otherwise leave the existing row alone.

**Never deletes.** A unit/lesson/exercise/teaching-card that existed
before but is absent from a new payload is left in place, orphaned but
intact — real user history referencing it is never destroyed (and the
`RESTRICT` foreign keys on `exercise_attempts`/`content_issue_reports`
wouldn't allow deleting it anyway).

**Retirement of vanished exercises (2026-09-29).** Import now *retires*
exercises that disappeared from the content: within every lesson present
in the payload (matched by `content_key`), an existing exercise whose
non-null `content_key` is absent from the incoming lesson gets `retired_at`
set (timestamp) instead of staying live. Exercises with no `content_key`
are never retired. A retired exercise that reappears in a later import is
un-retired (`retired_at` cleared) and updated in place. Rows are still
never deleted, so attempt history, SRS and progress keep their ids.
Lessons/units absent from the payload are untouched (partial/append
imports stay safe). Retired exercises are excluded from lesson detail
(`GET /lessons/{id}`), lesson exercise counts, and review/practice/
checkpoint pools; answers already in flight to a retired exercise are
still graded (no error).

Request, additive: optional boolean `retire_missing` (default `true`);
`false` keeps the old keep-everything behavior.

**Pre-existing rows (imported before this feature shipped) have
`content_key = NULL` forever** unless manually reconciled — this
migration does not attempt to backfill historical content_keys, since
there's no reliable way to recover which already-shipped row a given
key would have corresponded to. Re-importing content that predates
this feature behaves exactly as it did before (position-only
create/skip), until that content is re-authored with the compiler's
new content_key-emitting version.

`ImportOut` response, additive:
```json
{
  "imported_courses": 0,
  "created_units": 2, "updated_units": 1,
  "created_lessons": 6, "updated_lessons": 3,
  "created_exercises": 40, "updated_exercises": 5,
  "retired_exercises": 3, "unretired_exercises": 0,
  "created_teaching_items": 12, "updated_teaching_items": 8,
  "warnings": [
    "unit prs.a1.unit03: lesson order 2 conflicts with an existing, unaffected lesson; skipped (content_key='prs.a1.unit03.lesson02')"
  ]
}
```
`retired_exercises`/`unretired_exercises` are ints (0 when `retire_missing`
is false).

`warnings` is **non-fatal** — populated when an incoming item *does*
carry a content_key but its `order` still collided with something
unrelated (an author coordination conflict worth surfacing, not a
reason to fail the whole request; everything unambiguous already
committed by the time this is known). This is distinct from the
existing `422 content_invalid` failure, which is raised **before**
anything is written, for the pre-existing upfront structural
validation checks (duplicate orders within the same payload, missing
required blocks, etc.) — that behavior is unchanged.

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
  "refresh_token": "opaque-refresh-token",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": { "id": "uuid", "email": "string", "display_name": "string", "is_admin": false }
}
```
`is_admin` (added 2026-07-10) is UX-only, for gating admin UI (e.g.
`AdminContentPage`) on the real value instead of firing admin API calls
and reacting to the 403 after the fact — the actual security boundary for
every `/admin/*` route is unchanged: the `admin_user` dependency, checked
server-side on every request regardless of what the client believes.
Access tokens are intentionally short-lived bearer JWTs: 30 minutes
(`expires_in: 1800`). Installed mobile clients must not require a full login
every day, but access tokens should have a small blast radius if copied from
memory or logs; long-lived session continuity comes from refresh tokens
instead.

Refresh tokens are opaque, DB-backed tokens with only a password-hash-style
hash stored server-side. They live for 60 days by default, are revocable, and
rotate on every use: when a refresh token is accepted, the server revokes that
row and returns a fresh access token plus a fresh refresh token. Presenting an
already-revoked refresh token is treated as possible token reuse/theft; the
server revokes all refresh tokens for that user and returns 401
(`refresh_token_reused`).

One exception keeps a lost response from logging the user out. A token that
was revoked BY ROTATION (never by logout or reuse detection), whose successor
is still the live head of the chain (not itself rotated, revoked or expired),
is answered with that SAME successor plus a new access token when either:

- the request also carries `next_refresh_token` equal to that successor (the
  caller provably already holds it: an identical retry of the original
  request), at any age; or
- the rotation happened at most `REFRESH_REUSE_GRACE_SECONDS` ago (default
  30; `0` disables) -- a reload that lost the response, or two tabs
  refreshing at once -- and that window has answered fewer than
  `REFRESH_REUSE_GRACE_MAX_REPLAYS` (default 3) retries of this rotation.
  Past that cap a retry is reuse, so the window cannot mint access tokens
  without limit.

No new refresh token is minted on that path, so the chain never branches.
Concurrent refreshes of one token are serialized with a row lock and all
receive the same successor. Every rotation and every revoke-all of a user
first takes that user's row lock, so a revoke-all cannot miss a successor
being minted at the same moment. Anything else that presents a rotated-out
token is reuse.

`POST /auth/refresh` request:
```json
{
  "refresh_token": "opaque-refresh-token",
  "next_refresh_token": "optional: client-chosen successor, 43-128 base64url chars"
}
```
`next_refresh_token` (added 2026-10-10) lets the client generate its next
refresh token and persist it BEFORE sending, so a page closed mid-request can
resend the identical request later. It must be at least 43 base64url
characters (256 bits) and is rejected with 422 when it is trivially
low-entropy (fewer than 16 distinct characters). The server uses it as the
new refresh token unless a token with that value already exists (or is being
created by a concurrent request), in which case it picks one itself. The
response's `refresh_token` is always authoritative.
response:
```json
{
  "access_token": "jwt-string",
  "refresh_token": "new-opaque-refresh-token",
  "token_type": "bearer",
  "expires_in": 1800
}
```

`POST /auth/logout` request:
```json
{ "refresh_token": "opaque-refresh-token" }
```
Revokes that refresh token if it exists and belongs to a still-existing
session. Returns `204 No Content`; callers should discard both access and
refresh tokens locally.

`POST /auth/social` (added 2026-07-11, spec-first — implementation follows)
request:
```json
{
  "provider": "google | apple",
  "id_token": "provider-issued ID token (JWT) from the client-side sign-in flow",
  "display_name": "string, optional — Apple only sends the user's name on the FIRST authorization, so clients pass it through here when present"
}
```
response: identical shape to `POST /auth/login` (access_token + refresh_token
+ user). The server verifies the id_token server-side against the provider's
published JWKS (signature, expiry, issuer, and audience — audience must be in
the configured allowlist: `GOOGLE_OAUTH_CLIENT_IDS` / `APPLE_AUDIENCE_IDS`
env vars, comma-separated to cover web + iOS + Android client IDs). The raw
id_token is never stored.

Account resolution, in order: (1) an existing `(provider, provider_subject)`
identity row → that user; (2) no identity row but a provider-VERIFIED email
matching an existing account → link a new identity row to that account
(unverified provider emails never link — they create a fresh account, since
linking on an unverified email would let anyone claim an existing account);
(3) otherwise create a new passwordless user (null `password_hash`;
password login for such accounts returns the normal invalid-credentials
error, and `POST /auth/social` is their only login path until a password-set
flow exists — an accepted gap, same tier as the missing password reset).
Identities live in a new `user_identities` table (user_id, provider,
provider_subject unique per provider, created_at) — additive migration,
guarded per the standing migration rule.

Unset/empty provider env vars → `503 social_login_unavailable` for that
provider (same graceful-degradation convention as the TTS keys); the other
provider and password auth are unaffected. `GET /auth/me` gains an
additive `"identities": [{"provider": "google", "created_at": "..."}]` field
(subjects/emails from providers are not echoed back).

`GET /auth/me` response: `{ "id", "email", "display_name", "is_admin", "created_at", "identities" }`.

**Admin user management**

Every endpoint in this section is admin-only, enforced server-side by the
same `/admin/*` guard as content import. Admin status is true when either the
normalized email is listed in `ADMIN_EMAILS` or the persisted `users.is_admin`
column is true. `ADMIN_EMAILS` remains the bootstrap escape hatch.

`POST /admin/users` request:
```json
{ "email": "string", "display_name": "string" }
```
response `201`:
```json
{
  "user": { "id": "uuid", "email": "string", "display_name": "string", "created_at": "iso-datetime", "xp": 0, "streak": 0, "last_activity": null, "enrolled_courses": [], "is_admin": false, "is_active": true },
  "temporary_password": "server-generated plaintext shown once"
}
```
The temporary password is cryptographically random, stored only as a hash, and
never retrievable again.

`GET /admin/users?q=&limit=50&offset=0` response:
```json
{
  "items": [
    { "id": "uuid", "email": "string", "display_name": "string", "created_at": "iso-datetime", "xp": 0, "streak": 0, "last_activity": null, "enrolled_courses": [ { "id": "uuid", "title": "string" } ], "is_admin": false, "is_active": true }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```
`q` searches email/display name case-insensitively. `last_activity` is the
user stats `last_activity_date`.

`POST /admin/users/{id}/reset-password` response:
```json
{ "temporary_password": "new server-generated plaintext shown once" }
```
The old password stops working immediately; existing refresh tokens are
revoked.

`POST /admin/users/{id}/deactivate` and
`POST /admin/users/{id}/activate` return the same user object as list rows.
Inactive users are refused at password/social login and token refresh, and
existing access tokens stop working because authenticated dependencies reject
inactive users on every request. Deactivation also revokes existing refresh
tokens.

`DELETE /admin/users/{id}` permanently deletes that user and user-owned
learning state, using the same cascade behavior as `DELETE /me`. Returns
`204 No Content`.

`POST /admin/users/{id}/admin` request:
```json
{ "is_admin": true }
```
response: the same user object as list rows. Demoting the last remaining
admin is refused with `409 last_admin`.

`POST /admin/users/{id}/unlock` request:
```json
{ "course_id": "uuid, optional", "unit_id": "uuid, optional", "lesson_id": "uuid, optional" }
```
Exactly one target selector may be supplied. Response:
```json
{ "completed_lessons": 0, "passed_checkpoints": 0, "introduced_lexemes": 0 }
```
The endpoint marks the targeted lesson/unit/course state exactly like normal
completion/checkpoint paths: completed `lesson_progress`, matching
`skill_progress`, passed unit checkpoints, and due SRS rows for introduced
lexemes. It does not weaken normal unlock rules for anyone else.

`GET /me/export` (auth required) returns the authenticated account's complete
data export as one JSON document — the data-portability counterpart to
`DELETE /me` (export before deleting; deletion is irreversible). Served with a
`Content-Disposition: attachment; filename="lingosquared-export-<date>.json"`
hint. Arrays are complete row listings, not paginated — an export is a
snapshot, not a browsing API. Top-level shape:

```json
{
  "format_version": 1,
  "exported_at": "iso-datetime",
  "profile": { "id": "uuid", "email": "string", "display_name": "string", "created_at": "iso-datetime", "timezone": "IANA-string-or-null" },
  "stats": { "total_xp": 0, "streak_days": 0, "last_activity_date": "date-or-null", "daily_goal": 20, "streak_freezes_available": 0, "last_freeze_used_date": "date-or-null" },
  "skill_progress": [ { "course_id": "uuid", "completed_lessons": 0, "mastery": 0.0 } ],
  "lesson_progress": [ { "lesson_id": "uuid", "started_at": "iso-datetime", "completed_at": "iso-datetime-or-null", "correct_count": 0, "answer_count": 0, "xp_earned": 0 } ],
  "exercise_attempts": [ { "exercise_id": "uuid", "response": "any-json", "correct": true, "outcome": "string-or-null", "xp_awarded": 0, "created_at": "iso-datetime" } ],
  "practice_attempts": [ { "practice_item_id": "uuid", "course_id": "uuid", "prompt": {}, "response": "any-json", "correct": true, "xp_awarded": 0, "created_at": "iso-datetime" } ],
  "checkpoint_attempts": [ { "unit_id": "uuid", "total_items": 12, "passed": true, "score": 0.9, "weak_outcomes": [], "created_at": "iso-datetime", "scored_at": "iso-datetime-or-null" } ],
  "lexeme_srs": [ { "lexeme_id": "uuid", "token": "string", "english_gloss": "string", "language_code": "string", "course_id": "uuid", "mastery": 0.0, "ease_factor": 2.5, "interval_days": 0, "repetitions": 0, "due_at": "iso-datetime", "last_reviewed_at": "iso-datetime-or-null", "introduced_at": "iso-datetime", "suspended": false } ],
  "review_items": [ { "exercise_id": "uuid", "ease_factor": 2.5, "interval_days": 0, "repetitions": 0, "mastery": 0.0, "due_at": "iso-datetime" } ],
  "achievements": [ { "code": "string", "title": "string", "earned_at": "iso-datetime" } ],
  "quest_completions": [ { "quest_code": "string", "date": "date", "awarded_at": "iso-datetime" } ],
  "vocabulary_progress": [ { "content_item_id": "uuid", "mastery": 0.0, "last_reviewed_at": "iso-datetime-or-null" } ],
  "grammar_progress": [ { "content_item_id": "uuid", "mastery": 0.0, "last_reviewed_at": "iso-datetime-or-null" } ],
  "push_subscriptions": [ { "endpoint": "url", "created_at": "iso-datetime" } ],
  "content_issue_reports": [ { "id": "uuid", "exercise_id": "uuid-or-null", "practice_item_id": "uuid-or-null", "page_path": "string-or-null", "category": "string", "description": "string-or-null", "status": "string", "created_at": "iso-datetime" } ]
}
```

`stats` is `null` for an account that somehow has no `user_stats` row.
`achievements` lists earned achievements only (the catalog itself isn't user
data). `lexeme_srs` inlines each lexeme's `token`/`english_gloss`/
`language_code` so the export is meaningful standalone, not a bag of opaque
ids. Deliberately excluded: `refresh_tokens` rows (bearer-token session
material, not personal data — also revoked wholesale by `DELETE /me`
regardless) and push-subscription `p256dh`/`auth` values (channel crypto
keys, not personal data). Strictly scoped to the bearer token's own account;
no admin/other-user form exists.

`DELETE /me` (auth required) permanently deletes the current user's account
and user-owned learning state. Returns `204 No Content` on success. There is
no admin override form of this endpoint; a bearer token can only delete its
own account.

**Languages/courses**

`GET /languages` → array of the language objects shown above.

`GET /language-pairs` → flat array, no pagination (only ~90 possible rows):
```json
[ { "source_language": "en", "target_language": "fa", "course_count": 1 } ]
```

`GET /courses?source=en&target=fa` → flat array:
```json
[ { "id": "uuid", "source_language": "en", "target_language": "fa", "title": "string", "level": "string", "unit_count": 1, "recommended": false } ]
```

`recommended` is an additive course-list/detail field. It defaults to
`false`; course imports may set it to `true` to distinguish the preferred
course when multiple courses share a CEFR level. Content overlays may set
`course.recommended`; the compiler forwards it as `courses[].recommended`
when present and omits it when absent.

`GET /courses/{course_id}` → same shape as one list item, plus
`"description"`. Does not inline units (fetch those separately) — avoids two
sources of truth for unit ordering.

`GET /courses/{course_id}/units` → flat array of:
```json
[
  {
    "id": "uuid",
    "title": "string",
    "order": 1,
    "lesson_count": 4,
    "completed_lesson_count": 2,
    "section": "reading_writing",
    "locked": false,
    "checkpoint_passed": false,
    "content_key": "en.a1.unit06.family",
    "track": "core"
  }
]
```
`track` (`"core" | "situation"`, always present, default `"core"`) is an
additive unit field. Situation units are optional side content: they are
always unlocked in the UI and never the "next recommended" unit, and
`speaking_unlocked`, first-placement unit selection and any
course-completion/progress summary count **core units only**. Content YAML
sets it via an optional per-unit `track: situation` in realization files
(absent = core); the compiler validates the value (only `core|situation`) and
passes it through as the import payload unit's `track`, and
`POST /admin/content/import` updates it in place on existing units matched by
`content_key` (no rows moved or renumbered). No units are flagged yet — which
units to demote is an open product question (A2_REBUILD_PLAN Q8).
`completed_lesson_count` is learner-specific: with authenticated optional auth
it counts that user's lessons in the unit whose `LessonProgress.completed_at`
is non-null; anonymous requests return `0` for every unit.
`GET /units/{unit_id}/lessons` → flat array of
`{ "id", "title", "order", "exercise_count" }`.
`content_key` is the unit's stable authoring key (e.g.
`"en.a1.unit06.family"`, nullable for any unit imported before content_key
tracking existed) — the frontend uses its topic slug to pick a per-unit
icon (`frontend/src/lib/unitIcons.ts`), not just for content-import
matching.

**Lessons**

`GET /lessons/{lesson_id}` returns the full lesson **including all of its
exercises in one payload** (frontend should not need N+1 calls per
exercise). Each exercise's `prompt` object contains only what's needed to
render and answer it. Graded exercise types **never expose the correct
answer** (grading is server-side in `POST /exercises/{id}/answer`). The
explicit exception is `flashcard`: its prompt includes `back_text_blocks`
because the learner must reveal the back before self-reporting recall. Any exercise with
mixed-language text (e.g. an English prompt + a Farsi answer field) exposes
each piece of text as its own `text_block` with its own `language_code` and
`direction`, rather than one lesson- or exercise-level direction:

```json
{
  "id": "uuid",
  "unit_id": "uuid",
  "title": "string",
  "teaching": [
    {
      "kind": "vocabulary" | "phrase" | "grammar_note" | "dialogue" | "pronunciation_note" | "cultural_note" | "reading",
      "title": "string (optional, e.g. the grammar point's name)",
      "text_blocks": [
        { "text": "سلام", "language_code": "prs", "direction": "rtl" },
        { "text": "hello", "language_code": "en", "direction": "ltr" }
      ],
      "note": "string (optional — usage/grammar explanation in the source language)"
    }
  ],
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
        "word_bank": ["...word_order tiles, or generated tiles for A1/A2 free-text prompts..."],
        "pairs": ["...matching_pairs only (left/right items, shuffled, no answer key)..."],
        "back_text_blocks": ["...flashcard only — the back-of-card text_blocks, same shape as text_blocks, revealed client-side after the user flips the card..."]
      }
    }
  ]
}
```

**Teaching content (new — fixes a real pedagogy gap)**: lessons used to
jump straight to graded exercises with no way for the learner to have
actually encountered the word/phrase/grammar point being tested first.
`teaching` is an ordered array presented **before** the exercises, one
card per new vocabulary item, phrase, grammar point, or dialogue line
introduced in this lesson — every exercise in the lesson should test
something the learner was just shown in `teaching`, not something novel.
Frontend renders `teaching` as a "learn" phase (present each card, TTS on
every `text_block` same as everywhere else, learner clicks through at
their own pace, no grading/XP here) that must complete before the
existing exercise-answering phase begins. Legacy lessons with an empty or
missing `teaching` array just skip straight to exercises (backwards
compatible), but all new/reseeded content should include it.

**Vocabulary-example addition (2026-07-07, additive, no breaking
change)**: every teaching card may carry an optional `examples` array —
one entry per example sentence showing the card's word used in real
context, each the same `text_blocks` shape as the card itself
(target-language sentence first, then an optional source-language gloss
block):

```json
{
  "kind": "vocabulary",
  "title": "Great",
  "text_blocks": [
    { "text": "Prima", "language_code": "nl", "direction": "ltr" },
    { "text": "great / fine", "language_code": "en", "direction": "ltr" }
  ],
  "note": "…",
  "examples": [
    {
      "text_blocks": [
        { "text": "Prima, en met jou?", "language_code": "nl", "direction": "ltr" },
        { "text": "Great, and with you?", "language_code": "en", "direction": "ltr" }
      ]
    }
  ]
}
```

Authored in the realization as `example:` (a single text-block mapping,
or a list of them) on the teaching card, plus `example_gloss:` (a string,
or a positionally-matched list) on the overlay's teaching entry — see
`docs/content/AUTHORING_GUIDE.md` §19 for the authoring rules and the
compiler's enforcement (required for `kind: vocabulary` in files at
`schema_version` ≥ 1.1; warning-only for the existing 1.0 corpus until
the retrofit lands). Frontend renders `examples` inside the same
teaching card (each entry's blocks through the standard `TextBlockList`,
so per-sentence TTS comes for free); cards without `examples` render
exactly as before.

**Reading-track tap-to-gloss addition (2026-08-03, additive, no breaking
change; `docs/READING_TRACK_SPEC.md`)**: a `reading` teaching card may
carry an optional `glosses` map — `{ token → in-context English gloss }`,
where each key is the **exact surface token** (including
capitalization/inflection) as it appears in the card's passage
(`text_blocks[].text`), and each value is a short sense-in-context English
gloss. It is authored in the overlay (source-direction) alongside the
whole-passage `gloss`, embedded by the compiler, and served on the
teaching item:

```json
{
  "kind": "reading",
  "text_blocks": [
    { "text": "Kasia verandert van baan omdat ze verhuist.", "language_code": "nl", "direction": "ltr" }
  ],
  "glosses": {
    "verandert": "changes",
    "baan": "job",
    "verhuist": "is moving"
  }
}
```

Only content words worth helping with are glossed — NOT every token.
Frontend: a `reading` card whose `glosses` map is present and non-empty
renders its passage through `GlossableText` (each glossed surface token is
tappable → a small popover shows the English gloss; non-glossed tokens and
all separators render as plain text, RTL-aware via the block's
`direction`), keeping the usual `SpeakButton` narration. Every other card
kind — and any `reading` card without a `glosses` map (the existing
corpus) — renders exactly as before through the plain `TextBlockList`.

**Phase D additions (2026-07-05, additive, no breaking change):**

- Every `text_block` (in `teaching` and in exercise `prompt`s) gains an
  optional `speaker: string` field. A multi-turn `dialogue` teaching
  card must use one `text_block` per speaker turn, each with its own
  `speaker` value, instead of the old pattern of one block containing
  the whole exchange as literal text with embedded "Name:" labels and
  newlines — that pattern breaks TTS (reads straight through mid-line,
  chokes on the embedded newline) regardless of provider. The compiler
  rejects any NEW dialogue card whose single `text_block` contains a
  newline plus a "Name:"-style label pattern; existing content is
  migrated separately, not blocked by the new validator. Frontend
  renders the speaker label itself from `speaker` and calls the speak
  button once per turn/block, never once for the whole card.
- `Exercise.prompt`/teaching-card entries may carry a
  `media_asset_key: string` (already emitted by the compiler for
  `listen_*` types and any content declaring recorded audio — see
  `scripts/audio_manifest.py`'s `media_assets:` block). `GET /media/
  {media_asset_key}` serves the recorded clip (long cache headers,
  404 if not yet recorded — this is expected and not an error state,
  most keys won't have a recording yet). `POST /admin/media/upload`
  (admin auth, multipart: `key` + audio file) is how a recording gets
  attached to a key.
- Audio playback priority chain (frontend): recorded asset (if
  `media_asset_key` present and `GET /media/{key}` resolves) → cloud TTS
  (Google Cloud for its 8 supported languages, Azure Cognitive Services
  Speech for `fa` — see the Text-to-speech section below, existing quota
  logic unchanged) → browser `speechSynthesis` → the existing honest "no
  voice available" message. `prs` (Dari) still has zero cloud-TTS
  coverage from either provider, so for that one language the chain is
  effectively recorded-asset-or-nothing-but-the-honest-fallback until a
  given string has been recorded.

`POST /exercises/{id}/answer` request: `{ "response": <shape depends on
exercise type>, "client_operation_id": "uuid (optional)" }`:
`client_operation_id` is an optional client-generated operation key (up to
36 characters). Repeating the same key for the same user returns the stored
answer result and does not create another attempt or award XP again. Clients
should use a fresh key for each distinct answer submission. Without this
field, existing submission behavior is unchanged.
- Free-text types (`translation`, `writing_prompt`, `fill_in_blank`, etc.):
  a plain `string`.
- `word_order` / `listen_order`: `string[]` in the order the learner
  arranged the word bank.
- `matching_pairs`: `{ left: string, right: string }[]` — one entry per
  pair, in the SAME order as the exercise's `prompt.pairs` (i.e.
  `pairs.map(p => ({ left: p.left, right: matches[p.left] }))`, not a
  flat `{ [left]: right }` dict). This is the exact shape every
  `matching_pairs` exercise's content-side `accepted_answers` is
  authored in (see `docs/content/overlays/**`) — **a flat dict here
  will never compare equal and silently grades every match wrong**
  (real bug, shipped and fixed 2026-07-05, see `docs/BUILD_LOG.md`
  and the matching CLAUDE.md footgun entry).
  **`grade()` (`app/api/router.py`) additionally canonicalizes either
  representation** (flat `{left: right}` dict OR `{left,right}[]`, in
  any order) for this exercise type specifically, so both the frontend's
  documented submission shape above AND the Endless Practice engine's
  `derive_answer()` (`app/practice/service.py`, which produces a flat
  dict as `PracticeItem.correct_response` for `matching_pairs`) grade
  correctly against each other — found live 2026-07-05 while verifying
  the fix above: without this, the practice-engine path would have
  broken the identical way, just mirrored (list submitted, flat dict
  stored). Prefer the documented list-of-pairs shape for anything new;
  the dict tolerance exists for robustness, not as the preferred form.
- `flashcard`: exactly `"known"` or `"unknown"` — this self-report
  determines correctness and SRS scheduling rather than comparing typed
  text.

**Spoken-answer input mode (2026-09-29, additive):** Lesson, review, and
practice answer requests may include `"input_mode": "typed" | "spoken"`.
The field is optional and defaults to `"typed"`, preserving existing
clients and typed grading.
Clients send `"spoken"` when the submitted answer is a microphone
transcript. Spoken grading applies to any exercise type and also defaults
on for `speak_repeat` and `speak_response` exercises when the field is
omitted. It accepts small transcript differences, including bounded
word-level edits, one short missing or extra function word, and equivalent
digit/number-word tokens for supported languages. An answer accepted only
by this spoken tolerance is returned as `result: "almost"`; as with other
`almost` results, `correct` remains true and progress/SRS continue.
Typed requests retain the existing grading rules, including strict
checkpoint grading. Spoken tolerance applies to checkpoint transcripts too.

Response:
```json
{ "correct": true, "result": "correct", "correct_response": "...", "xp_awarded": 10, "feedback": "string (optional)" }
```

The first `POST /lessons/{lesson_id}/complete` for a lesson with exercises
requires at least one answer attempt since that lesson session was started.
Otherwise it returns HTTP 409 with the standard error envelope and code
`lesson_not_attempted`. Lessons with no exercises remain completable.

**Phase C additions (2026-07-05, additive, no breaking change):**

- `result: "correct" | "almost" | "incorrect"` — new field alongside the
  existing `correct` boolean (kept for backward compatibility; `correct
  == true` iff `result != "incorrect"`, i.e. `almost` still counts as
  correct for XP/SRS purposes). `almost` means a free-text answer was
  within Damerau-Levenshtein distance 1 of an accepted answer and the
  exercise/language allows typo tolerance (see `orthography_strict`
  below) — maps to SM-2 quality 4 via `quality_for_result()` in
  `app/review/sm2.py` (already an isolated seam from Phase A). Choice-type
  exercises (multiple_choice, matching_pairs, word_order, etc.) never
  produce `almost` — only free-text typed answers can.
- Choice-type exercise prompts may include an optional
  `feedback_by_option: { "<option string>": "<explanation>" }` map.
  Stored inside the existing `Exercise.feedback` column (already
  free-form; this phase encodes a JSON object into it rather than a
  plain string — zero DB migration) and surfaced via the answer
  response's `feedback` field when the learner's chosen wrong option has
  a specific entry, instead of the exercise's generic feedback text.
  Falls back to the generic `feedback` text (or nothing) when the chosen
  option has no specific entry.
- New content-compiler flag `orthography_strict: true | false` (per
  exercise, author override). Default is tolerant (typo-distance-1
  accepted as `almost`) for Latin-script target answers; default is
  STRICT (`almost` never awarded, distance-1 is just `incorrect`) for
  fa/prs and any non-Latin-script target answer, since single-letter
  distinctions are frequently the tested content itself.
  Script-introduction lessons (teaching the alphabet/script itself) are
  always strict regardless of the flag. A same-distance edit that
  crosses a script-purity boundary (e.g. Arabic ي vs. Persian ی) is
  never silently forgiven as a typo even in tolerant mode — it's
  surfaced as its own `feedback_by_option`-style explanation instead,
  since script confusion is a distinct, more instructive error than a
  fat-fingered typo.
- New content-compiler flag `case_sensitive: true | false` (per
  exercise, author override), added 2026-07-07 — a sibling of
  `orthography_strict`, not a replacement: `orthography_strict` only
  ever controls typo-edit-distance tolerance, never case. Default
  (flag absent, `false`) is the historical always-casefold comparison
  used everywhere before this flag existed. When `true`, grading
  compares without casefolding on every path (exact match, multi-
  answer, `matching_pairs`, `word_order`/`listen_order`, and the
  free-text typo-tolerance path), AND a mismatch that is *purely* a
  case difference (e.g. "sie" vs "Sie") is never forgiven as a
  distance-1 `almost` typo either — it grades `incorrect`, same
  "hard-block before typo-tolerance" treatment as a script-confusion
  substitution. Added for German, where the formal "Sie" (capital,
  "you" formal) vs. lowercase "sie" ("she"/"they") is a real
  grammatical distinction with no equivalent in nl/en/fa/prs content
  authored so far. Only applies to hand-authored `Exercise` rows
  (stored in the same `Exercise.feedback` JSON blob as
  `orthography_strict`/`feedback_by_option`) — Endless Practice's
  generated `PracticeItem`s have no per-template equivalent yet (no
  German Endless Practice content exists as of this writing).

`POST /lessons/{id}/start` and `POST /lessons/{id}/complete` just need to
return enough to update client state (e.g. `{ "started_at" }` /
`{ "completed_at", "xp_awarded", "accuracy" }`) — no strict shape mandated
beyond that.

**Progress/review** (settled as-implemented during integration — see note
below on how these got out of sync)

`GET /me/reviews?cursor=&limit=` — **always** returns the cursor-paginated
wrapper shape, not a flat array:
```json
{ "items": [ { "id":"...", "exercise_id":"...", "due_at":"...", "mastery":0.5, "exercise": { "id":"...", "type":"...", "prompt":{...} } } ], "next_cursor": "2026-01-01T00:00:00|abc123" }
```

`GET /me/progress`:
```json
{
  "lessons_started": 3, "lessons_completed": 1,
  "lesson_progress": [ { "lesson_id":"...", "started_at":"...", "completed_at":"...", "accuracy":0.8, "xp_earned":10 } ],
  "skill_progress": [ { "course_id":"...", "completed_lessons":1, "mastery":0.1 } ],
  "vocabulary_progress": [ { "content_item_id":"...", "mastery":0.5 } ],
  "grammar_progress": [ { "content_item_id":"...", "mastery":0.5 } ]
}
```

`GET /me/streak` → `{ "streak_days": 3, "last_activity_date": "2026-07-01", "streak_freezes_available": 0, "freeze_used_today": false, "active_today": false }`.
There is no "longest streak" tracked — only current `streak_days`.
`streak_freezes_available`/`freeze_used_today` are Phase E additions
(2026-07-05): one streak freeze is earned at every 7-day streak
milestone while none is currently banked, auto-consumed on exactly one
missed day instead of resetting the streak, both computed in the
user's own timezone (`User.timezone`, IANA string, UTC fallback).
`active_today` (added 2026-07-10, additive) is `last_activity_date ==
today`, computed server-side against that same user-timezone day
boundary — clients should use it (rather than re-deriving from
`last_activity_date` with the device clock, which can disagree with
the account timezone) to decide whether today's streak-preserving
activity has already happened; the HomePage streak-at-risk banner is
its consumer. The returned `streak_days` is the effective live streak:
it is zero when the last activity is too old in the account timezone,
allowing one missed day when a freeze is available. This read calculation
does not change the stored streak or consume a freeze.

`GET /me/xp` → `{ "total_xp": 120, "daily_goal": 20, "xp_today": 15 }`.
`daily_goal` is the authenticated user's configured target and defaults to
20 XP. `GET /me/daily-goal` returns `{ "daily_goal_xp": 20 }`.
`PUT /me/daily-goal` accepts `{ "daily_goal_xp": 10|20|30|50 }` and returns
the same shape. These values correspond to casual/regular/serious/intense.
Other values return the standard `422` error envelope.
`xp_today` (added 2026-07-10) is the XP earned within the user's own
local day (same `activity_day_bounds()` window streaks/quests use),
summed live from the persisted per-answer rows: `ExerciseAttempt`
(lesson answers) + `PracticeAttempt` (practice / Phase A review
sessions / checkpoints) + today's `QuestCompletion` rewards.
`LessonProgress.xp_earned` is deliberately excluded — it is a running
sum of the same `ExerciseAttempt` rows and would double-count. Known
gap: the legacy `POST /reviews/{id}/answer` flow bumps `total_xp`
without persisting a per-answer XP row, so its XP cannot be attributed
to a day; the frontend no longer uses that flow.

`GET /me/achievements` → `[ { "id":"...", "code":"...", "title":"...", "description":"...", "earned": true } ]`.

`GET /me/quests` (Phase E3, 2026-07-05) → `{ "quests": [ { "code":"clear_reviews", "title":"...", "description":"...", "xp_reward":10, "completed":false, "progress":0, "target":1 } ] }`. Three quests are deterministically selected from the quest pool per user and local date. Quest XP rewards do not count as learning activity or extend a streak; reading quests never awards XP unless the underlying learning action is already complete.
Server-authoritative daily nudge quests, computed live against the
user's own local day (same timezone logic as streaks) rather than
tracked via per-action hooks into every answer endpoint — quest
completion is DERIVED from existing state each time this endpoint is
called (e.g. "clear your due reviews" checks `GET /me/reviews/due`'s
own due-count logic, "complete a lesson" checks today's `LessonProgress
.completed_at`, "5 correct in practice" checks today's `PracticeAttempt
.correct` count), not incrementally updated by modifying lesson/review/
practice endpoints. XP is awarded exactly once per quest per day the
first time it's observed complete (a small idempotent completion
record, not re-awarded on repeat `GET` calls). Deliberately light — a
nudge system, not a game economy — no UI/endpoint for "claiming," XP
just lands automatically the moment the quest is satisfied.

Note: this section originally only said "flat array is fine" for
`/me/reviews` and didn't specify `/me/progress`, `/me/streak`, `/me/xp`,
`/me/achievements` shapes at all — a real gap in the original contract.
Backend and frontend were built in parallel against that gap and made
different reasonable choices; the shapes above are the backend's
as-built, tested behavior, confirmed working during integration testing on
the Debian server, and the frontend was updated to match them.

`POST /reviews/{id}/answer` — same response shape as the exercise-answer
endpoint, plus `next_due_at`.

### Endless Practice feed

`POST /practice/{course_id}/batch` returns freshly generated
`PracticeItem`-backed feed items for the current learner:

```json
{ "size": 10, "mode": "mixed" }
```

`size` is optional and must be between 1 and 20. `mode` is optional and
defaults to `"mixed"` for the existing adaptive template mix. Added
2026-07-13: `mode: "speaking"` is an additive pronunciation-practice filter
that returns only generated `speak_repeat` / `speak_response` items, using
course material from lessons the learner has completed. The speaking
generator prefers the learner's tracked SRS lexemes weakest/due-first when
available, falls back to completed-lesson lexemes otherwise, and never uses
lexemes from uncompleted lessons. It is fully deterministic through the same
practice batch seeding path and performs zero runtime LLM calls.

Added 2026-07-13: `mode: "conversation"` is an additive branching-dialogue
practice filter that returns only generated `conversation` items, using
course material from lessons the learner has completed. A conversation item
is generated from already-taught dialogue/phrase/lexeme material and performs
zero runtime LLM calls. It is deterministic through the same practice batch
seeding path and never uses lexemes from uncompleted lessons.

Response shape is unchanged:

```json
{
  "locked": false,
  "items": [
    { "id": "uuid", "type": "speak_repeat", "prompt": {} }
  ]
}
```

Speaking feed items are answered through
`POST /practice/items/{item_id}/answer` with the transcript string in the
same `{ "response": "..." }` shape as lesson `speak_*` exercises.

Conversation feed item prompt shape:

```json
{
  "locked": false,
  "items": [
    {
      "id": "uuid",
      "type": "conversation",
      "prompt": {
        "start_node_id": "node_0",
        "current_node": {
          "id": "node_0",
          "app_turn": {
            "text": "Buenas tardes",
            "language_code": "es",
            "direction": "ltr"
          },
          "accepted_variants": ["Buenos días", "Buenas tardes"],
          "answer_language_code": "es",
          "terminal": false
        },
        "nodes": [
          {
            "id": "node_0",
            "app_turn": {
              "text": "Buenas tardes",
              "language_code": "es",
              "direction": "ltr"
            },
            "accepted_variants": ["Buenos días", "Buenas tardes"],
            "branches": [
              { "variant": "Buenos días", "next_node_id": "node_1" },
              { "variant": "Buenas tardes", "next_node_id": "node_2" }
            ],
            "fallback_node_id": "node_retry",
            "answer_language_code": "es",
            "terminal": false
          }
        ]
      }
    }
  ]
}
```

The client renders `current_node.app_turn` as the app's spoken/dialogue turn
(using existing TTS where available) and accepts the learner's typed answer
or speech transcript. To submit a conversation reply, call
`POST /practice/items/{item_id}/answer` with:

```json
{
  "response": {
    "node_id": "node_0",
    "response": "Buenas tardes"
  }
}
```

The answer response keeps the existing fields and, for conversation items
only, adds `next_node` when the conversation should continue:

```json
{
  "correct": true,
  "result": "correct",
  "correct_response": ["Buenos días", "Buenas tardes"],
  "xp_awarded": 0,
  "next_node": {
    "id": "node_2",
    "app_turn": {
      "text": "Buenas noches",
      "language_code": "es",
      "direction": "ltr"
    },
    "accepted_variants": ["Buenas noches"],
    "answer_language_code": "es",
    "terminal": false
  }
}
```

If no accepted variant matches, the server returns `result: "incorrect"` and
selects the node's `fallback_node_id`, so an unrecognized reply never
dead-ends. `xp_awarded` is `0` until a terminal conversation node is reached;
terminal replies are recorded as the completed practice attempt.

### Lexeme review flow

`GET /me/reviews/due` returns the current user's unsuspended lexeme reviews
whose `due_at` is at or before the server's current time:

```json
{
  "due_count": 3,
  "by_course": [
    { "course_id": "uuid", "due_count": 3 }
  ]
}
```

`POST /reviews/session` request:

```json
{ "course_id": "uuid", "size": 10 }
```

`size` must be between 1 and 20. The response contains freshly generated
practice-engine items and intentionally has no `locked` field:

```json
{
  "items": [
    { "id": "uuid", "type": "multiple_choice", "prompt": {} }
  ]
}
```

Items are answered through the shared
`POST /practice/items/{item_id}/answer` endpoint. Its response is identical
to `PracticeAnswerOut`:

```json
{
  "correct": true,
  "correct_response": "server-held answer",
  "xp_awarded": 5
}
```

A review item remains single-answer: submitting the same item twice returns
409. After answering it, `POST /reviews/items/{item_id}/retry` creates one
fresh item for the same lexeme and review session:

```json
{
  "items": [
    { "id": "new-uuid", "type": "fill_in_blank", "prompt": {} }
  ]
}
```

The retry endpoint returns 404 for a foreign or non-review item, 409 if the
original item has not been answered, and 409 if no valid reviewed template
can generate the retry. A retry is cosmetic for SRS scheduling: only the
first answer for a lexeme in a review session advances its interval.

The legacy `GET /me/reviews` and `POST /reviews/{id}/answer` exercise-level
endpoints are deprecated in favor of the lexeme review flow above. They
remain available only for pre-existing `ReviewItem` rows; lesson answers no
longer create new legacy review rows.

### Lexeme browser and mistakes hub, 2026-07-10

`GET /me/lexemes` is the vocabulary browser data source. Auth required.
Query params:

```
course_id=uuid
sort=due_soonest|mastery_asc|mastery_desc|alphabetical|recently_introduced
part_of_speech=noun
search=substring
limit=50
offset=0
```

`course_id` is a query parameter (not a path parameter) to match the
course-scoped `/me/*` style used by review endpoints. It is required in
practice; an unknown course returns `404 course_not_found`. `limit` is 1-200
and `offset` is >=0. Only lexemes with a `UserLexemeSRS` row for the current
user are returned — this is the learner's encountered vocabulary, not the full
course-wide lexeme pool.

Response:

```json
{
  "items": [
    {
      "token": "uno",
      "english_gloss": "one",
      "part_of_speech": "noun",
      "mastery": 0.42,
      "interval_days": 3,
      "repetitions": 2,
      "due_at": "2026-07-10T12:00:00Z",
      "introduced_at": "2026-07-01T12:00:00Z",
      "suspended": false,
      "last_reviewed_at": "2026-07-09T12:00:00Z"
    }
  ],
  "total_count": 1,
  "limit": 50,
  "offset": 0
}
```

`GET /me/lexemes/summary?course_id=uuid` powers the small vocabulary-page
stats header. Auth required. Unknown course returns `404 course_not_found`.

```json
{
  "total_tracked": 42,
  "mastery_bands": { "new": 8, "learning": 22, "strong": 12 },
  "due_today": 5,
  "suspended": 1
}
```

Mastery bands are rough UI buckets over the existing 0.0-1.0 `mastery` float:
`new` < 0.33, `learning` 0.33-0.749..., `strong` >= 0.75. `due_today` counts
unsuspended tracked lexemes due at or before the end of the learner's current
local day (`User.timezone`, UTC fallback).

`GET /me/mistakes?course_id=uuid&limit=50&offset=0` is the mistakes hub data
source. Auth required. Unknown course returns `404 course_not_found`.

Important data-source caveat: real per-lexeme attempt history currently exists
only for `PracticeItem`-backed flows (`/practice/{course_id}/batch`,
`/reviews/session`, and unit checkpoints) because `PracticeItem.target_lexeme_id`
identifies the tested word. Legacy hand-authored `ExerciseAttempt` lesson rows
record correct/incorrect answers but do not identify a lexeme, so they cannot
honestly be rolled up into a per-word mistakes hub without a new persistence
model. This endpoint therefore aggregates wrong attempts from the last 30 days
of lexeme-linked `PracticeAttempt` rows and sorts worst-first.

```json
{
  "items": [
    {
      "token": "uno",
      "english_gloss": "one",
      "part_of_speech": "noun",
      "mastery": 0.2,
      "repetitions": 3,
      "recent_accuracy": 0.33,
      "wrong_attempt_count": 2,
      "total_attempt_count": 3
    }
  ],
  "total_count": 1,
  "limit": 50,
  "offset": 0
}
```

### Vocabulary export, 2026-07-10

`GET /courses/{course_id}/lexemes/export?format=csv|anki` downloads the
current user's tracked vocabulary for that course (same
`UserLexemeSRS`-backed population as `GET /me/lexemes` — encountered words
only, never the full course-wide lexeme pool) as a file for external tools.
Auth required. Unknown course returns `404 course_not_found`. `format`
defaults to `csv`; any other value is a 422. Rows are sorted alphabetically
by token. This is a file-download endpoint, not JSON — no pagination, all
tracked rows in one response, `Content-Disposition: attachment` with a
`vocabulary-{course_id}.{csv|txt}` filename.

`format=csv` (`Content-Type: text/csv; charset=utf-8`) is a spreadsheet
export with a header row:

```csv
token,gloss,part_of_speech,mastery,due_at
uno,one,noun,0.42,2026-07-10T12:00:00+00:00
```

`format=anki` (`Content-Type: text/tab-separated-values; charset=utf-8`,
`.txt` filename since that's what Anki's importer expects) is the standard
2-column Anki text-import shape — front (token) TAB back (gloss), one note
per line, no header row. Two `#`-prefixed Anki file-header directives
(`#separator:tab`, `#html:false`) lead the file; Anki ≥2.1.55 honors them
and older versions ignore `#` lines as comments, so the file imports
cleanly either way.

### Content issue reporting for PracticeItem-backed content, 2026-07-07

`POST /exercises/{exercise_id}/report` only ever recognized real `Exercise`
rows (compiled lesson content) — but review sessions, unit checkpoints, and
the Endless Practice feed are all backed by `PracticeItem`, a separate table
with no relationship to `Exercise`. `ReviewPage.tsx` was passing a
`PracticeItem.id` into that endpoint and 404ing on every report (reproduced
live); the Endless Practice feed had no report button wired in at all.

New endpoint, same request/response shape as the exercise one:

```
POST /practice/items/{item_id}/report
{ "category": "wrong_answer_key", "description": "...", "learner_response": ... }
→ 201 { "id": "uuid", "status": "open" }
```

404s (`practice_item_not_found`) for a foreign or nonexistent item, same
ownership check as `POST /practice/items/{item_id}/answer`. Use this for any
id that came from `/reviews/session`, `/practice/{course_id}/batch`, or
`/units/{unit_id}/checkpoint` — never `/exercises/{id}/report`, which will
404 for all of those.

`ContentIssueReport.exercise_id` is now nullable; a new nullable
`practice_item_id` FK was added (mirrors the existing nullable
`content_key_id` secondary FK on this same table). Exactly one of
`exercise_id`/`practice_item_id` is ever set (DB check constraint,
migration 0014) — `GET /admin/content/issues` and `PATCH
/admin/content/issues/{id}` are otherwise unchanged, `ContentIssueOut` just
gained `practice_item_id` alongside the now-optional `exercise_id`. `GET
/admin/content/coverage`'s per-course `open_issue_count` is unchanged and
intentionally still counts only `Exercise`-linked reports (it's derived via
the `Course → Unit → Lesson → Exercise` join, which has no equivalent path
for PracticeItem) — PracticeItem-backed reports don't appear in that
specific rollup yet, a known scope gap, not a regression.

### General app/page feedback (not content-issue-specific), 2026-07-09

Every existing report path (`POST /exercises/{id}/report`, `POST
/practice/items/{id}/report`) requires a real `Exercise`/`PracticeItem` id —
there was no way to report a problem with the app itself (a broken button, a
confusing screen, a login failure) or leave general feedback from a page
that isn't an exercise. Also: this app is meant to be usable in at least
three deployment shapes (Ramin's home server, a locally-run clone someone
starts via a shortcut, and eventually a hosted public domain) — a report
mechanism that only writes to whatever backend instance happens to be
running locally would silently lose all feedback from the "everyone runs
their own local copy" shape, since nobody but that one person would ever
see it. This endpoint is deliberately unauthenticated (feedback about a
broken login page has to work without being logged in) and the frontend is
expected to point it at one fixed, centrally-reachable backend regardless of
which backend instance is serving the rest of the app (see
`VITE_FEEDBACK_API_URL` below) — that's a deployment/config concern, not
something this endpoint itself needs to know about.

```
POST /feedback
{ "page_path": "/lessons/abc123", "category": "app_bug", "description": "The next button does nothing", "client_context": {...} }
→ 201 { "id": "uuid", "status": "open" }
```

- No auth required. If a valid bearer token is present, `reporter_user_id`
  is set from it; otherwise the report is anonymous (`reporter_user_id`
  null). `ContentIssueReport.reporter_user_id` is now nullable for this
  reason — every existing exercise/practice-item report path is unaffected
  (a logged-in user is required to reach a lesson/practice item at all, so
  those two paths always populate it in practice).
- `category` gains two new values on top of the existing set
  (`wrong_answer_key`/`mistranslation`/`untaught_vocabulary`/`audio_issue`/
  `unclear_instruction`/`other`): `app_bug` (something is broken) and
  `general_feedback` (a suggestion/comment, nothing broken). Plain `String`
  column, not a DB enum — Pydantic validates the allowed set, same as
  today.
- New nullable `page_path: str` column (the frontend route path at
  submission time, e.g. `/lessons/abc123` or `/home` — not a full URL, no
  query string/PII). `exercise_id`/`practice_item_id`/`page_path` are
  mutually exclusive-ish in practice (a page-level report has neither id
  set) but the DB check constraint only enforces "at most one of
  exercise_id/practice_item_id" (relaxed from "exactly one" — migration
  needed), it does not require `page_path` specifically; that's an
  application-level convention, not a DB-level one.
- `GET /admin/content/issues` and `PATCH /admin/content/issues/{id}` are
  unchanged in shape — `ContentIssueOut` gains `page_path` alongside the
  existing nullable `exercise_id`/`practice_item_id`. A page-level report
  (both ids null) is a legitimate row, not an error case.
- `GET /admin/content/coverage`'s per-course `open_issue_count` is
  unaffected (page-level reports have no course to roll up into, same
  known-scope-gap precedent as the PracticeItem entry above).

**Feedback attachments (screenshots), added 2026-07-12 (spec-first —
implementation follows):**

```
POST /feedback/attachments        (multipart/form-data, field "file")
→ 201 { "attachment_key": "fb_<random>", "expires_in_seconds": 3600 }
```

- No auth (same rationale as `/feedback` itself), but hard abuse limits
  enforced server-side: image content types only (png/jpeg/webp — sniffed
  from magic bytes, never trusted from the header), max 5 MB, its own
  rate limit at least as strict as `/feedback`'s. Uploads land as opaque
  keys in a private directory (`backend/feedback_uploads/`, gitignored,
  NEVER served statically); an attachment is an orphan until a
  `POST /feedback` references it, and orphans older than ~1 hour are
  eligible for cleanup (opportunistic sweep on new uploads — no cron
  infrastructure exists, same constraint as E4).
- `POST /feedback` gains optional `"attachment_keys": ["fb_..."]` (max 3);
  unknown/expired keys are silently dropped (report still succeeds —
  feedback must never be lost over a bad attachment). New
  `FeedbackAttachment` table (id/key/report_id nullable until claimed/
  content_type/byte_size/created_at) — additive, guarded migration.
- Retrieval is ADMIN-ONLY: `GET /admin/content/issues/{id}/attachments/
  {attachment_id}` streams the image with auth; `ContentIssueOut` gains
  `attachments: [{id, content_type, byte_size}]`. Attachment bytes are
  never exposed on any unauthenticated route (an unauthenticated upload
  must not become an unauthenticated public file host).
- Frontend: the feedback widget gains an optional image picker (`<input
  type="file" accept="image/*">` — on phones this offers camera/photo
  library natively); client-side downscale to ≤1600px longest edge before
  upload to keep mobile uploads fast.

Frontend: `VITE_FEEDBACK_API_URL` is a new, separate env var (falls back to
the existing `VITE_API_BASE_URL` when unset, which is correct for the
"single shared backend" deployment shapes — home server or hosted domain).
It only needs to be set to something different in the "many independent
local installs" shape, and only once Ramin has a real, stable,
internet-reachable URL for one canonical collector backend (e.g. a tunnel
or DNS record pointed at his home server, or the eventual hosted domain) —
until then, local installs' feedback stays local to that install, which is
a known limitation of that deployment shape, not a bug in this mechanism.

### Issue-triage enrichment on `GET /admin/content/issues`, 2026-07-10

An admin triaging a report used to see only a raw exercise/practice-item
UUID — understanding what the report was even about meant manually digging
through YAML/psql. `ContentIssueOut` (both the list endpoint and the PATCH
response share this schema) gains four additive, nullable fields, computed
per-request by `GET /admin/content/issues` (never stored on the report row):

- `exercise_prompt` (object|null): the referenced `Exercise.prompt` payload
  (same shape the learner saw — `text_blocks`, `options`, `word_bank`, …).
  Only set on exercise-backed reports whose exercise still exists.
- `exercise_correct_response` (any|null): that exercise's server-held
  answer key, arbitrary shape by exercise type (same caveats as
  `correct_response` everywhere else in this contract).
- `practice_item_prompt` (object|null): for PracticeItem-backed reports,
  the generated item's stored `prompt` payload (its `correct_response` is
  intentionally not exposed here — generated items are ephemeral
  per-user artifacts; the prompt is what identifies the content problem).
- `open_report_count` (int|null): how many currently-OPEN reports point at
  the same `exercise_id` (duplicate spotting). Counted against the whole
  table, not just the returned page. Null on practice-item/page reports.

All four are null on `PATCH /admin/content/issues/{id}` responses (the
PATCH returns the bare row without re-running the enrichment joins) and on
page-level feedback rows. The existing `learner_response` field (the
learner's actual submitted wrong answer, stored at report time) was always
returned by this endpoint — the frontend `ContentIssue` type/rendering now
finally surfaces it alongside the correct answer.

### Unit checkpoint (test-out), Phase F, 2026-07-05

Not the rejected placement-quiz enrollment system — assembled entirely from
the unit's own existing reviewed exercises/practice templates (practice-engine
generation across all ladder tiers), graded by the existing `grade()`, no new
content authoring required.

`POST /units/{unit_id}/checkpoint` generates 12-15 mixed items and returns
them the same shape as `POST /reviews/session`'s `items` array (server-held
answers, single-answer-per-item via the shared
`POST /practice/items/{item_id}/answer` endpoint):

```json
{ "items": [ { "id": "uuid", "type": "multiple_choice", "prompt": {} } ] }
```

**Strict grading only for checkpoint items — no typo tolerance ("almost")
regardless of the answer's script**, since this is a pass/fail assessment,
not a learning exercise; `PracticeItem`s generated for a checkpoint carry
enough context (a `source` value distinct from `"practice"`/`"review"`, e.g.
`"checkpoint"`) for the answer endpoint to force `orthography_strict`
behavior unconditionally.

`GET /units/{unit_id}/checkpoint/result` reports the current session's
state — call it any time after starting a session, not just once every item
is answered:

```json
{
  "status": "in_progress",
  "answered_items": 9,
  "total_items": 15,
  "passed": null,
  "score": null,
  "weak_outcomes": [],
  "checkpoint_passed": false
}
```

Once `answered_items == total_items`, the same call scores the session
(idempotently — repeat calls re-return the persisted result rather than
re-scoring) and `status` becomes `"complete"`:

```json
{
  "status": "complete",
  "answered_items": 15,
  "total_items": 15,
  "passed": true,
  "score": 0.87,
  "weak_outcomes": ["gloss of a missed lexeme", "..."],
  "checkpoint_passed": true
}
```

`checkpoint_passed` reflects the unit's ALL-TIME pass state for this user
(true forever once any attempt passes, independent of the specific session
just scored) and is also returned per-unit on `GET /courses/{course_id}
/units` as an additive `checkpoint_passed: bool` field — this is what
frontend uses to turn `LevelCheckPage`'s existing honor-system "Recommended
for you" badge into a demonstrated skip via a "Test out of Unit N" button.

Passing at ≥80%: lexemes covered by the checkpoint's items enter SRS as
consolidated if not already tracked for this user (mastery floor 0.5,
`due_at` = scoring time + 3 days — skips the normal fresh-introduction
ladder since a passed checkpoint already demonstrates mastery). Any lexeme
the user already had an SRS row for is left completely untouched, never
downgraded or reset.

Failing is cheap and kind, not punitive: `weak_outcomes` lists the English
glosses of incorrectly-answered lexemes (for the frontend to suggest the
unit's own lessons), and a 1-hour server-side retake delay is enforced —
`POST /units/{unit_id}/checkpoint` returns `429 checkpoint_retake_delayed`
with a `retry_after_seconds` field (see the error-shape section above) when
called again too soon after the same user's most recent attempt for that
unit, race-safe under concurrent requests.

### Placement test (course-level), 2026-08-05

CEO-approved 2026-08-05 (full design in `docs/PLACEMENT_TEST_SPEC.md`). Distinct
from the placement-quiz *enrollment* system rejected in favor of the unit
checkpoint above: this is recognition-only, **assembled from the course's own
existing reviewed exercises** (no new content authoring), graded by the existing
`grade()`, and in the MVP writes **nothing** — no `ExerciseAttempt`,
`LessonProgress`, XP, streak, or SRS rows. It only *recommends* a starting unit;
the recommendation is persisted client-side (`localStorage`, same mechanism as
`LevelCheckPage`'s existing per-course level preference), so the MVP needs **zero
migrations**. Server-side persistence + progress/SRS seeding is a deferred growth
step (one small `placement_results` table) and is NOT part of this contract yet.

Probes are restricted to `multiple_choice` and `matching_pairs` (self-contained,
choice-graded, no audio, no free-text) so grading is script-agnostic and RTL/
`prs`-no-TTS-safe. Items are laddered by the CEFR level of their owning unit
(parsed from `Unit.content_key`, never `Course.level`), in blocks of 4 per level
A1→A2→B1→B2, deterministically selected (stable order) so the set is reproducible.

All three endpoints require auth (`current_user`) and are rate-limited under the
existing per-account answer limit (`ANSWER_RATE_LIMIT`, 120/60s → `429
answer_rate_limited` with `retry_after_seconds`, same shape as the other answer
endpoints).

`GET /courses/{course_id}/placement` returns the laddered probe set with answers
withheld (same `{id, type, prompt}` item shape as lessons/checkpoints, plus a
per-item `level`):

```json
{
  "course_id": "uuid",
  "levels": ["A1", "A2", "B1", "B2"],
  "block_size": 4,
  "pass_threshold": 3,
  "items": [ { "id": "uuid", "level": "A1", "type": "multiple_choice", "order": 0, "prompt": {} } ]
}
```

Returns `404 course_not_found` for an unknown course, and `409
placement_unavailable` when the course cannot fill even one A1 block (< 4 usable
probes).

`POST /courses/{course_id}/placement/answer` grades ONE item live (for immediate
feedback + client-side adaptive early-exit) with **no side effects** — a pure
`grade()` call, no rows written:

```json
// request
{ "exercise_id": "uuid", "response": "<AnswerResponse, same union as POST /exercises/{id}/answer>" }
// response
{ "correct": true, "result": "correct", "correct_response": "<shown answer>" }
```

Returns `400 exercise_not_in_placement` if the `exercise_id` does not belong to
`course_id`, and `404 course_not_found` for an unknown course.

`POST /courses/{course_id}/placement/result` is the authoritative recommendation:
the server **re-grades** every submitted answer (so pass thresholds live only
server-side and cannot be gamed), computes per-level accuracy, maps it to a
recommended CEFR level, and resolves the first reading/writing unit of that level.
Also **no side effects** in the MVP:

```json
// request
{ "answers": [ { "exercise_id": "uuid", "response": "<AnswerResponse>" } ] }
// response
{
  "recommended_level": "A2",
  "recommended_unit_id": "uuid",
  "recommended_unit_content_key": "nl.a2.unit05.slug",
  "recommended_unit_title": "…",
  "per_level": { "A1": { "correct": 4, "total": 4 }, "A2": { "correct": 2, "total": 4 } }
}
```

Recommendation mapping: fail A1 → course start; pass A1 / fail A2 → first A2 unit;
pass A1+A2 / fail B1 → first B1 unit; pass all present → first unit of the highest
level present. A pass of a level's block is `≥ pass_threshold` correct. An empty
or short `answers` array recommends the course start rather than erroring; `404
course_not_found` for an unknown course.

### Web push notifications (Phase E4), 2026-07-10

Standard Web Push with VAPID — no third-party push provider, no new
frontend dependency (the browser Push API + `pywebpush` server-side).
Server config is `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` (plus optional
`VAPID_SUBJECT`, a `mailto:` contact URI) env vars, following the same
unset-by-default/graceful-degradation convention as the TTS/STT
credentials: when either key is empty, push is "not configured" and the
whole feature no-ops honestly (endpoints below return `configured: false`
/ `503 push_not_configured`; the frontend hides all push UI) — never a
crash, never a broken button.

`GET /push/vapid-public-key` — unauthenticated capability probe. The
frontend calls this before rendering ANY push UI; `configured: false`
means hide the feature entirely:

```json
{ "public_key": "BPa1…base64url", "configured": true }
```

(`public_key` is `null` whenever `configured` is `false`. The key is the
raw base64url-encoded VAPID public key; the frontend converts it to a
`Uint8Array` for `pushManager.subscribe()`'s `applicationServerKey`.)

`POST /push/subscribe` (auth) — the body is the browser
`PushSubscription`'s own fields, exactly as `subscription.toJSON()`
produces them:

```json
{ "endpoint": "https://fcm.googleapis.com/…", "keys": { "p256dh": "…", "auth": "…" } }
→ { "subscribed": true }
```

`endpoint` is the uniqueness key (one row per browser profile + service
worker registration). Re-subscribing an endpoint that already exists
re-binds it to the calling user and refreshes its keys — the correct
behavior for a shared device where a second account logs in. Returns
`503 push_not_configured` when VAPID keys are unset.

`POST /push/unsubscribe` (auth) — `{ "endpoint": "…" }` →
`{ "subscribed": false }`. Idempotent (an unknown or other-user endpoint
is not an error) and deliberately NOT gated on `push_configured`, so a
client can always clean up a local subscription even after the server's
keys were rotated away.

Admin triggers remain available for manual use. An optional in-process
scheduler also runs the daily reminder triggers every 15 minutes when
`ENABLE_PUSH_SCHEDULER=true`; it is disabled by default. Sends are guarded
per user, trigger, and local date, and users without an active push
subscription receive nothing.

`POST /admin/push/notify-due-reviews` (admin auth) — sends a "Reviews are
waiting" notification to every user with at least one due, non-suspended
SRS lexeme:

```json
→ { "notified_users": 3, "notifications_sent": 4 }
```

`POST /admin/push/notify-streaks-at-risk` (admin auth) — sends a streak
warning to users with a live streak who have not been active in their own
local day. Both trigger types are deduplicated per user, trigger, and local
date, including when multiple scheduler workers are running.

**Push payload contract (server → service worker)** — the data of every
push message is JSON:

```json
{ "title": "Reviews are waiting", "body": "You have words due for review — keep your streak going.", "url": "/review" }
```

The web frontend's service worker (`frontend/public/sw.js`) shows a
notification with `title`/`body` and, on notification click,
focuses/opens the app at `url` (an app-relative path, not a full URL).
Unknown extra fields must be ignored by the SW, never treated as an
error.

Dead subscriptions (the push service answers a send with 404/410) are
pruned server-side automatically on the next send attempt; other send
failures are logged and skipped, never fatal to the whole batch. The
frontend does not need to re-assert its subscription on every load,
though re-POSTing `/push/subscribe` with the same endpoint is harmless.

Frontend behavior (web): push UI appears in exactly two places — a
dismissible "enable notifications" card on HomePage (shown only when the
server reports `configured: true`, the browser actually supports Web Push
(`serviceWorker` + `PushManager` + `Notification` all present — iOS
Safari outside an installed PWA does not), permission is not already
denied, no subscription exists yet, and the user hasn't dismissed it;
dismissal persists per-device in localStorage) and an enable/disable
control in ProfilePage's settings area. Unsupported browsers see neither
surface — hidden, not disabled.

## Auth mechanism

JWT bearer token, returned from `/auth/login` and `/auth/register` as
`access_token`. Clients send it as `Authorization: Bearer <token>`.
`refresh_token` is an opaque long-lived credential used only with
`POST /auth/refresh` or `POST /auth/logout`; clients must treat it as more
sensitive than the access token and never send it as a bearer token.

## Error shape (consistent across all endpoints)

```json
{ "error": { "code": "string_machine_code", "message": "human readable" } }
```

Some errors carry additional fields alongside `code`/`message` (e.g.
`checkpoint_retake_delayed`'s `retry_after_seconds` — Phase F, 2026-07-05):

```json
{ "error": { "code": "checkpoint_retake_delayed", "message": "...", "retry_after_seconds": 3592 } }
```

**Rate limiting (2026-07-06 security hardening item)**: `POST /auth/login`
(brute-force protection, 10 requests/60s per client IP — counts failed
attempts too), `POST /auth/register` (abuse prevention, 5 requests/hour per
client IP), and the three answer-submission endpoints (`POST /exercises/{id}
/answer`, `POST /reviews/{id}/answer`, `POST /practice/items/{id}/answer` —
120 requests/60s per account) all return `429` with the same additional-field
shape when exceeded: `login_rate_limited`, `register_rate_limited`, and
`answer_rate_limited` respectively, each with `retry_after_seconds`.
**Added 2026-07-10**: `POST /auth/refresh` and `POST /auth/logout` (30
requests/60s per client IP, shared between the two — both are
unauthenticated, refresh-token-bearing endpoints, so this bounds stolen-token
replay probing and valid-token guessing; deliberately more generous than
login's 10/60s because legitimate clients refresh automatically on
access-token expiry and several devices can share one NAT'd IP) return the
same `429` shape with code `refresh_rate_limited`. Invalid-token probes count
against the limit exactly like login's failed attempts do. In-memory
sliding-window limiter (`app/core/rate_limit.py`), not Redis-backed — correct
for this deployment's single-process, no-Redis stack; would need to move to a
shared store if ever scaled to multiple worker processes.

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

## Course levels

`level` on `CourseOut`/`CourseDetail` is a validated CEFR value:
`A1`, `A2`, `B1`, `B2`, `C1`, `C2` — not a free string. `GET
/courses?source=&target=` can now return **multiple courses for the same
pair at different levels**; frontend sorts them by level (A1 first) and
shows each with a plain-language one-line description (not just the CEFR
code, which most learners won't recognize) plus a "not sure? start at the
earliest level" hint. No separate placement-test/enrollment mechanism for
now — decided against it (see project discussion): a real placement quiz
needs a calibrated question bank and interacts messily with existing
per-course progress/XP and the speaking-unit unlock gate (which is scoped
per-course). Revisit only if real usage shows learners want it. Course
uniqueness is still `(source_language, target_language, title)` — distinct
levels naturally get distinct titles, no schema constraint change needed.

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

## Text-to-speech

**Superseded 2026-07-04: ElevenLabs was replaced with Google Cloud TTS**
(ElevenLabs never supported fa/prs at all; Google Cloud TTS turned out to
have zero Persian/Dari voices either, so the fallback behavior below was
unchanged at the time, only the primary provider changed). Phase D of the
current build program (see `docs/SONNET_BUILD_PROMPT_UPGRADES.md`) adds a
third tier — recorded human audio for fa/prs — ahead of both.

**Added 2026-07-06: Azure Cognitive Services Speech as a second cloud TTS
provider, specifically to close Google's Farsi gap.** Google Cloud TTS
has zero Persian/Dari voices at all (confirmed against Google's own
supported-voices list); Azure has real, licensed neural voices for Farsi
(`fa-IR-DilaraNeural` female — the default used here — and
`fa-IR-FaridNeural` male), confirmed against Azure's own voice gallery.
Dari (`prs`) still has no voice on Azure either, so `prs` is unaffected
and still falls all the way through to the browser fallback. `/tts`'s
request/response shape is unchanged — the frontend never needs to know
or care which provider actually generated a given `audio/mpeg` response.

`POST /tts` (auth required — this hits a metered paid API). Request:
```json
{ "text": "سلام", "language_code": "fa", "speaking_rate": 0.9 }
```
`speaking_rate` (added 2026-07-07, optional, default `1.0` = normal
native speed): a multiplier passed straight through to whichever
provider handles `language_code`, validated `0.25`–`2.0` server-side
(422 `validation_error` outside that range) — matches
`google-cloud-texttospeech`'s own `AudioConfig.speaking_rate` bound.
Google's field is used as-is; Azure has no equivalent request field, so
`synthesize_azure()` wraps the SSML in `<prosody rate="...">` (e.g.
`0.9` → `"-10%"`) to get the same effect. **This is a per-request
parameter only — nothing is persisted server-side.** The frontend derives
it from a per-device, per-language `localStorage` preference
(`frontend/src/lib/ttsSpeedPreferences.ts`, same shape/precedent as the
existing per-language voice preference in
`frontend/src/lib/voicePreferences.ts` and the STT mic/keyboard toggle in
`frontend/src/lib/answerInputMode.ts`) exposed via a Settings UI
(`SpeechSpeedSettings.tsx`, next to `VoiceSettings` on `ProfilePage`),
restricted to a `0.75`–`1.25` slider range there (too slow feels
unnatural, too fast defeats comprehension for a language learner) —
**not a backend user-account field**, since `/tts` never caches
synthesized audio across users/requests (confirmed: every call hits the
provider fresh), so there's no shared-cache-correctness reason to push
this server-side, and per-device is the right shape anyway (same
reasoning as the voice preference: what sounds right depends on the
learner, not the account).

Response is one of two things, and the frontend must branch on
`Content-Type`:
- `audio/mpeg` — raw MP3 bytes, generated via Google Cloud TTS (most
  languages) or Azure Cognitive Services Speech (`fa` only), already at
  the requested `speaking_rate`. Play directly.
- `application/json` — `{ "use_browser_tts": true, "reason": "unsupported_language" | "quota_exceeded" | "provider_error" }`.
  Frontend must fall back to the browser's built-in `speechSynthesis` API
  with this `language_code` in this case — never treat this as a hard
  error. If the browser itself has no voice for that language either
  (confirmed real gap for fa/prs on most devices), the frontend shows an
  honest `speak.no_voice_available` message instead of a silently-dead
  button — never fail silently. The browser-TTS path applies the same
  per-language rate preference client-side via
  `SpeechSynthesisUtterance.rate` (no request field involved at all).

**Recorded human audio (`GET /media/{key}`, Phase D3) is a flat,
fixed-speed MP3 file — the speed preference can't be threaded through
that route at all (no synthesis step to parameterize).** The frontend
instead applies the SAME per-language rate to recorded playback
client-side via `HTMLMediaElement.playbackRate` on the `<audio>` element
(`frontend/src/api/tts.ts`'s `playRecordedAsset()`) — a real browser
feature (not a hack) that resamples playback speed with pitch
preservation on by default in every evergreen browser, so recorded
clips DO respect the learner's speed preference in practice, just via a
different mechanism (client-side resampling) than the two TTS tiers
(server-side synthesis parameter / `speechSynthesis.rate`). Document
this distinction if it's ever revisited — it's not a limitation in
practice, but it IS a different code path than the other two tiers and
could silently regress independently.

Backend owns:
- Google Cloud TTS integration (`GOOGLE_CLOUD_TTS_CREDENTIALS_JSON` env var
  — raw service-account JSON content, not a file path — `pwdlib`-style
  service-account auth, `ssml_gender=NEUTRAL`, no explicit voice `name`).
- Azure Cognitive Services Speech integration (`AZURE_SPEECH_KEY` +
  `AZURE_SPEECH_REGION` env vars — a subscription key and its resource
  region, e.g. `eastus`), via the plain REST API (`app/services/tts.py`'s
  `synthesize_azure()`, no SDK dependency — an access token is exchanged
  from the subscription key, then SSML is POSTed to the region's
  `tts.speech.microsoft.com/cognitiveservices/v1` endpoint requesting
  `fa-IR-DilaraNeural`). Same graceful-degradation convention as Google:
  an unset/empty key or region raises, which the route catches and turns
  into the `provider_error` browser-fallback JSON rather than a 500.
- `tts_service.GOOGLE_TTS_SUPPORTED_LANGUAGES` (`{en,nl,fr,de,it,es,ru,zh}`)
  and `tts_service.AZURE_TTS_SUPPORTED_LANGUAGES` (`{fa}`) are each
  provider's own supported-language set; `tts_service.
  TTS_SUPPORTED_LANGUAGES` (their union) is the authoritative "does /tts
  have a real cloud voice for this language at all" set the route gates
  on. `tts_service.synthesize(text, language_code)` dispatches to
  whichever provider covers that language — Azure for `fa`, Google for
  everything else it covers. **Dari (`prs`) still has zero coverage from
  either provider** — `/tts` always returns the browser-fallback JSON for
  `prs`, never attempts a provider call. Note: the Endless Practice
  engine's `listen_select` generation gate (`app/practice/service.py`)
  deliberately still checks `GOOGLE_TTS_SUPPORTED_LANGUAGES` specifically,
  not the new union — whether to generate real-audio `listen_select`
  practice items for `fa` now that Azure covers it is a separate,
  not-yet-made product decision (see `docs/BUILD_LOG.md`'s Phase D4 note),
  left untouched by this change.
- Tracking cumulative characters synthesized per calendar month against
  `TTS_MONTHLY_CHAR_BUDGET` (config: `tts_monthly_char_budget`, default
  4,000,000) via a Postgres advisory-lock-guarded `TTSUsage` row,
  preemptively returning `reason: "quota_exceeded"` once a request would
  exceed the budget — never rely on the provider's own error response for
  this. This budget/usage tracking is shared across both providers (not
  split per-provider) — it's one meter on `/tts` as a whole.

Frontend owns: a reusable "speak this text" control (`SpeakButton`, e.g. a
speaker icon) attached to any `text_block`, calling `/tts` and playing the
result via `<audio>` or `speechSynthesis`, everywhere `text_block`s are
rendered (vocabulary, exercises, dialogues, reading passages) — not just
one exercise type. Also: a custom on-screen keyboard (`VirtualKeyboard.tsx`)
for non-Latin scripts on any typed-answer exercise, shown while the answer
field has focus (per `answer_language_code`), with a dismiss control to
fall back to the device's own keyboard.

## Speech-to-text (mic-based speaking exercises)

Added 2026-07-06: `speak_response` and `speak_repeat` gain real mic input.
Both compile with a genuine `correct_response`/`accepted_answers` (confirmed
against real content — e.g. `nl.a1.unit02.lesson01.exercise08.say_seven`
tests "zeven"; `fr.a1.unit01.lesson03.exercise07_read_liaison` tests "Vous
êtes. Un atelier." with an unaccented variant also accepted) — the spoken
answer is graded through the exact same `POST /exercises/{id}/answer` path
as every other free-text exercise (`FREE_TEXT_EXERCISE_TYPES` in
`app/review/grading.py`), just with the `response` string produced by
transcription instead of a keyboard.

**Primary path is 100% client-side and never touches the network with raw
audio**: the frontend records via `MediaRecorder`, transcribes in-browser
with a WASM Whisper model (Transformers.js, `Xenova/whisper-tiny`, run in a
Web Worker), and submits the transcript text as the answer exactly like a
typed response. The backend has no visibility into this path at all.

**Fallback path**: `POST /stt/transcribe` (auth required, multipart
form-data: `audio` file field + `language_code` form field). Only called
when the client reports client-side transcription isn't usable (no
WebAssembly, WASM model failed to load/download, or transcription itself
threw). Response:
```json
{ "transcript": "zeven" }
```

**Pronunciation-feedback extension (S1, 2026-07-13, contract-first — not
yet implemented):** `POST /stt/transcribe` accepts an optional
`detail=words` form field. When present, the response adds a `words` array
from faster-whisper's word-level output; without it the response is
byte-identical to today (fully backwards-compatible):
```json
{
  "transcript": "it will probably take two months",
  "words": [
    { "word": "it", "start": 0.12, "end": 0.24, "probability": 0.97 },
    { "word": "probably", "start": 0.61, "end": 1.02, "probability": 0.41 }
  ]
}
```
`probability` is the model's per-word confidence (0-1), the v1
pronunciation signal: the frontend maps it to per-word feedback
(e.g. <0.55 = "unclear — try again", highlighting the word). This is a
CLARITY heuristic, not phoneme-level scoring — no claim of accent
assessment. The client-side WASM path may synthesize an equivalent `words`
array locally when its model exposes token probabilities; the shape above
is the shared contract either way.
Errors are the standard error shape (`docs/CONTRACT.md`'s Error shape
section) with `code` one of `empty_audio` (413/422 — zero-byte upload),
`audio_too_large` (413 — over 5 MB, same cap as `/admin/media/upload`; a
few seconds of spoken audio is always far under this), or
`transcription_failed` (500 — the Whisper call itself raised).

Backend owns: `app/services/stt.py` (`faster-whisper`, self-hosted,
CPU-only, `whisper_model_size`/`whisper_compute_type` config, lazy
singleton model load on first request — never a cloud STT API). Dari
(`prs`) has no distinct Whisper training language; `language_code=prs`
hints the model with `fa` as the closest available option, a real accuracy
caveat (transcripts may lean Farsi spelling/vocabulary) not a bug. **Raw
audio bytes are never persisted to disk and never logged** — read into
memory, transcribed, discarded, matching the TTS-neighboring privacy bar.

Frontend owns: the mic/keyboard toggle (localStorage-persisted last choice,
NOT an account-wide server field — silent/typed is still the default), the
`MediaRecorder` capture + WASM transcription pipeline, and the graceful
degrade back to typing if mic permission is denied or `getUserMedia` is
unavailable — same "honest fallback, never silently dead" pattern as
`SpeakButton`/`speak()`.

## Course sections (reading/writing vs. speaking)

Every `Unit` now belongs to a section: `GET /courses/{id}/units` items gain
a `section: "reading_writing" | "speaking"` field (default
`"reading_writing"` for existing/legacy units) and a `locked: boolean`
field. `reading_writing` covers vocabulary, grammar, reading, and writing
exercise types (`grammar_check`, `reading_comprehension`, `writing_prompt`,
`fill_in_blank`, `translation`, etc. — no new exercise types needed, this
is purely a grouping/gating concept over the existing ones).
`speaking` units are **locked** (backend returns 409
`speaking_locked` on `POST /lessons/{id}/start` for a lesson in a locked
unit) until the learner has completed every `reading_writing` unit earlier
in that course's order. Later reading/writing units do not block an earlier
speaking unit. Frontend shows locked speaking units visibly-but-disabled
(not hidden) with a short explanation of what unlocks them, using the
`locked` field — never infer lock state client-side from other data.

Backend implementation choice: a `reading_writing` unit is complete when
all of its lessons are complete; only those preceding the speaking unit in
course order are prerequisites. Anonymous unit listings conservatively return
`locked: true` for speaking units because lock state is learner-specific.
