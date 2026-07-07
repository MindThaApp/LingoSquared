# Lingo² — next-phase architecture spec (post Phase A–G)

Written 2026-07-07 by Fable, as the successor to
`docs/APP_SPEC_FOR_FABLE_REVIEW.md`. That document reviewed the app as
it stood before the upgrade program and produced the phased work order
in `docs/SONNET_BUILD_PROMPT_UPGRADES.md`. **Phases A–G are now all
shipped and live-verified** (see CLAUDE.md's "Current plan of record").
This document answers the question that comes next: with the runtime
learning loop rebuilt and the publish-gate content push mid-flight,
**what should the project actually do between now and a real beta
launch — and what should it deliberately not do?**

Read `CLAUDE.md` first for current state. This spec assumes it.

---

## 0. The one-sentence thesis

The feature program is essentially done; **the remaining work to launch
is operational, not architectural.** The single biggest risk to the
"very usable, minimum bugs" publish bar is no longer a missing feature —
it is that the app has never been deployed to its target box, has no way
to observe itself once real users are on it, has no data backup, and has
no measurement of whether the ≥10hr content-depth bar is actually met.
Every one of those is cheaper to fix now than after the first beta user
hits a silent failure the team can't see. Resist the pull toward Phase H
= "more learning features." The next phase is **make the thing you
already built safe to run in front of strangers.**

This reorders the instinct baked into the prior spec (which was
correctly feature-first, because the runtime loop was genuinely broken).
That job is done. The center of gravity has moved.

---

## 1. Where the program actually stands

**Done and live-verified (A–G):** lexeme-level SRS unified with the
practice engine; in-lesson error recycling; typo-tolerant grading with
per-language strictness and distractor-specific feedback; recorded-audio
mechanism + dialogue per-speaker-turn split; timezone-correct streaks,
streak freeze, daily quests; home screen leading with due reviews; unit
checkpoint test-out. Plus standalone wins outside the program: real
mic-based STT speaking exercises, Azure Farsi TTS, per-language TTS
speed. The backend surface is coherent and the grading paths have been
hardened against the two real content-shape bugs (matching_pairs,
word_order) that shipped and were caught live.

**Genuinely not done, and correctly deferred:**
- E4 (web push) — the prior spec itself said skip if effort balloons.
- `user_grammar_srs` — Phase A explicitly built lexeme SRS first and
  left grammar SRS as "mechanical to add, don't build yet."
- The content-depth push itself: the ≥10hr teaching + ≥10hr practice
  bar per launch pair is **stated but never measured** (CLAUDE.md and
  the prior spec both say so in as many words).
- A real deploy: the live box (192.168.4.4) has never been deployed to
  beyond original setup. The next deploy is from-scratch-equivalent.

The gap between "features shipped" and "launchable" is entirely in that
second list, and only the last two items are on the critical path.

---

## 2. Phase H — Pre-deploy hardening (do this first; it is the launch blocker)

This folds in the security/pre-deploy re-audit. I checked the open
items from CLAUDE.md's "Known limitations" against the actual code and
the runbook. **Good news: the previously-flagged items are genuinely
handled or correctly documented.** The findings below that are new are
operational, not vulnerabilities.

### H0. Audit result on the already-flagged items (verified, not just re-listed)

- **ADMIN_EMAILS placeholder / admin-registration race** — real, and
  correctly captured as a *deployment* step in
  `PRE_DEPLOY_RUNBOOK.md` (set the real email before any invite,
  register Ramin's account immediately). Not a code bug. The runbook
  handles it. Keep it on the pre-invite checklist; nothing to build.
- **CORS_ORIGINS localhost-only** — same: documented in the runbook as a
  product decision (what the real origin is), fails safe. Nothing to
  build; just don't forget it at deploy time.
- **Unbounded `response` DoS** — **fixed and verified in code.**
  `AnswerIn` / `ContentIssueReportIn` route through
  `_bounded_payload_size()` (5000 serialized-char cap) in
  `app/schemas/api.py`, with `test_security_payload_bounds.py` covering
  it. This closes the O(len×len) Damerau-Levenshtein amplification. Good.
- **JWT_SECRET** — runbook flags it (confirm it's real, never regenerate
  on a live deploy). Auth uses HS256 with a 24h expiry, no refresh, no
  revocation — all accepted scope, fine for a home-server beta.
- **Rate limiting** — present on register/login/answer, configurable
  ceilings, in-memory single-process (correctly documented as fine for
  one uvicorn process; move to Redis only if scaled). Adequate.
- **Media/STT upload paths** — properly bounded (5 MB cap, MIME check,
  key regex rejecting `..`, atomic link-based write). Good.

**Conclusion of the security re-audit: no new vulnerability found. The
input-validation and auth surface is in good shape for a beta.** The
real pre-deploy risks are the three operational gaps below.

### H1. Database backup — currently zero, this is the highest-severity gap

The runbook itself notes no backup exists anywhere in the project's
history. For a local-first app whose entire value to Ramin is his own
fa/prs progress plus (post-launch) real beta users' accounts and SRS
state, **a single `docker volume` loss is unrecoverable.** Before any
beta invite: a scheduled `pg_dump` (cron on the box, or a
`docker compose` one-shot) to a second disk / the NAS at 192.168.4.8,
with at least one restore actually tested end-to-end. This is a few
lines of shell, not a feature — but it is the difference between "a bug
lost a day of one user's data" and "a disk event ended the beta." Do it
before H2.

### H2. Observability — the app cannot currently tell you when it fails

This is the finding I'd most want Ramin to internalize. The stated
launch strategy is "ship early, fix errors as users report them via the
in-app report button." But that only covers **content** errors a user
notices and bothers to report. It covers none of:

- `/tts` swallows every synthesis failure in a bare `except Exception`
  and returns a browser-fallback — a corrupted Google credential, an
  expired Azure key, or a quota exhaustion is **invisible** (CLAUDE.md's
  own footgun entry admits "the `/tts` route's except Exception
  swallows the real exception with no logging").
- `/stt/transcribe` returns a generic 500 on any failure with no trace.
- The global `except Exception` handler in `main.py` returns a clean
  "unexpected server error" to the client and logs **nothing**
  server-side.
- Grep confirms only `app/content/service.py` has a logger at all. The
  request path has no structured logging, no error aggregation, no
  request-id, no latency metric.

For a self-hosted beta this doesn't need Datadog. It needs: (a) the
global exception handler and the `/tts`//`/stt` catch blocks to
`logger.exception(...)` before returning the safe response; (b) a
single rotating log file the box retains; (c) optionally a dead-simple
error counter surfaced on the existing admin surface. Without this, "fix
errors as noticed" silently means "fix only the errors a non-technical
beginner both notices and reports" — which for audio/grading/infra
failures is close to none. **This is the load-bearing complement to the
report-button loop the whole ship-early strategy rests on, and it's
missing.** Cheap to add; do it before real users, not after.

### H3. `PracticeItem` unbounded growth

Every review session, checkpoint, and Endless Practice scroll inserts
`PracticeItem` rows (plus `PracticeAttempt`), and nothing ever deletes
them — there is no GC path in `app/practice/service.py`. On a
single-box Postgres this is slow-burn, not urgent, but a heavy user
scrolling the infinite practice feed generates unbounded rows with a 24h
answer window that are dead weight forever after. A periodic reaper
(delete answered/expired `PracticeItem`s older than N days; keep
`PracticeAttempt` if you want the history, or roll it into an aggregate)
is worth scheduling alongside the H1 backup cron. Not a launch blocker;
a "don't let the DB quietly bloat over the first months" item.

### H4. Deploy dress rehearsal on an isolated stack

The next deploy is from-scratch-equivalent and the ordering is subtle
(migrations → seed → `up -d` → content import → **lexeme backfill →
practice import**, an order that was documented backwards once and
causes 100% practice-import failure if wrong). Before touching
192.168.4.4, run the entire runbook against a throwaway isolated compose
project end-to-end — the `faqa`/`fib`/`play` stacks other sessions are
standing up are, whatever else they're for, exactly the right shape for
this. A rehearsal that reaches a working seeded stack from an empty
volume is the real pre-flight check; the runbook's prose is not.

---

## 3. Phase I — Prove the content-depth bar (measurement, not authoring)

The ≥10hr teaching + ≥10hr practice bar is a hard publish-gate
requirement that **has never been measured** — both CLAUDE.md and the
prior spec say the practice hours are "meant to come from" the Endless
Practice engine and that "actual hour-depth per path hasn't been
separately measured." Shipping against an unmeasured gate is shipping
against a vibe.

This does not need new content first — it needs a **ruler**. A small
script (INFRA lane, sibling to `audio_manifest.py`) that estimates, per
launch pair: teaching-content minutes (cards × a calibrated
seconds-per-card, split by kind — a dialogue card is not a vocab card)
and practice depth (unique generable items before the anti-repeat
sampler starts recycling, which is the honest measure of "hours of
non-repeating practice," not raw template count). Template *count* is a
proxy that can badly overstate real depth if the lexeme pool feeding the
slots is thin. Once the ruler exists, the content lanes have a target
they can actually converge on and Ramin has a number to gate on. **Build
the ruler before authoring the last mile of content**, or the last mile
is aimed blind.

---

## 4. Phase J — grammar SRS (the one real feature still owed)

Phase A deliberately shipped lexeme SRS only and left `user_grammar_srs`
as "designed to be mechanical to add." It's the one genuine pedagogical
gap remaining: the app spaces *vocabulary* retrieval but not *grammar
points*, so a learner who's memorized every word can still never be
re-tested on the case/gender/word-order rules that are the actual hard
part of nl and de (and the ezāfe/formal-register contrasts in fa). This
matters more the moment German is a real path — German is where "knows
the words, can't build the sentence" is most acute.

Do it **after** H and I, and only if the beta's real usage shows grammar
retention is the weak point (the report queue + H2 observability will
tell you). It's the highest-value *feature* left, but it is still a
feature, and the thesis of this document is that features are no longer
the gate. Build the parallel `user_grammar_srs` keyed to grammar-point
content items exactly as Phase A's design anticipated; reuse the same
`schedule()` and format-ladder machinery. No new architecture — the
Phase A design already carved the socket for it.

---

## 5. Answers to the three standing questions the prior spec asked Fable

The prior spec closed with three questions. Now that the program has
shipped, the answers are load-bearing for what's next:

1. **Procedural-not-generative practice — does it hold up?** Yes, and it
   has now proven itself in production shape across 6 directions. The
   one caveat surfacing post-ship: procedural recombination's *real*
   depth is bounded by lexeme-pool size, not template count (see Phase
   I). The decision was right; just measure it honestly rather than
   trusting the template tally.
2. **Depth-first on fa/prs vs. pulling a Latin path forward for working
   audio?** This is now moot in the way that matters: **nl is the Latin
   reference path with full working audio**, and it's the primary UX
   verification target. fa has Azure TTS built (pending a real key); prs
   remains audio-gapped and always will until recorded human audio
   exists. The right framing going forward: **nl is the "does the whole
   experience feel good" path; fa/prs are the "does the hard machinery
   work" path.** Keep both roles explicit — don't let nl's polish hide a
   regression that only shows on RTL/script-strict/no-TTS fa/prs.
3. **FSI/Tatoeba-as-reference red flags?** None new. The policy in
   AUTHORING_GUIDE §10 (FSI/Peace Corps public-domain as scaffold with
   mandatory modernization; Tatoeba reference-only, never copied) is
   sound. The only watch-item is the one the fresh-context review
   process already catches: FSI's 1960s-70s register leaking through as
   dated phrasing. That's a content-review concern, not a licensing one.

---

## 6. Deliberate non-goals for this phase (don't get pulled into these)

- **No new gamification.** Hearts/leagues/gems stay rejected. Daily
  quests + streak freeze are the accepted ceiling and they shipped.
- **No mobile app yet.** Expo/React Native remains the correct *future*
  path reusing the JSON API; it is not this phase and not a launch
  blocker for a PWA-first product.
- **No runtime-LLM content.** Unchanged, permanent.
- **No B1+ content breadth push for launch.** The launch gate is depth
  on 6 directed paths, not breadth. The other 12 paths keep dripping.
- **No Redis / multi-worker scale-out** until a real traffic reason
  exists. The in-memory rate limiter and single uvicorn process are
  correct for a home-server beta; premature horizontal scaling would
  just add failure modes.

---

## 7. Recommended ordering

```
H1 (backup)  ->  H2 (observability)  ->  H4 (deploy rehearsal)
     |                                        |
H3 (PracticeItem GC, alongside H1's cron)     |
                                              v
              I (content-depth ruler)  ->  finish content to the measured bar
                                              |
                                    -- BETA LAUNCH GATE --
                                              |
              J (grammar SRS)   -- only if beta usage shows grammar is the weak point
              E4 (web push)     -- still last, still optional
```

H is the launch blocker and is mostly shell scripts and log lines, not
feature code — days, not weeks. I is a single measurement script that
unblocks a confident "we hit the bar" call. Everything past the launch
gate is genuinely post-launch, driven by what the (now-observable) beta
actually shows. The feature-building phase of this project is over; the
**operate-it-safely** phase is the one that gets it in front of users.
