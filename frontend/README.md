# Lingo² Frontend

Local web frontend for Lingo², built against the API contract in
`../docs/CONTRACT.md`. React + TypeScript + Vite, React Query for
server-state, React Router for navigation.

## Run locally

```bash
cd frontend
npm install
cp .env.example .env   # defaults to http://localhost:8000
npm run dev
```

Opens on `http://localhost:5173`.

## Run for LAN testing (e.g. against the backend on the Debian media server)

```bash
npm run dev -- --host 0.0.0.0
```

Then set `VITE_API_BASE_URL` in `.env` to the backend's LAN address, e.g.
`http://192.168.4.x:8000`, and access the frontend from another device at
`http://<this-machine-ip>:5173`.

## Build for production

```bash
npm run build
npm run preview -- --host 0.0.0.0
```

## Structure

- `src/api/` — typed API client (`client.ts`, `endpoints.ts`, `types.ts`
  mirroring `docs/CONTRACT.md`)
- `src/auth/` — auth context (JWT storage, 24h token, hard logout on 401)
- `src/components/exercises/` — one renderer per exercise type
- `src/components/TextBlock.tsx` — per-block RTL/LTR text rendering
- `src/pages/` — route-level screens

## Implemented

Auth (register/login/logout), language/course picker (source ≠ target
enforced client-side too), course → units → lessons drill-down, lesson
runner for all 13 exercise types (listening/speaking render as "coming
soon" placeholders, matching the backend), spaced-review flow, profile
dashboard (XP/streak/achievements/progress).

## Not implemented yet (by design, see docs/FRONTEND_PROMPT.md)

Admin content import/export UI (API-only for now), offline/PWA, push
notifications, payments, mobile (Expo) apps.

## Known gaps / things to verify against the real backend

This was built in parallel with the backend against the shared contract,
before the backend existed. Once integrated (Codex owns that pass, see
`docs/CONTRACT.md`), verify:
- Exact `prompt` field names the backend actually returns per exercise
  type (`options`, `word_bank`, `pairs`, plus `back_text_blocks` for
  flashcards — this last one wasn't in the original contract schema and
  was added here as a reasonable extension; flag if the backend uses a
  different name).
- `/me/reviews` pagination — flat array assumed here; add cursor handling
  if the backend implements it.
