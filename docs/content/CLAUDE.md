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
- **The shared English realization is consumed by FOUR X→en overlay
  sets: nl-en, fa-en, prs-en AND de-en** — any change to an en
  realization's matching_pairs/exercise shapes must update ALL FOUR
  mirrors (a §16 retrofit missed de-en on 2026-07-12; caught in review
  by the compiler's mirror validator). Grep content_manifest.txt for
  every line referencing the changed en file before committing.
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

- **`backend/tests/test_content_answer_shapes.py`: the corpus is CLEAN
  as of 2026-07-13** — two independent Codex enumerations (en-hi and
  all other courses) found 0 failing answer-shape instances; the old
  "~226 known failing" note reflected pre-2026-07-11 state before the
  mass grading repairs. (Historical class list, for context only (real learner-facing ungradeable exercises: 159 en-hi
  comprehension `correct_response`=Hindi-source bug, ~60 en-nl
  `matching_pairs` missing-right-entry, ~6 phrasing mismatches, 1 en-fa
  `grammar_check`, 1 en-fr `reading_comprehension`). **Do not "fix" this
  by weakening the test** — fix the content (this lane). (How to actually
  run the test — the repo-mount invocation — is in `backend/CLAUDE.md`.)
  Detail: BUILD_LOG 2026-07-10.
- **The spine outcome count moves fast — re-grep
  `docs/content/universal_spine.yaml` before trusting any number.** Grew
  19→24→26→28 across 2026-07-05/06. The English realization (all X→en
  directions) covers ALL spine outcomes as of 2026-07-12
  (a2_unit27_banking + a2_unit28_doctor exist on disk). 10 of 18 paths
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

## Dispatching an authoring task? Paste the pre-flight checklist.

**`docs/content/AUTHORING_PREFLIGHT.md` must be pasted VERBATIM into every
content-authoring dispatch prompt** (not linked — pasted), and the author
must self-report per item before claiming done.

Evidence it works, 2026-07-12: of the bug classes below, the ONE that was
quoted verbatim in that day's dispatch prompts (duplicate/gloss-sharing
matching_pairs lefts) came back with **zero findings in two independent
reviews** — after needing 5 fixes the previous wave. All 23 defects found
that day were classes the prompts did NOT mention, even though every author
had this file auto-loaded and the guide "binding". Authors apply what is in
front of them while writing, not what is merely loaded. This is also the
cheap path: author-side prevention costs a paragraph; reviewer-side
detection cost ~200k tokens per review.

## Bug classes found 2026-07-12 (all slipped a GREEN 0-error compile)

Three fresh-context reviews in one day surfaced these. Validators are being
built for the automatable ones, but AUTHORS must not reproduce them:

- **Underdetermined production prompts.** An instruction satisfiable by
  more than one taught form, graded against ONE exact string, marks correct
  learners wrong. "Write a polite request to move the meeting" after
  teaching four request forms → 3 of 4 correct answers fail. **Name the
  form the prompt wants.** Sub-cases seen: an instruction saying "three
  words" whose accepted answer had five; a prompt whose own feedback
  displayed a DIFFERENT string than the accepted answer.
- **Confusable matching_pairs LEFTs.** The compiler enforces pair COUNT
  (§16) but not DISTINCTNESS. Four mutually interchangeable glosses ("a
  polite way to ask for a change" / "…to ask someone to do something") make
  the exercise unanswerable — the lefts are the learner's ONLY
  discriminator. Every left must discriminate on actual meaning.
  (Duplicate RIGHT values are FINE and intentional — many lefts → one right
  is valid pedagogy; the frontend was fixed 2026-07-12 to support it.)
- **Dialogue cards vs the unit's own AUDIO.** A ru card put Дима's line in
  Настя's mouth (she asked how many rooms were in her own apartment);
  another taught only 3 of the audio's 4 turns, leaving a word untaught
  that a later exercise tested. Enumerate the audio's turns against the
  teaching cards; attribute every line to the speaker who actually says it.
- **Cross-unit character-canon violation.** it unit17 made Sam a teacher;
  unit02 pinned him as an engineer. No validator and no single-file review
  can catch this — **grep the established character profiles before writing
  any new dialogue.**
- **Vocabulary is CUMULATIVE across the course, not unit-local.** An author
  needlessly dropped a valid pair believing "non" was untaught — it had been
  taught since unit12. Conversely, `untaught_vocabulary` only checked
  `tested_text`, NOT `prompt.target_blocks`, so untaught tokens leaked into
  prompts in two separate waves — **hand-check target_blocks** until the
  extended validator lands.

## Per-lane register pins (prevents cross-unit register drift)

- **fa-en overlay lane: colloquial spoken Persian** (می‌شه/می‌کنه/اینجاست
  style, polite شما where addressing the learner) — the norm set by
  units 49-58 and confirmed 2026-07-12 after Codex-authored 59-63
  arrived in formal register and had to be converted. Pin any NEW
  lane's register in the first dispatch prompt and record it here.
- **fa.json UI locale (app chrome): formal written Persian** — distinct
  surface from course-content overlays; normalized 2026-07-12.
- **prs-en overlay lane: colloquial Dari** (می‌تانین/استه style).
- **nl-en overlay lane: informal jij-register.**
