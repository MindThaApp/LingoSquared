# Backend Build Prompt (for Codex)

You are building the backend for **Lingo²**, a local-first language learning
app. This is a from-scratch build — there is no prior backend implementation
to review or merge. A frontend is being built in parallel by Claude under
`frontend/` in this same repo; you do not need to touch it.

**Scope boundary:** only write inside `/Users/raminazizi/dev/LingoSquared/`.
Specifically `backend/` for code, and you may propose edits to
`docs/CONTRACT.md` if you find a genuine gap (see "Contract" below) — but
flag any such change explicitly rather than just changing it silently.
Never write anything under `/Users/raminazizi/dev/portal` — unrelated
project, do not touch.

Do not build a public production deployment yet — this is for internal LAN
testing on a Debian media server via Docker Compose.

## Contract (read first, do not diverge without flagging it)

`docs/CONTRACT.md` in this repo is the shared source of truth between
backend and frontend: the 10 supported languages, the exercise-type enum,
API endpoint list and request/response schemas, auth mechanism, error
shape, and port conventions. It also documents the lesson-payload shape
(all exercises in one response, no correct answers exposed, per-text-block
language/direction for mixed-language exercises), the no-refresh-token /
24h-token decision, and the no-public-course-creation-endpoint decision —
all settled after a Codex review pass on an earlier draft, so treat these
as resolved, not open. Follow it exactly so the frontend (built
independently, in parallel) integrates without rework. If you still think
something is wrong or underspecified, say so in your final report rather
than silently changing behavior.

You (Codex) also own the final backend+frontend integration pass once both
builds are done — see "Integration ownership decision" in
`docs/CONTRACT.md`.

## Product requirements

Lingo² must support learning **any of these 10 languages from any other**:
English (en), Dutch (nl), French (fr), German (de), Italian (it),
Spanish (es), Russian (ru), Chinese/Mandarin Simplified (zh), Farsi (fa),
Dari (prs). Do not assume English is always the source language — every
ordered pair (source != target) among these 10 must be constructible.

Farsi and Dari are **separate language records**, both RTL, each with their
own vocabulary/pronunciation/grammar/cultural notes and their own courses in
both directions (en→fa, en→prs, fa→en, prs→en, etc. are all distinct
courses). Shared terms are allowed but never auto-merged.

## Target architecture

```
backend/
  app/
    main.py
    core/          # config, security/JWT, settings from env
    db/            # session, base, engine
    models/        # SQLAlchemy/SQLModel models
    schemas/        # Pydantic schemas
    api/           # FastAPI routers
    services/      # business logic (SRS scheduling, XP/streak calc, etc.)
    content/       # import/export/validation of course content
    gamification/  # XP, streaks, achievements, hearts/gems (config-gated)
    review/        # spaced repetition engine
  tests/
  alembic/         # migrations
  Dockerfile
  docker-compose.yml
  .env.example
  README.md
```

Stack: FastAPI, PostgreSQL, Alembic migrations, Pydantic schemas,
SQLAlchemy/SQLModel models, Docker Compose.

## Feature checklist

**Content model:** courses, units, lessons, exercises, vocabulary, phrases,
grammar notes, dialogues, pronunciation notes, cultural notes.

**Exercise types** (exact string enum, must match `docs/CONTRACT.md`):
`multiple_choice`, `translation`, `reverse_translation`, `fill_in_blank`,
`word_order`, `matching_pairs`, `listening_placeholder`,
`speaking_placeholder`, `dialogue_response`, `grammar_check`, `flashcard`,
`reading_comprehension`, `writing_prompt`. The two placeholder types just
need schema/fields defined now (no real audio/speech implementation) so no
migration is needed when they're built out later.

**Progress tracking:** lesson start, exercise answer submit, lesson
complete, skill progress, vocabulary progress, grammar progress, review
item creation.

**Gamification:** XP, streaks, daily goals, achievements, optional
hearts/lives, optional gems/coins, local leaderboard (disabled by default —
config flag).

**Adaptive review (spaced repetition):** due review items, review answer
submit, mastery update, next-due-date update. Use a standard SRS algorithm
(e.g. SM-2 or a documented variant) — pick one, document your choice and
reasoning in the README, don't invent something exotic.

**Admin/content tooling:** content import, content export, content
validation, missing-content report, seed command (must seed all 10
languages and at least one full course pair, e.g. en→fa or en→es, with
enough content — units/lessons/exercises/vocab — to be genuinely testable
end-to-end, not just a stub row).

## API endpoints (must match `docs/CONTRACT.md` exactly)

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

`GET /languages` must return the RTL/LTR + script metadata shape defined in
the contract so the frontend never has to hardcode direction per language
code.

Auto-generate OpenAPI docs (FastAPI gives you this for free at `/docs`) —
make sure schemas are complete enough that it's actually useful as API
documentation for a frontend developer who hasn't read your code.

## Language-pair test (required)

Add a test that iterates all ordered pairs of the 10 languages (source !=
target, 90 pairs) and confirms the backend can construct/represent a course
for that pair (doesn't require seeded content for all 90 — just that the
data model and course-creation path don't assume a fixed source language
anywhere).

## Minimum passing tests

Auth register/login; language seed (all 10 present); all ordered language
pairs supported; course creation; lesson retrieval; answer submission; XP
update; streak update; review schedule update; content import validation;
Farsi/Dari separate courses; RTL metadata present and correct for fa/prs.

Note: "course creation" here means exercising the admin import/seed path
end-to-end and asserting the resulting course/units/lessons are queryable
via the `GET` endpoints — there is deliberately no public `POST /courses`
(see `docs/CONTRACT.md`, "no public POST /courses" note).

## Docker / LAN deployment

Debian media server target, Docker Compose. Bind `0.0.0.0` inside the
container; host port configurable via `.env` (`API_PORT`, default 8000 —
match `docs/CONTRACT.md`). Postgres should not be exposed to the host by
default. Provide exact commands in the README for: clone/open repo, copy
`.env.example` to `.env`, start services, run migrations, seed content, run
tests, view logs, and access `/docs` from another LAN device.

## Constraints (do not overbuild)

No frontend work. No public cloud deployment. No paid third-party APIs by
default. Do not scrape or copy content from Duolingo/Babbel — original or
public-domain seed content only. No app-store packaging.

## When finished, report

1. Final file tree
2. Exact Debian/Docker setup commands (copy-pasteable)
3. Test results (pass/fail counts, and paste any failures)
4. API docs URL
5. Sample API calls (curl) for: register, login, get languages, get a
   course, start a lesson, submit an answer, get XP/streak
6. Known limitations
7. Any place you deviated from `docs/CONTRACT.md` and why
