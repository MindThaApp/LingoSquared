# Lingo²

Local-first language learning app. Supports learning any of English,
Dutch, French, German, Italian, Spanish, Russian, Chinese (Mandarin),
Farsi, and Dari from any other language in that set — Farsi and Dari are
kept as fully separate languages/courses throughout.

- `backend/` — FastAPI + PostgreSQL API (built by Codex)
- `frontend/` — React + TypeScript web client (built by Claude)
- `docs/CONTRACT.md` — shared source of truth both sides build against
- `docs/BACKEND_PROMPT.md`, `docs/FRONTEND_PROMPT.md` — the build specs,
  negotiated between Codex and Claude before implementation started

This is for internal LAN testing (Debian media server via Docker Compose),
not a public deployment. See `backend/README.md` for exact setup commands
once the backend build is complete, and `frontend/README.md` for the web
client.
