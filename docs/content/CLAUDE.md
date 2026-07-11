# Content authoring & review — rules for `docs/content/**`

This file auto-loads when you work under `docs/content/`. It carries ALL
content-authoring and content-review rules. The root `CLAUDE.md` still
governs cross-cutting concerns (git/worktree/agent footguns, division of
labor, the tiered review policy, the verification bar). **`docs/content/
AUTHORING_GUIDE.md` remains binding for all content authoring** (spine
discipline, exercise pacing, dialect authenticity, jargon leaks, YAML
footguns, sibling-file isolation) — this file is the standing-invariant
digest, not a replacement for it.

## Authoring-dispatch requirements

- **Content-authoring dispatches to Codex must always include, up
  front:** the recognition→drag→production pacing rule; and — when
  authoring a source overlay against an existing target realization — the
  STRONG form of the sibling-isolation rule ("treat the sibling-direction
  overlay as if it does not exist, do not open it at all"; "for reference
  only" has failed twice). Point every content task at AUTHORING_GUIDE.md
  + AUTHORING_PROMPT_TEMPLATE.md, and **route every deliverable through a
  SEPARATE fresh-context review task (zero access to the authoring
  reasoning) before import.**
- The tiered review policy (how much review each lane needs, when to
  sample vs. full-review) lives in root `CLAUDE.md` → POLICIES → Tiered
  review. Launch-gate content (en-nl/en-fa/en-prs) stays at full review
  until launch.

## Content sourcing policy

- **Try `firecrawl search`/`firecrawl scrape` for real public-domain
  source material FIRST** (FSI/Peace Corps/DLI or any public-domain
  course for the specific language), before falling back to
  established-conventions-only authoring — strictly better than manual
  `WebFetch`+`pdftotext` PDF-wrangling; this replaces the old default
  research step. A confirmed new source: the DLI Dari Basic Course
  (`fsi-languages.yojik.eu/languages/DLI/Dari/Books/`, cleanly
  text-extractable). Detail: BUILD_LOG 2026-07-09.
- **`FIRECRAWL_API_KEY`: never hardcode, persist to a committed file, or
  embed directly in a shell-command argument** (exposes it in shell
  history/process listings). Safe pattern: `firecrawl login --api-key
  ...` run once by Ramin, after which the CLI reads stored credentials.
  **`.firecrawl/` is gitignored — write scrape output there with `-o`.**
- **Disclose the actual source and its actual license in
  `generation_provenance`** — never one undifferentiated "found real
  material" bucket, whether you found usable content or genuinely nothing.
- **CC-licensed sources are a real but currently-BLOCKED tier**, not a
  live second option. Per AUTHORING_GUIDE §10 (authoritative):
  - **Tatoeba — reference-only in practice.** The CC0 subset is
    effectively empty for launch languages (fa 0, prs 0, nl 50); the
    CC-BY pool needs a learner-facing attribution surface (schema + UI)
    that doesn't exist yet. **Don't re-investigate pool sizes without new
    information.**
  - **Wikibooks / any CC BY-SA source — categorically excluded** until
    Ramin explicitly resolves the share-alike question (a real legal
    call), *before* first use, not after shipping derived content.
  - **University OER / other CC-BY courseware (e.g. COERLL) — usable only
    after a real attribution credit surface exists** (hard precondition
    of first import, per the COERLL Français interactif precedent).
  - See §10 for the categorical-exclusion list (DLI GLOSS/Headstart2,
    OpenSubtitles-derived corpora, Anki shared decks, commercial
    apps/textbooks).

## Content-authoring tooling

- **`docs/content/AUTHORING_PROMPT_TEMPLATE.md`** — fill-in-the-blanks
  Codex dispatch templates with standing rules baked in.
- **`scripts/audio_manifest.py`** — aggregates realization
  `media_assets:` blocks into one recording queue.

## Content footguns (hard-won — do not relearn these)

- **Parallel sessions authoring content collide on unit numbers because
  logs/notes lag real disk state — always `ls
  docs/content/realizations/<lang>/` immediately before claiming a new
  unit number.** Never trust a log/memory/self-report, only the files on
  disk right now. Detail: BUILD_LOG.
- **`compile_content.py`'s `--realization`/`--overlay` are `nargs='+'`,
  not `action='append'`** — the interleaved form silently keeps only the
  LAST value. Correct: all realizations together, all overlays together,
  matched by position (`--realization A B --overlay A B`). Detail: BUILD_LOG.
- **Sweep for internal-jargon leaks after every content round** — bare
  snake_case tokens in `options`/`distractors`/`correct_option`
  (`null_subject`, `both_speakers` shipped for real) and internal words
  like "reviewed" in learner-facing feedback. Grep `docs/content/`
  periodically. Detail: BUILD_LOG.
- **A `listen_select`/`dialogue_response` distractor must never be
  something the tested speaker says ANYWHERE in that audio, full stop** —
  verify this explicitly (not just that it differs from the correct
  answer) when authoring/reviewing multi-turn dialogue-audio exercises. nl
  units 44-50 made 6/15 exercises unanswerable this way. Not yet enforced
  by the compiler (Codex lane) or AUTHORING_GUIDE. Detail: BUILD_LOG 2026-07-09.
- **Never write bare `yes`/`no`/`true`/`false`/`on`/`off` as a YAML
  string value in content fields — PyYAML silently coerces to booleans.
  Always quote (`"Yes"`).** The compiler validates this but has a gap
  (next bullet); don't rely on catching it after. Detail: BUILD_LOG.
- **The compiler's boolean-coercion validator does NOT cover every field
  — `title`/`gloss` on vocabulary teaching items passed clean while
  becoming Python booleans**, caught only by the import API's Pydantic
  schema. Until widened (Codex lane), manually grep/spot-check new content
  for this beyond a green compile. Detail: BUILD_LOG 2026-07-08.
- **`content_key` is unique PER COURSE, never globally** (migration 0015)
  — fa-en/nl-en/prs-en share the same English realization so content_keys
  are identical across them; a global unique index 500s the second
  course's import. Use `PracticeTemplate`'s `UniqueConstraint("course_id",
  "content_key")` pattern for any future content_key-bearing table. Detail: BUILD_LOG 2026-07-07.
- **`compile_content.py`'s tokenizer (`[\w‌]+` regex) doesn't cleanly
  match Devanagari combining vowel signs/virama** — this was FIXED
  2026-07-11 (Codex): the tokenizer now handles matras/virama correctly,
  zero non-Devanagari deltas. The fix surfaced 53 real previously-masked
  token-coverage errors in en-hi-a2/b1 (follow-up dispatched same day).
  (Historical note for any other Devanagari-script authoring: budget extra
  validation-fix iterations if token-coverage errors look spurious.)

Note: the frontend-side answer-shape contract for `matching_pairs` /
`word_order` (how the component submits vs. how content is authored) and
the exercise-type-registration exhaustive check live in
`frontend/CLAUDE.md` — but when authoring those exercise types, be aware
`grade()` canonicalizes multiple authored shapes, so both a space-joined
string and a token list are accepted for `word_order`.

## Seeded courses (state)

**Re-check by `ls docs/content/realizations/<lang>/` before quoting —
grows fast; counts as of 2026-07-08:** en→nl 37 units; en→fa 26 A1/A2 + 1
B1; en→prs 28 A1/A2 + 1 B1; fa-en/nl-en/prs-en share the same English
realization, ~33 units; es/fr 3 units each (A1, parked); de 10 units. New
units are `status: unreviewed` drafts pending mandatory fresh-context
review.

## Known content limitations

- **`backend/tests/test_content_answer_shapes.py`, when run with the
  corpus reachable, shows ~226 known FAILING cases — expected, not a
  regression** (real learner-facing ungradeable exercises: 159 en-hi
  comprehension `correct_response`=Hindi-source bug, ~60 en-nl
  `matching_pairs` missing-right-entry, ~6 phrasing mismatches, 1 en-fa
  `grammar_check`, 1 en-fr `reading_comprehension`). **Do not "fix" this
  by weakening the test** — fix the content (this lane). (How to actually
  run the test — the repo-mount invocation — is in `backend/CLAUDE.md`.)
  Detail: BUILD_LOG 2026-07-10.
- **The spine outcome count moves fast — re-grep
  `docs/content/universal_spine.yaml` before trusting any number.** Grew
  19→24→26→28 across 2026-07-05/06. The English realization (all X→en
  directions) still only covers the first 26 outcomes;
  `banking`/second-`health` aren't realized anywhere yet. 10 of 18 paths
  have zero content; no path is past A2.
- No native-speaker review network in general — nl is the deliberate exception.
- Writing prompts graded by exact string match (Phase C adds distance-1
  typo tolerance, per-language strictness).
- **Fixed 2026-07-05:** `POST /admin/content/import` now appends new
  units to an existing course (diffed by unit `order`) instead of
  skipping the whole course — previously every unit beyond a course's
  seed was validated-on-disk but never live. Detail: BUILD_LOG.
- **Fixed 2026-07-05 (Phase D2):** the full fa course compiles
  end-to-end — the embedded-multi-speaker-label dialogue cards in fa
  units 01/02 were split into one `text_blocks` entry per speaker turn
  (name in `target.speaker`). *Not done:* several single-turn cards (fa
  unit02 misc + units 04/05) still bake the name into `text`; harmless
  to the compiler but a TTS voice reads the name aloud. Detail: BUILD_LOG.
