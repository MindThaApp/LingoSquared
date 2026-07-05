# Lingo² — app spec & build methodology (for Fable review)

Written 2026-07-05 by the executing Claude session, for Fable to review
against the architecture Fable itself designed. This is a snapshot
document — what the app IS, and HOW it's being built — not the
chronological build log. For full session-by-session detail, see
`CLAUDE.md` at the repo root. For the exact API/schema contract, see
`docs/CONTRACT.md`. For the canonical phased roadmap and locked scope
decisions, see the `project-lingosquared-roadmap` memory file.

## 1. What this app is

Lingo² is a Duolingo/Babbel-caliber language-learning app covering
**18 directed learning paths**: English to/from each of nl, fr, de, it,
es, ru, zh, fa, prs (hub-based — no non-English↔non-English pairs).
Ramin (the product owner) is personally the primary user for the
en↔fa/prs paths; the app is intended for real public use beyond that.

**"Complete" is defined as**: genuine fluency per language, full CEFR
A1→C2 — not just A1/A2 as this section originally said. Content
build-out order is still basics (A1 across all 18 paths, then a
usage-prioritized A2 wave) → intermediate (B1/B2) → advanced (C1/C2),
repeated per language, expect many incremental releases within each
tier rather than one big drop per tier.

**Publish is a separate, much earlier gate (decision, 2026-07-05):**
Ramin does not want to wait for the above breadth before shipping.
Publish as soon as the core runtime (the upgrade program in
`docs/SONNET_BUILD_PROMPT_UPGRADES.md`) is solid and the first
lesson(s)/unit(s) actually shipped are genuinely good — not gated on
a full A1 pass across all 18 paths. The in-app content-issue report
button + admin triage queue (§3) is the load-bearing feedback loop
that makes this viable: real user reports after launch feed back into
what Codex/Claude prioritize next, so quality compounds via live usage
rather than requiring near-perfect content pre-launch.

**Publish-gate language set, decided 2026-07-05: en↔nl and en↔fa/prs
only** (6 directed paths). These are exactly the languages Ramin can
personally verify — nl natively (the designated native-review
language), fa/prs as his personally relevant pair, shipped as a bundle
since they share ~100% of the RTL/script tooling from Phase 1/2. The
other 15 directed paths (Latin cohort, ru, zh) keep building toward A1
per the existing phase order but are NOT required to be launch-quality
before shipping — they continue as post-launch drip content.

**Publish-gate quality bar, decided 2026-07-05: "very usable, minimum
bugs," not a phase checklist.** Real beta users on en-nl/en-fa/prs need
to hit essentially no functional breakage, so their feedback is about
content/pedagogy/UX quality, not bug reports. **The executing Claude
session does this verification BEFORE any user sees it** — the
existing non-negotiable verification bar (compiler + backend pytest +
full frontend build + live browser verification with a fresh account,
run against the actual lesson/review/practice flows these three
languages will be used through) is what earns "minimum bugs." The
report-button → triage-queue loop is the NEXT layer, for once the app
is already solid — not a substitute for pre-launch verification.

**Publish-gate content depth, decided 2026-07-05: ≥10 hours new
teaching content + ≥10 hours practice + working scored module
checkpoints, per launch language pair.** Enough to get someone by
day-to-day in-country, not a demo. The ≥10 practice hours are meant to
come from the Endless Practice engine (currently fa→en-only, needs
extending to all 6 launch paths), not hand-authored drills — and
"module tests with scores" means Phase F (unit checkpoint tests, see
`docs/SONNET_BUILD_PROMPT_UPGRADES.md`) is now a hard publish-gate
requirement, not deferred post-launch polish. See the
`project-lingosquared-roadmap` memory file's "Ship-early,
drip-content strategy" section for the full note.

**Platform**: PWA first (installable on iPhone/iPad/Android/desktop,
offline-capable, web push) — one codebase, no app-store dependency to
ship. Native Expo/React Native apps are a deliberately deferred later
phase, reusing the same JSON API. Per-language-audience app variants
(e.g. a Dari-focused build) are supported as build-config flavors of
the same codebase, not separate forks.

**Explicitly rejected scope** (don't re-propose without a strong new
reason): hearts/lives, leagues/leaderboards, gems/currency, an
elaborate mascot cast. Accepted instead: daily quests, one earned
streak freeze, light recurring dialogue characters, and (new this
session) an endless AI-assisted practice feed — see §6.

## 2. Content architecture (the actual hard part of this product)

Four layers, in order of authoring:

1. **Universal competency spine** (`docs/content/universal_spine.yaml`)
   — language-agnostic communicative *outcomes* with stable IDs (e.g.
   `universal.a1.greetings.open_close_exchange`). The spine defines
   outcomes only, not ordering — each language's realization may
   prepend its own script/phonology "module 0" (Persian/Dari alphabet,
   Chinese pinyin+tones) and reorder/split/reweight spine nodes freely.
   **24 A1 outcomes currently defined** (greetings, introductions,
   numbers, dates, time, family, food, shopping, places, directions,
   routines, plans, past events, preferences, comparisons, travel,
   health, work, housing, weather, clothing, emotions, communication,
   money/payments — the last 5 added 2026-07-05, verified compiling
   clean) — extensible, not a hard-capped list.
2. **Target-language realization** (`docs/content/realizations/<lang>/`)
   — one set per target language, reused across every X→that-language
   path (English's realization is reused across all 9 X→en paths).
   Authored **target-language-first**: the realization owns scenario,
   character names, food, register, and culture — structurally
   identical dialogues across two languages for the same spine node is
   a validation *failure*, not efficiency, because it produces
   translated-feeling content instead of a lesson that actually belongs
   to that language's world.
3. **Source-language overlay** (`docs/content/overlays/<src>-<tgt>/`) —
   one per direction (18 total once complete): explanations, glosses,
   contrastive grammar, interference-error distractors tailored to that
   specific source-language speaker (a Russian learning English needs
   article-error distractors; a Chinese speaker needs tense-mapping
   ones — this is exercise data, not just prose).
4. **Versioned course-release assembly** — `scripts/compile_content.py`
   turns spine + realization(s) + overlay(s) into the JSON the API
   imports, with global content-key uniqueness, cross-file consistency
   checks, and machine-checkable validators (script-purity codepoint
   checks for e.g. Arabic ي/ك vs Persian ی/ک, YAML boolean-coercion
   traps, answer-key sanity). Content keys are stable and independent
   of DB UUIDs.

**Current real coverage** (not aspirational — what's actually authored
and importable today): 6 courses exist as content — en→es (1 unit),
en→fr (1 unit), en→fa (2 units), en→prs (1 unit), fa→en (2 units),
prs→en (2 units, same underlying English realization as fa→en, an
independently-authored Dari overlay). That's roughly 2 of 19 spine
outcomes built, for 4 of 18 paths. This is intentionally still small —
see §5 for why depth-first on fa/prs came before breadth.

## 3. Review methodology (the actual quality-control mechanism)

There is **no native-speaker reviewer network** — this was an accepted
risk tradeoff from the start, replaced by an AI cross-review process:

- **Fresh-context review, mandatory**: every piece of learner-facing
  content is reviewed by a *separate* AI session with zero access to
  the authoring reasoning — a reviewer that saw the generation context
  tends to rubber-stamp it. This has caught real, specific defects
  every single time it's been run this project (not theoretical):
  wrong grammar, a lesson that drifted off its declared learning
  outcome into an unrelated scenario, ambiguous pronoun exercises with
  no grammatical basis, an instruction/answer-key mismatch that would
  mark a correct answer wrong, internal authoring jargon leaking into
  learner-facing text, Dari content that was grammatically distinct
  but structurally templated from the Farsi version (same scenario,
  swapped names) rather than genuinely independently authored.
- **Deterministic validators for everything checkable by code**:
  content-key uniqueness, script-purity, YAML footguns, answer-key
  presence — models only judge what code provably can't.
- **In-app error reporting**: every exercise has a report-an-issue
  button feeding an admin triage queue — the intentional other half of
  the "AI review only" tradeoff, since "fix errors as noticed" requires
  a notice mechanism.

**Division of labor** (followed strictly, confirmed working well this
session): Codex authors all backend code and *all* language content —
Ramin's explicit call, and empirically the right one; Codex has handled
schema migrations, generation-service logic, and every language's
prose competently, with the review pipeline catching drift when it
happened. The executing Claude/Sonnet session owns frontend code,
orchestration of Codex's output (extract → validate → apply), and
end-to-end verification.

**Verification bar, non-negotiable**: compiler validation green;
backend test suite green (28 tests currently, real Postgres via
docker compose, not sqlite/mocked); frontend `npm run build` — the
*full* build, not just `tsc --noEmit` (this has caught real type
errors twice that `--noEmit` alone missed); and live browser
verification with a fresh test account for anything user-facing —
reading a diff is not considered sufficient. This project has a
documented habit of finding real bugs specifically at the live-browser
step that code review missed (a deleted logout button, exercise
components silently never wired to the current design system, a
generation-service distractor bug only visible with a real narrow
just-unlocked vocabulary).

## 4. Technical shape

- **Backend**: Python/FastAPI, SQLAlchemy, Postgres. 7 migrations so
  far, additive-only policy (never delete/reassign exercise UUIDs;
  users are pinned to content releases; seeds are idempotent
  create-missing-only — a destructive delete-and-recreate-on-import bug
  was found and fixed early, since the naive version would have wiped
  user progress on every deploy).
- **Frontend**: React, TypeScript, i18next. Full RTL support for
  fa/prs. Every exercise type renders through one `ExerciseRenderer`
  dispatch, which is why new exercise-shaped features (like the
  practice feed, §6) can reuse it unchanged.
- **TTS**: Google Cloud TTS for live audio synthesis, with a browser
  speechSynthesis fallback. **Real, confirmed gap**: Google Cloud TTS
  has zero Farsi/Dari voices, and most browsers/OSes have none either
  (verified directly this session: one real browser had 199 voices
  across ~50 languages, zero Farsi). This is currently the single
  biggest audio-quality gap for the two highest-priority languages.
  Self-hosted TTS (Piper/XTTS) is the identified fix, not yet built.
  Where a device *does* have a working voice, live synthesis works and
  is presented honestly (a real "no voice available" message replaces
  what used to be a silent dead button).
- **Custom on-screen keyboard** for non-Latin scripts (currently
  Perso-Arabic), since relying on the OS's own keyboard switcher proved
  unreliable in practice; shows on focus, has a "use my own keyboard
  instead" dismiss for when the learner wants their device's native
  input (e.g. for Latin/numeric answers).

## 5. Why fa/prs first, not breadth

This was Ramin's own most personally relevant and self-reviewable
pair, and the phased plan deliberately goes deep on it before fanning
out: Phase 1 (en↔fa) and Phase 2 (en↔prs) exist specifically to prove
the whole pipeline — content architecture, review process, compiler,
generation service — against the two hardest languages in the set
(RTL, non-Latin script, and for Dari specifically zero TTS coverage
anywhere) before replicating the pattern across the easier Latin-script
cohort (es/fr/it/de/nl), then Russian, then Chinese last (heaviest
tooling lift: pinyin/tone-aware audio, IME-aware grading, no
whitespace segmentation).

## 6. New this session: "Endless Practice" — a generative feed, not a generative curriculum

Ramin asked about accelerating content production via AI generation and
free/open-source material, and separately proposed a live-generative
lesson feed. The load-bearing decision made in response, which Fable
should specifically sanity-check:

**Rejected**: generating core lesson content live via an LLM call per
scroll/click. Reason: it would ship completely unreviewed content
straight to beginners who by definition can't self-correct an AI
error — the entire review methodology in §3 exists because of exactly
this risk. It also breaks spaced-repetition (nothing stable to
re-test), breaks trustworthy grading (a live-generated exercise needs a
live-generated answer key, unreviewed), and re-introduces a live
LLM-token cost Ramin explicitly does not want (confirmed: he cannot
have per-use AI token spend in the running app).

**Built instead**: a bounded, **procedural** generation engine.
Codex authors reviewed *sentence-frame templates* (slotted, tagged,
fresh-context reviewed exactly like lesson content) plus a lexeme pool
promoted from each lesson's already-taught vocabulary. At runtime, a
deterministic seeded sampler recombines them — zero LLM calls, zero
per-use token cost, server-authoritative answer keys, so XP can't be
gamed. Eligibility is gated to vocabulary the learner has actually
completed lessons for. Currently piloted on the fa→en course (2
units, 72 reviewed templates, both live and functioning): infinite-
scroll feed, reuses the existing `ExerciseRenderer` unchanged, smaller
diminishing-returns XP so it supplements rather than replaces real
lessons, zero listening cards generated for fa (the TTS gap in §4
applies here too and is respected rather than papered over).

**Free/open material research** (informational, not yet incorporated
into the pipeline): public-domain FSI language courses and the
CC-BY-licensed Tatoeba sentence corpus exist and are usable, but their
value is as *pedagogical reference* fed into Codex's authoring
prompts (proven lesson sequencing, natural example sentences) — not as
directly-imported content, and explicitly not anything from
Duolingo/Babbel, which is proprietary. Not yet built into the actual
authoring workflow; flagged here as a real, low-risk lever if content
velocity becomes the bottleneck again.

## 7. Known real gaps, as of this writing

- TTS has zero Farsi/Dari voice coverage anywhere in the current stack
  (§4) — the single highest-impact unfixed gap for the top-priority
  languages.
- Practice-feature migrations and content exist only in local dev, not
  deployed to the live server yet.
- Only ~2 of 19 spine outcomes are built, for 4 of 18 paths — this is
  a genuinely multi-month build at current velocity; no finish date
  should be inferred from anything in this document.
- No admin UI for content authoring (curl/API-only) — an intentional
  scope trim, not an oversight, given Codex authors via files.
- No native-speaker review network — an accepted, explicit risk
  tradeoff, not a gap anyone is trying to hide.

## 8. Specific questions for Fable

1. Does the procedural-not-generative decision in §6 hold up, or is
   there a bounded generative-content design that preserves the review
   guarantee we're missing?
2. Is depth-first on fa/prs (§5) still the right call given TTS remains
   unsolved for exactly those two languages, or should a Latin-script
   path be pulled forward to get a fully-working (audio included)
   reference path sooner?
3. Any red flags in the free/open-source-material-as-reference idea in
   §6 — licensing, quality, or otherwise — before it's built into the
   actual authoring pipeline?
