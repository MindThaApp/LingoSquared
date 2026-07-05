# Lingo² backend

FastAPI/PostgreSQL backend for the Lingo² local language-learning application. It supports the ten contract languages, arbitrary ordered language pairs, server-side exercise grading, progress, XP/streaks, achievements, and SM-2 review scheduling.

## Debian/Docker setup

Install Docker Engine and the Compose plugin using Docker's Debian repository, then:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $VERSION_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin git
sudo usermod -aG docker "$USER"
# Log out and back in once so group membership takes effect.
```

Application setup:

```bash
git clone <repository-url> LingoSquared
cd LingoSquared/backend
cp .env.example .env
# Edit POSTGRES_PASSWORD and JWT_SECRET in .env before first start.
docker compose build
docker compose up -d db
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m app.content.seed
docker compose up -d api
docker compose ps
docker compose logs -f api
```

Run tests against a separate database so test schema cleanup cannot destroy development data:

```bash
docker compose exec db createdb -U lingosquared lingosquared_test
docker compose run --rm \
  -e DATABASE_URL=postgresql+psycopg://lingosquared:change-me@db:5432/lingosquared_test \
  api pytest
```

Replace `change-me` in the test URL with the value in `.env`. To stop the stack, use `docker compose down`; add `-v` only when intentionally deleting database data.

From another LAN device, open `http://SERVER_LAN_IP:8000/docs`. Set `API_PORT` in `.env` if port 8000 is unavailable.

## Operations

```bash
# Apply new migrations
docker compose run --rm api alembic upgrade head

# Idempotently refresh the original seed course
docker compose run --rm api python -m app.content.seed

# Follow API logs
docker compose logs -f api

# Export content (TOKEN must belong to ADMIN_EMAILS)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/admin/content/export > content.json

# Import that content
curl -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  --data @content.json http://localhost:8000/admin/content/import
```

The seed contains all ten language records plus original en→fa, en→prs, and
prs→en A1 example courses, plus an en→prs A2 example course. Every reseeded lesson has an ordered teaching
phase before its exercises. The Dari courses use their own `prs` content and
remain separate from Farsi.

Lesson teaching cards reuse `content_items` with a lesson association and
order. Admin imports accept `teaching` on each lesson; each card contains a
kind, optional title/note, and mixed-language `text_blocks`. Legacy imports
may omit the array and the lesson API returns `teaching: []`.

Course levels are validated CEFR values (`A1`, `A2`, `B1`, `B2`, `C1`,
`C2`). Imports default to A1 when the level is omitted, and course listings
sort by level then title. Multiple independently progressed courses may exist
for one language pair; there is no placement or enrollment state.

## Authentication and administration

JWT bearer tokens expire after 86,400 seconds (24 hours). There is no refresh flow. Registration grants administrator status only when the normalized email is listed in `ADMIN_EMAILS`. Admin import replaces a course with the same source, target, and title atomically within the request transaction.

All API errors use `{ "error": { "code": "...", "message": "..." } }`. Correct answers are omitted from lesson and review prompts and returned only after answer submission.

## Text-to-speech

Authenticated clients call `POST /tts` with `text` and `language_code`.
Supported languages use ElevenLabs `eleven_multilingual_v2` and return raw
`audio/mpeg`. Farsi and Dari always return the contract's browser-TTS JSON
fallback without contacting ElevenLabs. Missing credentials and provider
errors also return a fallback instead of failing the request.

Set `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, and optionally
`ELEVENLABS_MONTHLY_CHAR_BUDGET` (default 10,000). Usage is counted by UTC
calendar month. Characters are transactionally reserved before each provider
call; requests that would exceed the configured budget never reach ElevenLabs.
The reservation is committed only after audio is returned and is rolled back
on provider errors, so failed generations do not consume the local budget.

## Course sections

Units are grouped into `reading_writing` and `speaking` sections. The unlock
threshold is 100%: every lesson in every reading/writing unit in the course
must be completed by the learner. Until then, speaking units return
`locked: true`, and starting one of their lessons returns HTTP 409 with code
`speaking_locked`. Anonymous unit listings conservatively report speaking
units as locked.

## Review and progress behavior

Review items are created when an exercise is answered. Scheduling uses SM-2: successful first and second reviews use one- and six-day intervals, later intervals multiply by the ease factor, and failed reviews reset repetitions with a one-day interval. SM-2 is widely understood, deterministic, and sufficient for this local MVP.

Flashcards are self-graded: the prompt exposes `back_text_blocks` for the
reveal step, then answer and review submissions send `{"response":"known"}`
or `{"response":"unknown"}`. These map to successful or failed SM-2 recall;
flashcards never use typed-answer equality grading.

`GET /me/reviews` always uses cursor pagination, capped at 200 items per page, and returns `{ "items": [...], "next_cursor": string|null }`. This avoids a later response-shape change as a user's review history grows.

XP is awarded once per correct submission (including retries); this MVP does not prevent repeated practice from awarding XP. Streak activity uses the API host's calendar date. Hearts, gems, and leaderboard flags are configuration-gated; persistence fields exist, while no contract endpoints expose those optional features yet.

## Content format

Admin import accepts `{ "courses": [...] }`. Each course contains ordered units, lessons, exercises, and optional `content_items`. Content item kinds are `vocabulary`, `phrase`, `grammar_note`, `dialogue`, `pronunciation_note`, and `cultural_note`. Each exercise requires prompt `text_blocks` whose language and direction match seeded language metadata. `correct_response` is JSON and may be a string, list, object, number, or boolean.

Validation is available without mutation at `POST /admin/content/validate` with `{ "content": { "courses": [...] }`. The missing report lists absent ordered language pairs and content kinds.

## Local non-Docker development

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg://lingosquared:change-me@localhost:5432/lingosquared
alembic upgrade head
python -m app.content.seed
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pytest
```

Configuration is entirely environment-driven; see `.env.example`. PostgreSQL is intentionally not published to the host in Compose.

## API examples

```bash
curl -X POST http://localhost:8000/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"learner@example.com","password":"long-password","display_name":"Learner"}'

curl -X POST http://localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"learner@example.com","password":"long-password"}'

curl http://localhost:8000/languages
curl 'http://localhost:8000/courses?source=en&target=fa'
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/lessons/$LESSON_ID/start
curl -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"response":"سلام"}' http://localhost:8000/exercises/$EXERCISE_ID/answer
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/me/xp
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/me/streak
```

## Known limitations

- Listening and speaking exercise types are schema placeholders only.
- No refresh tokens, password reset/email verification, audio storage, public authoring UI, or public course-create endpoint.
- Writing prompts are exact-match graded; semantic grading requires a future explicit design.
- Daily goals have persisted defaults but no contract endpoint for changing them.
- Migrations use a single initial schema revision; future changes should add normal incremental Alembic revisions.
