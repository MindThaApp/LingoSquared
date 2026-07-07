# Lingo² launch program — build prompt for the executing Claude session(s)

Written 2026-07-07 by Fable, as the successor to
`docs/SONNET_BUILD_PROMPT_UPGRADES.md` (phases A–G, all shipped and
live-verified as of this date — see CLAUDE.md's "Current plan of
record"). That program fixed the runtime learning loop. This one gets
the app **into real users' hands and keeps it healthy there**. It was
written alongside a same-day fresh security/integrity audit of
`backend/app/**` (findings are Phase H below — they are new, not
recycled from the 2026-07-05 passes).

Everything standing in CLAUDE.md still binds: division of labor
(backend = Codex, dispatched and verified by Claude), the
non-negotiable verification bar, every footgun, the rejected-scope
list. Phases are lettered H onward to avoid collision with A–G in
logs and commit messages.

**The one-sentence thesis:** the mechanism is done; the remaining path
to launch is (1) a small set of genuinely new integrity/abuse fixes,
(2) *measured* — not estimated — content depth on the six launch
paths, (3) a first real deploy treated as a from-scratch operation
with backups and observability, and (4) the human-dependent audio and
beta-mechanics work only Ramin can do, scheduled so it never blocks
(1)–(3).

---

## Phase H — Pre-beta integrity and abuse fixes (Codex, small, do first)

These come from a 2026-07-07 code audit of the current
`app/api/router.py` / `app/schemas/api.py` / `app/services/**`. None
require a migration. All are additive and small; a single Codex
dispatch plus the standard verification pass should clear the set.

### H1. Speaking-lock bypass (integrity, the real find of this audit)

The server-enforced speaking unlock is only checked in
`POST /lessons/{id}/start`. But:

- `GET /units/{unit_id}/lessons` and `GET /lessons/{lesson_id}` return
  lesson content and exercise IDs for locked speaking units (and do so
  unauthenticated),
- `POST /exercises/{id}/answer` → `exercise_answer()` **creates the
  `LessonProgress` row itself if missing**, with no lock check, and
- `POST /lessons/{id}/complete` only requires that a `LessonProgress`
  row exists.

So a user can enumerate a locked unit's lessons, answer every exercise
directly by ID (earning XP), and then `complete` each lesson — fully
bypassing the unlock that CLAUDE.md describes as "server-enforced."
Fix: `exercise_answer()` and `complete()` must run the same
`speaking_locked` check `start()` does (one shared helper, three call
sites). Decide deliberately whether unauthenticated `GET
/lessons/{id}` on locked units is acceptable (content scraping is a
separate, lower concern) — but the *write* paths must be closed.
Verify live: fresh account, locked speaking unit, attempt the bypass
via curl, confirm 409 at both answer and complete.

### H2. Rate-limit the expensive endpoints (abuse/cost)

The three existing limiters cover login/register/answers only. Left
unlimited today:

- **`POST /tts`** — 5,000 chars/request against a shared
  4M-chars/month Google budget: one authenticated account can burn the
  entire month's TTS quota in ~800 requests (minutes), silently
  degrading every user to browser TTS until the 1st. Once the Azure
  key is provisioned this becomes real money, not just quota. Add a
  per-account limiter (e.g. 30/min) AND a per-account daily character
  cap (e.g. 100k chars/day — two orders of magnitude above real use).
- **`POST /stt/transcribe`** — CPU-bound faster-whisper on a
  single-process server; 5MB uploads; unlimited. One account (or one
  stolen token) can pin the API CPU indefinitely. Per-account limiter,
  low ceiling (e.g. 10/min) — it's a fallback path, real clients use
  WASM Whisper.
- **The generation endpoints** — `POST /reviews/session`,
  `POST /practice/{course_id}/batch`, `POST /units/{id}/checkpoint`:
  each call does the (now-memoized, still heaviest-in-app) batch
  generation and writes up to 20 `PracticeItem` rows. Add one shared
  per-account limiter (e.g. 20/min across the three) — generous for
  humans, fatal for loops.

Reuse `app/core/rate_limit.py` + the Settings-configurable-ceiling
pattern exactly as the existing three do (the e2e suite depends on
being able to raise ceilings via env).

### H3. Unbounded registration strings

`RegisterIn.display_name:str|None=None` (`app/schemas/api.py`) is the
one string field on the auth path that never got the bounded-payload
treatment every other free-form field on this endpoint has —
`password` is `max_length=128`, `email` is bounded by `EmailStr`'s own
RFC-length ceiling. An unbounded `display_name` is persisted verbatim
to `User.display_name` and echoed back on every `UserOut`/`MeOut`
response for the lifetime of the account, rendered directly in the
frontend nav/profile chrome — a multi-megabyte value is layout-breaking
at best and a cheap per-request storage/bandwidth amplification at
worst, since every subsequent authenticated response that serializes
the user re-sends it. `RegisterIn.timezone`/`LoginIn.timezone` have the
same unbounded-`str` shape, though the practical exposure is smaller —
`valid_timezone_or_none()` routes anything that isn't a real IANA zone
straight to `None`, so garbage is validated-then-discarded rather than
persisted — but there's no reason to hand an unbounded string to
`ZoneInfo()` at all.

Fix: `display_name:str|None=Field(default=None,max_length=100)` (100
chars comfortably covers any real display name; matches the existing
`description`/`triage_notes` bound convention already in this file) and
`timezone:str|None=Field(default=None,max_length=64)` (the longest real
IANA zone names, e.g. `America/Argentina/ComodRivadavia`, are under 40
chars — 64 is headroom, not a tight fit that could reject a real zone).
Both additive, schema-level only, zero migration, zero behavior change
for any legitimate registration or login.

Verify: register with a real name → unchanged; register with a
10,000-character `display_name` → `422 validation_error`, not a 500 and
not a silently truncated/stored value; existing accounts under the new
bound are unaffected (this only changes acceptance going forward, no
backfill needed).

### H4. Content-issue reports have no rate limit

`POST /exercises/{id}/report` and `POST /practice/items/{id}/report`
(`report_content_issue`/`report_practice_item_issue`, `app/api/
router.py`) are the only two authenticated write endpoints in the
entire router that never call `enforce_rate_limit` — not even the loose
120/min `ANSWER_RATE_LIMIT` every answer-submission path already shares.
Each call is cheap individually (one `ContentIssueReport` insert), but
the endpoint exists specifically to feed the admin triage queue that
`docs/APP_SPEC_FOR_FABLE_REVIEW.md` §3 names as the load-bearing
post-launch feedback loop — an unrated account (or one compromised
token) can flood that queue with thousands of rows, burying real
reports and degrading the coverage dashboard right when it matters most
(a fresh beta's first days). Fix: reuse `ANSWER_RATE_LIMIT` (both report
endpoints already sit next to the answer endpoints they report on), or
a dedicated, slightly tighter `REPORT_RATE_LIMIT` (e.g. 20/min) —
reporting is genuinely rarer than answering, so a dedicated limiter is
arguably more correct, and it's one more line in the existing
`register_limiter(RateLimiter(...))` pattern.

Verify: a real account reporting a handful of issues in normal use is
unaffected; a scripted loop past the ceiling on either report endpoint
gets `429 report_rate_limited` with `retry_after_seconds`, matching the
shape every other limiter already returns.

### H — verification bar for this phase

Same non-negotiable bar as A–G (compiler/pytest/frontend build/live
browser), applied specifically to: the speaking-lock bypass via a real
curl sequence against a fresh locked account (H1), a scripted burst
against `/tts`, `/stt/transcribe`, and each generation endpoint
confirming 429s fire at the configured ceiling while normal use is
unaffected (H2), a registration attempt with an oversized
`display_name` (H3), and a scripted report-spam burst against both
report endpoints (H4). All four are additive, no migration, small
enough for a single Codex dispatch plus one verification pass — don't
let this phase balloon into a general re-audit; that pass already
happened (`docs/NEXT_PHASE_ARCHITECTURE_SPEC.md` §2, Phase H0) and came
back clean beyond these four findings.

---

## Phase I — Prove content depth is measured, not assumed

Identical scope and rationale to `docs/NEXT_PHASE_ARCHITECTURE_SPEC.md`
§3 (its own Phase I) — not repeated here so the two documents don't
drift out of sync. Build the depth-measurement ruler (teaching-minutes
and unique-generable-practice-items per launch pair) *before* authoring
the last mile of content toward the ≥10hr bar, or the last mile is
aimed blind.

---

## Phase J — First real deploy, treated as from-scratch

Identical scope to `docs/NEXT_PHASE_ARCHITECTURE_SPEC.md` §2's Phases
H1–H4 (backup, observability, `PracticeItem` GC, and a full
isolated-stack deploy rehearsal before touching 192.168.4.4) — read
that document for the detail rather than this one duplicating it. The
one build-prompt-specific addition here: fold this program's own Phase
H (H1–H4 above) into the SAME Codex dispatch/verification pass as
whatever code changes come out of the deploy rehearsal's dry run, so
the live server's first real deployment ships with the integrity fixes
already in, not as a fast-follow patch applied right after real users
arrive.

---

## Phase K — Human-dependent work (schedule so it never blocks H–J)

- **ADMIN_EMAILS / CORS_ORIGINS real values**: product decisions only
  Ramin can make (see `PRE_DEPLOY_RUNBOOK.md`) — get these answers
  early so Phase J's deploy isn't blocked waiting on them at the last
  step.
- **Azure Farsi TTS key provisioning**: built and tested, not yet live
  (CLAUDE.md's Secrets section) — a Ramin-side Azure Portal action, not
  code; once H2's per-account TTS cap lands this becomes safe to flip
  on without a runaway-cost risk.
- **fa/prs recorded-audio session**: Phase D's pipeline (manifest →
  upload → serving → priority chain) is fully built and verified; it
  has zero real clips yet. Pure human time (Ramin recording against
  `scripts/audio_manifest.py`'s queue), not a build task — schedule in
  parallel with H–J, it blocks nothing else.
- **nl native-review pass**: ongoing per CLAUDE.md's standing
  instruction (Ramin reviews nl content directly as it's authored) —
  keep this flowing continuously, don't batch it up to the end.

None of Phase K gates H, I, or J. It's surfaced here only so it isn't
forgotten while the code/ops phases are in flight.

---

## Ordering, scope discipline, and definition of done

```
H (integrity/abuse fixes, Codex, small)  ->  J (backup/observability/GC/rehearsal,
                                                 per NEXT_PHASE_ARCHITECTURE_SPEC.md §2)
                                                          |
                              I (content-depth ruler)  ->  finish content to the measured bar
                                                          |
                                          -- BETA LAUNCH GATE --
```

K runs in parallel with all of the above, gating nothing, blocked by
nothing.

- Order: H before J — don't deploy a from-scratch stack that still has
  the speaking-lock bypass or an unlimited `/tts` in it. I can start
  before H/J finish (it's a measurement script against existing
  content, no dependency on the code fixes), but content authoring
  toward the measured bar should wait for the ruler to exist.
- Same non-negotiable verification bar as every phase before this one:
  compiler validation, backend pytest, full frontend build, live
  browser verification with a fresh account — reading a diff is not
  verification, this project has the scar tissue to prove it.
- If any phase here turns out to need something CLAUDE.md's
  rejected-scope list already closed off (runtime LLM, hearts, Redis
  before there's a real scale reason), stop and ask Ramin — the
  standing rule from the A–G program is unchanged.
- **Done means**: a fresh account cannot bypass the speaking lock or
  exhaust the TTS budget via curl; the live server has a tested backup
  and a first log line for every swallowed exception; a from-scratch
  deploy has actually been rehearsed once, not just documented; and the
  ≥10hr content-depth bar has a real number behind it, not an estimate
  — every one of those observed directly, the same discipline every
  phase since A has been held to.