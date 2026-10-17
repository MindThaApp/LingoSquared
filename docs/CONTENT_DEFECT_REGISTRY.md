# Content Defect Registry

Single consolidated registry of every content/code defect class ever found
in this project, across content authoring (`docs/content/**`), the
compiler (`scripts/compile_content.py`), the grading path
(`backend/app/api/router.py`, `backend/app/review/grading.py`), and the
Endless Practice engine (`backend/app/practice/service.py`). Built
2026-07-11 for the tiered review policy adopted the same day
(`CLAUDE.md`, commit `48cea58`) — a coordinator making a per-lane
full/sample/validator-only review-tier call should consult this file
first, not vibes.

**Sources mined**: `CLAUDE.md` (Footguns + phase entries), the full
`docs/BUILD_LOG.md` (10,426 lines, 2026-07-02 through 2026-07-10),
`docs/content/AUTHORING_GUIDE.md` (20 numbered rules, each traceable to
an incident), `review:`/`notes:` blocks across
`docs/content/{realizations,overlays,practice}/**/*.yaml`, and
`git log --oneline` on `master` (771 commits, ~149 fix/bug-named) with
`git show`/`git log -1 --format=%B` follow-up on ambiguous ones.

---

## Section 1: Bug-class catalog

Each entry: name; description; first found; instances/languages hit;
root cause; learner impact; prevention status; how to avoid.

### 1.1 First-listed-only multi-answer grading
**Description**: `canonical_response()` only ever compiled the FIRST
`accepted_answers` variant; `grade()` did single-value equality — every
accepted-answer list across fa/prs/es only accepted the first-listed
spelling variant.
**First found**: 2026-07-04, `docs/BUILD_LOG.md` line ~202 ("CRITICAL
FIX: multi-answer grading").
**Instances**: systemic, every multi-variant exercise authored before
the fix (fa/prs/es content of that date).
**Root cause**: compiler compiled a single value; backend had no
membership-check concept.
**Learner impact**: correct answers other than the first-listed variant
graded wrong.
**Prevention status**: AUTOMATED — `correct_response` now compiles to
`{"canonical", "accepted"}`; `backend/tests/test_multi_answer_grading.py`
+ `scripts/tests/test_compile_content.py` cover it.
**Avoid**: none needed — mechanism-level fix, not an authoring
discipline.

### 1.2 Multi-speaker dialogue blob breaks TTS ("choking" audio)
**Description**: dialogue teaching cards stored a whole exchange as one
`text_block` with embedded `"Name: ..."` labels and literal newlines;
TTS read speaker names aloud and stumbled on the raw newline.
**First found**: 2026-07-04 (Ramin's own hands-on testing),
`docs/BUILD_LOG.md` ~line 250.
**Instances**: every dialogue card authored before Phase D2/D3
(2026-07-05); confirmed residual instances in fa unit02
(arrival/meet_mina/sara_name/ask_origin/pleased/pleased_and_enter) and
all of fa units 04/05 — single-turn so they don't trip the validator,
just read the name aloud.
**Root cause**: dialogue authored as one blob instead of one
`text_blocks` entry per speaker turn.
**Prevention status**: AUTOMATED for NEW cards — compiler now rejects
new dialogue cards using the old anti-pattern (Phase D2/D3,
2026-07-05). UNPREVENTED for existing pre-Phase-D2 cards not yet
migrated (the fa unit02/04/05 residual, `CLAUDE.md` "Known
limitations" closing paragraph) — compiler validator only blocks
new/edited cards, doesn't retroactively flag old ones.
**Avoid**: always author dialogue as one `text_blocks` entry per turn
with `target.speaker` set, never bake the name into `text`.

### 1.3 `listen_select`/`listen_type`/`listen_order` had no audio at all
**Description**: `media_asset_key` was compiled but never referenced by
the frontend — listening exercises showed an instruction with nothing
to play.
**First found**: 2026-07-04, root cause of Ramin's "exercise 1 is
impossible" report.
**Instances**: every listening exercise, every shipped language, at
that date.
**Prevention status**: AUTOMATED — compiler stamps `audio_text`/
`audio_language_code`, frontend renders a "Tap to listen" `SpeakButton`
wired to live `/tts`.
**Avoid**: n/a, mechanism fix.

### 1.4 Exercise types shipped in content but never registered in the frontend
**Description**: `speak_response`, `listen_order`,
`dialogue_comprehension`, `speak_repeat`, `listen_select`, `listen_type`
— six types valid in the backend enum and used in shipped content but
absent from `ExerciseRenderer.tsx`'s switch, crashing the whole lesson
with "Unsupported exercise type."
**First found**: 2026-07-04, found by doing an exhaustive `comm` diff
after tripping over the 2nd and 3rd instance one at a time.
**Prevention status**: GUIDE-RULE / PROMPT-BAKED — CLAUDE.md footgun:
"Exercise-type registration must be checked exhaustively... after any
content or exercise-type change." No compiler-level or CI-level
automated check exists (UNPREVENTED at the tooling layer — this is a
manual-discipline rule, not a validator).
**Avoid**: `comm` diff every `type:` in `docs/content/realizations/`
against every `case` in `ExerciseRenderer.tsx` after any exercise-type
or content-type change.

### 1.5 Internal-jargon / snake_case tokens leaking into learner-facing text
**Description**: `null_subject`, `both_speakers`, `neither_speaker` and
similar internal tags shipped verbatim as `options`/`distractors`/
`correct_option` text.
**First found**: 2026-07-04 (Dari content), recurred 2026-07-04
(en-fa/en-prs unit01/02 dialogue-comprehension) and again as a
full-corpus sweep, commit `5da3874` ("Fix 12 internal-jargon leaks").
**Instances**: at least 3 documented rounds, ≥15 total instances across
en-fa/en-prs/Dari.
**Root cause**: authoring pattern reused across files copies internal
bookkeeping tags into learner-visible fields.
**Prevention status**: GUIDE-RULE (`AUTHORING_GUIDE.md` §4) +
PROMPT-BAKED sweep instruction in CLAUDE.md footguns ("grep
`docs/content/` periodically"). UNPREVENTED by any automated
validator — no compiler check exists for bare snake_case in
learner-facing fields.
**Avoid**: grep `docs/content/` for bare snake_case tokens in
`options`/`distractors`/`correct_option` after every content round.

### 1.6 `dialogue_response` built as multiple-choice but content is free-text
**Description**: component always had an empty `options` array in
practice (every shipped `dialogue_response` compiles to a free-text
`{canonical, accepted}` reply), so the "Respond" button stayed
permanently disabled.
**First found**: 2026-07-04, live browser playthrough.
**Prevention status**: AUTOMATED — rewritten to match `Translation.tsx`'s
free-text pattern. No recurrence risk (component-level fix).

### 1.7 `matching_pairs` answer-shape mismatch (frontend/backend/practice-engine)
**Description**: three independent instances of dict-vs-list shape
mismatch: (a) `MatchingPairs.tsx` submitted a flat `Record<left,right>`
while all hand-authored `accepted_answers` are `{left,right}[]`; (b)
`grade()`'s generic fallback had no shape canonicalization; (c) the
Endless Practice engine's `derive_answer()` independently produces a
FLAT dict for the same exercise type, rendered through the same
component/grade path.
**First found**: 2026-07-05, live claude-in-chrome walkthrough
(`73dae0d`, `9c42e9f`, `28048ed`, and the backend half in a second
concurrent session).
**Instances**: every `matching_pairs` exercise in every course, both
lesson-authored and Endless-Practice-generated, at that date.
**Learner impact**: every matching_pairs exercise graded "Not quite"
regardless of correctness; wrong-answer hint rendered literal
`[object Object],[object Object]`.
**Prevention status**: AUTOMATED — `canonical_pairs()` in
`app/api/router.py` canonicalizes either shape into an
order-independent frozenset; `frontend/src/lib/formatAnswer.ts`
centralizes display; `backend/tests/test_matching_pairs_grading.py`
covers both shapes.
**Avoid**: whenever an exercise component's answer payload isn't
string/string[], verify what `accepted_answers` actually looks like in
real content AND what the Endless Practice engine independently
produces — don't infer the contract from one side only (this is the
general lesson CLAUDE.md draws from this incident).

### 1.8 `matching_pairs` content bug: overlay `left` text translated/mismatched vs. rendered `prompt.pairs`
**Description**: distinct from 1.7 (a shape bug) — this is a *content*
bug: the overlay's `accepted_answers[].left` was translated into the
source language (or otherwise didn't match) while the realization's
`prompt.pairs` (what the frontend actually renders and the learner
clicks) stayed in the displayed language, so `canonical_pairs()`
correctly canonicalizes shape but the sets never matched regardless of
learner input.
**First found**: systemically via `backend/tests/
test_content_answer_shapes.py` (added 2026-07-10) — 94 instances fixed
in one pass (`44765aa`), further instances found and fixed by
fresh-context reviews across nl-en units 25/31/38-58 and a2/25-27
(`c8ce1ae`, `d2ccb5e`, `476acc9`, `4d64abc`, `f9a912a`).
**Instances**: ≥94 confirmed fixed (nl-en/fa-en/prs-en X-en overlays,
en-nl overlays keying only a subset of displayed pairs, one YAML
boolean-coercion variant in en-fa b1 unit05); concentrated in the
X-en directions since they share the underlying English realization.
**Source conflict**: `CLAUDE.md`'s "Known limitations" section
(written 2026-07-10, before `44765aa` and the nl-en fresh-context
reviews) states "~60 matching_pairs... ~6 more matching_pairs phrasing
mismatches" as still-open — that count is now STALE; `44765aa` alone
fixed 92 matching_pairs instances of the same class. **Re-run
`test_content_answer_shapes.py` against the full corpus before trusting
either count** — this registry cannot assert the current true-zero
state without that live re-run.
**Root cause**: overlay authoring reflexively translates every field
including `left`, without checking it must mirror what the realization
actually displays.
**Prevention status**: AUTOMATED detection (`test_content_answer_shapes.py`,
corpus-wide, ~12,627 parametrized cases) but NOT compiler-blocking —
the compiler's own `validate`/`compile` passes clean regardless. Fixes
are review-driven, not automatic. Effectively GUIDE-RULE (§16 density
guidance references correctness) + AUTOMATED-DETECTION-ONLY.
**Avoid**: overlay `accepted_answers` for `matching_pairs` must mirror
the realization's `prompt.pairs` verbatim on the `left` side (the
rendered text), never translate it.

### 1.9 `word_order`/`listen_order` string-vs-list shape mismatch (~84% of corpus)
**Description**: `WordOrder.tsx` always submits a list (tile-click
order); `canonical_response()` passes hand-authored `accepted_answers`
through unchanged, and 146/173 (~84%) of all word_order/listen_order
exercises corpus-wide are authored as a plain space-joined STRING.
`normalized()` returns a list for list input, a string for string
input — never equal regardless of tile order.
**First found**: 2026-07-07, real user report ("Hallo, met Omar" tiles
clicked in correct order still graded wrong), commit `ada1cdc`.
**Instances**: 146 of 173 word_order/listen_order exercises
corpus-wide at that date (an earlier 2026-07-06 investigation of the
same symptom concluded "could not reproduce" because it happened to
test one of the 24 already-working list-shaped exercises).
**Prevention status**: AUTOMATED — new `canonical_order_tokens()`
canonicalizes either shape before comparing.
**Avoid**: n/a going forward, mechanism fix; general lesson — check
grading against every shape `accepted_answers` is actually authored in
across the real corpus, not one example.

### 1.10 `word_order`/`listen_order` `accepted_answers` authored in scrambled (not sentence) order
**Description**: distinct from 1.9 — even where the list SHAPE is
correct, `accepted_answers` was sometimes authored in the same
scrambled order as the display `word_bank` instead of correct sentence
order. `word_order` grading is order-sensitive; the compiler only
checks the accepted tokens form the same MULTISET as `word_bank` (not
order), so this passes `validate`/`compile` clean.
**First found**: fresh-context review of en A2 units 30-34 + fa-en
overlays, commit `1bb596e` — 15 instances (3/unit across 5 units), all
graded wrong regardless of what the learner clicked.
**Prevention status**: UNPREVENTED at the compiler level — the
compiler's multiset check cannot distinguish this from a correct
answer; only caught by human fresh-context review or a corpus-wide
answer-execution test (not yet built for this specific ordering
check). Flag prominently — see Section 3.
**Avoid**: when authoring `accepted_answers` for word_order/listen_order,
always write the tokens in correct grammatical sentence order, never
copy the scrambled `word_bank` order.

### 1.11 RTL word-order tile assembly rendered left-to-right regardless of script
**Description**: `word_bank`/`pairs` tokens are plain arrays with no
per-item direction; `WordOrder.tsx`'s render container had no explicit
`dir` and didn't inherit direction from anywhere, so Farsi/Dari tiles
assembled visually LTR even though the underlying `chosen` click-order
array (and grading) was always correct.
**First found**: 2026-07-09, live Ramin report.
**Prevention status**: AUTOMATED for this component — new
`answerDirectionForExercise()` helper applies `dir` to both word-bank
and answer-row containers. GUIDE-RULE (documented as a general lesson
for any FUTURE sequence-assembly UI): any new component rendering a
sequence of independently-clickable raw tokens needs an explicit `dir`
prop — not automatically checked for components not yet built.
**Avoid**: for any new tile/letter-bank UI, explicitly check/set `dir`
before shipping; don't assume the browser handles it.

### 1.12 YAML boolean coercion (`yes`/`no`/`true`/`false` unquoted)
**Description**: PyYAML silently coerces bare `yes`/`no`/`true`/`false`/
`on`/`off` to booleans.
**First found**: recurring — fa unit20 `right: yes` (`4f776bb`), prs B1
`title: Yes`/`gloss: yes` on vocabulary teaching items (`58a1248`),
also surfaced inside the 94-instance matching_pairs fix (`44765aa`).
**Instances**: ≥3 confirmed distinct instances across fa/prs, likely
undercounted (this class only surfaces when something downstream
chokes on the wrong type).
**Root cause**: compiler's boolean-coercion validator has a confirmed
gap — passes `compile_content.py` with 0 errors on `title`/`gloss`
fields of vocabulary teaching items specifically (found 2026-07-08),
then only caught later by the stricter Pydantic import schema or a
runtime grading failure.
**Prevention status**: PARTIALLY AUTOMATED — compiler validates some
fields; UNPREVENTED for the title/gloss-on-vocabulary-teaching-item gap
specifically (`CLAUDE.md` Footguns, explicit: "treat this as still
needing a manual grep/spot-check... not just a green compile_content.py
run"). See Section 3.
**Avoid**: always quote `"Yes"`/`"No"` etc. as YAML string values;
don't trust a green compiler run alone for title/gloss fields.

### 1.13 `content_key` uniqueness scoped globally instead of per-course
**Description**: fa-en/nl-en/prs-en all realize the same underlying
English content, so their `content_key` values are identical by
construction — a global unique DB index made the second course's
import 500 on collision.
**First found**: 2026-07-07, real `IntegrityError` importing nl-en into
a DB that already had prs-en.
**Prevention status**: AUTOMATED — migration `0015` rescoped the index
to `(course_id, content_key)`, matching `PracticeTemplate`'s existing
pattern. Standing rule in CLAUDE.md Footguns for any future
content_key-bearing table.

### 1.14 Endless Practice self-reference (word is both fixed anchor text and its own fillable candidate)
**Description**: a frame's literal text collides with one of its own
slot's real candidate values (e.g. "It's the [ordinal] of April" where
"april" was itself tagged as a candidate `ordinal_number`, producing
"Het is de april april").
**First found**: multiple instances across sessions — nl-en unit07
"sandwich", en-nl unit07 "market_quantity"/produce-quantity confusion,
"april"/`ordinal_number` (`6636194`).
**Prevention status**: AUTOMATED — `scripts/_practice_content_integrity_check.py`
(2026-07-07) reproduces the real `render_frame()`/`build_prompt()`
logic and checks all 157 practice files corpus-wide. Corpus-wide sweep
found 0 NEW instances beyond the already-known 2 as of 2026-07-06, and
1 more (en-prs a1_unit15, a dead-anchor variant not self-reference) on
2026-07-07 — the checker itself is a durable tool, kept as a permanent
validator.
**Avoid**: n/a going forward for checked packs; run the checker after
any new practice-pack authoring round.

### 1.15 Endless Practice dead anchor (template's `lesson_content_key` resolves to a lesson introducing zero vocabulary)
**Description**: a practice template anchored to a pure reading/review
lesson with `introduced_tokens` summing to zero can never actually
resolve at runtime.
**First found**: fa-en unit23 (ad hoc catch during authoring), then
en-prs a1_unit15 `person_name_pair.001` via the dedicated
`_practice_content_integrity_check.py` sweep, 2026-07-07.
**Prevention status**: AUTOMATED — same checker as 1.14, both bug
classes covered by one tool, run corpus-wide (157 files/2056
templates) 0/1 found respectively.

### 1.16 `fill_in_blank` ambiguous open-vocabulary slot (no disambiguating context)
**Description**: an open-vocabulary slot (colors, names, weekdays,
occupations...) embedded in a fixed-text frame with no other anchor is
structurally unable to tell the learner which pool member is correct,
because `_material()` scopes the candidate pool to every lexeme from
every completed lesson, not just the template's own anchor lesson.
**First found**: 2026-07-06, corpus-wide audit
(`scripts/_fill_in_blank_ambiguity_check.py`) triggered by a live
en-nl user report of an unanswerable exercise.
**Instances**: 251 single-slot templates flagged out of 276 total
fill_in_blank templates project-wide (en-fa 17, fa-en 52, en-prs 29,
prs-en 52, en-nl 47, nl-en 54), plus 6 multi-slot templates needing
human read. 229/251 had a safe sibling exercise already covering the
vocabulary (mechanical-removal-safe); 22 had no sibling (need real
authoring). 43 fixed same night in untouched files; remainder deferred
to lanes under active concurrent edit at audit time — **status of the
remaining ~180 as of this writing is not independently re-verified by
this registry**; a follow-up sweep in `c963e03`/`5c0b527` closed at
least the en-prs `condition_word` instance.
**Prevention status**: AUTOMATED DETECTION
(`_fill_in_blank_ambiguity_check.py`, permanent tool,
`AUTHORING_GUIDE.md` §17 references it) but fixes are manual/review-
driven per instance, not auto-applied except the mechanical-removal
subset.
**Avoid**: run `_fill_in_blank_ambiguity_check.py` after authoring any
new fill_in_blank template; if flagged with no sibling, either add
real disambiguating context or narrow the pool.

### 1.17 `fill_in_blank` true-synonym slot pools (all pool members equally correct)
**Description**: narrower than 1.16 — real surrounding context DOES
survive masking, but every candidate in the slot's pool is a true
register/stress synonym of the others (je/jij, alsjeblieft/alstublieft,
mijn/je/jouw) with nothing in the frame able to prefer one; only ONE
was ever marked correct by the sampler.
**First found**: 2026-07-06, same audit as 1.16, 4 confirmed instances
(en-nl unit01/05/06).
**Prevention status**: AUTOMATED mechanism (opt-in
`interchangeable: true` flag on `answer_derivation`, computes every
still-matching lexeme into a multi-answer `{canonical, accepted}`
shape) + GUIDE-RULE `AUTHORING_GUIDE.md` §17. Detection is via the same
`_fill_in_blank_ambiguity_check.py` tool as 1.16, but distinguishing
"true synonym, use `interchangeable: true`" from "different word, needs
real narrowing" (1.16) is a HUMAN judgment call, not automated.
**Avoid**: when a flagged slot's candidates are true synonyms with no
possible disambiguation, use `interchangeable: true` rather than
picking one arbitrarily as correct.

### 1.18 Cross-course-level (A1/A2) candidate-pool reuse breaks candidate-floor exercise types
**Description**: `multiple_choice`/`listen_select` need ≥3 distinct
candidates; reusing an already-classified tag across the A1/A2 course
boundary (two separately-scoped `Course` rows at runtime) silently
undercounts real candidates for the new course level, since the
classification list is combined across both levels but runtime scoping
is per-course.
**First found**: 2026-07-07, dedicated audit after a methodology
concern was raised about the "tag-reuse depth technique."
**Instances**: 25 real violations across 9 files (nl-en a2_unit25/26,
fa-en/prs-en a2_unit25-28 — mirrored since they share underlying
English content).
**Prevention status**: GUIDE-RULE (`AUTHORING_GUIDE.md` §18, added
2026-07-07) — no automated per-authoring-time check exists; the audit
script (`_practice_slot_check.py` extended with the `level` filter) is
a detection tool, must be run manually, not wired into
`compile_content.py`'s own validate/compile path.
**Avoid**: filter `iter_specs()`'s own `level` field before deciding to
use `multiple_choice`/`listen_select` across a course-level boundary;
`word_order`/`translation` have no candidate floor and are always safe.

### 1.19 `matching_pairs` needs real scale (a handful to a dozen pairs, not 2-3)
**Description**: guide rule (§16) — thin matching_pairs pools make the
exercise trivial/guessable.
**First found**: established as a rule after repeated review findings;
concrete violation counts: 29 §16 violations found across the shared
English A1/A2 realization (`5d412a2` fixed 23/29, follow-up commits
closed the rest), plus 9 unplayable zero-pairs matching_pairs
exercises found separately (`194b3a2`).
**Prevention status**: GUIDE-RULE (`AUTHORING_GUIDE.md` §16). No
automated validator enforces a minimum pair count at compile time —
UNPREVENTED at the tooling layer.

### 1.20 Wrong/contradictory `media_asset_key` (audio references a different clip than the exercise tests)
**Description**: an exercise's `media_asset_key` pointed at a
completely different lesson's audio clip, or a bare vocabulary word
list instead of the sentence actually being tested.
**First found**: 2026-07-06, cross-language content-integrity sweep,
bug class 3 of 5. 2 real instances found and fixed (nl unit22, en
unit21) via a purpose-built comparison script; ~30 other candidates
were false positives after refining to word-level comparison.
**Prevention status**: UNPREVENTED as a standing automated check — the
comparison script used was ad hoc for that one sweep, not integrated
as a permanent validator (`_practice_content_integrity_check.py` and
siblings don't cover this class). See Section 3.
**Avoid**: when authoring/reviewing any exercise with `media_asset_key`,
confirm the referenced clip's declared transcript actually contains
the `tested_text`, not just that a key exists.

### 1.21 `accepted_answers` missing natural multi-clause phrasing variants
**Description**: a natural sentence has multiple valid punctuation/
conjunction joins (e.g. "[reply]. And you?" vs. "[reply], and you?")
but only one was authored.
**First found**: 2026-07-06, cross-language sweep, bug class 4 of 5 —
~28 candidates found by script, 9 highest-confidence fixed same night
(fa-en/prs-en/nl-en/en-fr/en-es unit01, en-nl unit09/10/12/13).
**Prevention status**: GUIDE-RULE (`AUTHORING_GUIDE.md` §12). No
automated validator — detection was a one-off script, not a permanent
tool. ~19 lower-confidence candidates (mostly open-ended prompts) left
untriaged.
**Avoid**: when authoring a tag-question or multi-clause reply pattern,
author every natural punctuation/conjunction join as a listed variant,
not just one.

### 1.22 `listen_select` distractor is something the tested speaker actually says elsewhere in the same dialogue audio
**Description**: a listening distractor drawn from another line of the
same multi-turn dialogue audio, spoken by the SAME tested speaker,
makes both options technically correct — genuinely unanswerable
regardless of what the learner picks.
**First found**: regression confirmed 2026-07-09 (a 2026-07-0x audit
had already fixed this once, class regressed under overnight-pace
authoring). nl units 44-50: 6 of 15 such exercises (40%) were
unanswerable; commit `148240e` fixed those 6; 3 more borderline
"assembled from separate turns" cases in nl unit42/49/50 lesson04 left
as defensible-but-fragile. Also found: 29 more unanswerable
`listen_select` + 1 truncated `listen_order` answer (`8a0b948`, "Fable
plan W6"), and 17 more unanswerable `dialogue_comprehension` in
en-de/de-en (`f622d7f`).
**Instances**: ≥52 confirmed fixed across multiple rounds; this is a
CONFIRMED-RECURRING class, not a one-off.
**Prevention status**: UNPREVENTED — explicitly flagged in CLAUDE.md
Footguns as "not yet enforced by the compiler... or the authoring
guide." **This is a top-priority automation gap** (Section 3).
**Avoid**: a listening distractor must be something NOT said by the
tested speaker anywhere in that audio, full stop — verify explicitly
when authoring/reviewing any `listen_select`/`dialogue_response` built
from multi-turn dialogue audio.

### 1.23 Apostrophe-elision defeats the compiler's untaught-vocabulary tokenizer (validator-gaming risk)
**Description**: `TOKEN_RE = [\w‌]+` splits on apostrophes ("J'ai" →
`{"j","ai"}`), and `validate_untaught_vocabulary` resets its `taught`
set per (realization, overlay) file pair, not across units — so a
genuinely-required elided subject like "J'" can appear "untaught" even
when correctly used, tempting an author to delete it from the answer
(making the sentence ungrammatical) rather than declare it taught.
**First found**: 2026-07-06, French unit03 — exactly this: "J'ai deux
sœurs" had its "J'" deleted from `word_bank`/`correct_response`
entirely, leaving the ungrammatical "ai deux sœurs" as the only correct
answer.
**Instances**: 1 real user-facing instance (fr unit03) + 13 cosmetic-
only instances (dropped "J'" in internal `tested_text` only, not in
learner-facing fields) across fr unit02/03. No other language showed
this exact apostrophe-elision failure mode in the same sweep.
**Prevention status**: UNPREVENTED at the tokenizer level — the
compiler's tokenizer gap itself was not fixed, only the one real
instance's content. Related to 1.24 (Devanagari) — same tokenizer
class of bug, different scripts.
**Avoid**: never delete a token to make an "untaught vocabulary" error
go away — add it to `introduced_tokens` instead, and check whether the
apparent gap is a real teaching gap or a tokenizer artifact.

### 1.24 Devanagari tokenizer fragmentation (compiler doesn't cleanly match combining vowel signs/virama)
**Description**: `[\w‌]+` can fragment a Devanagari word into a shorter
substring (e.g. "नया" → "नय"), applied lossily to both
`introduced_tokens` and `tested_text` — an infinitive doesn't
automatically cover its own inflected surface forms, and "already
taught" status doesn't reliably carry across files.
**First found**: 2026-07-10, authoring Hindi A2 content.
**Prevention status**: UNPREVENTED — explicitly flagged in CLAUDE.md
"Known limitations," Codex's lane
(`scripts/compile_content.py`), not yet fixed. Same tokenizer bug
family as 1.23.
**Avoid**: budget extra validation-fix iterations for Hindi/Devanagari
content; explicitly re-declare tested surface forms rather than assume
coverage carries over.

### 1.25 Case-sensitivity never modeled in grading (German Sie/sie)
**Description**: `normalized()`/`_normalize()` unconditionally
`.casefold()`s every string; German's formal "Sie" vs. lowercase "sie"
("she"/"they") is a real grammatical distinction with no equivalent in
nl/en/fa/prs content, making it ungradeable under always-casefold
comparison.
**First found**: 2026-07-07, the content lane authoring German
correctly deferred teaching this contrast rather than ship an
ungradeable exercise, and flagged it.
**Prevention status**: AUTOMATED for hand-authored `Exercise`s — new
`case_sensitive: bool` flag (sibling of `orthography_strict`), hard-
blocks a case-only mismatch to `incorrect` rather than letting it fall
into the distance-1 "almost" typo-tolerance path. NOT wired into
Endless Practice's generated `PracticeItem`s — `PracticeTemplate` rows
have no per-template metadata slot analogous to `Exercise.feedback`,
and no German Endless Practice content exists yet. Gap is
acknowledged/scoped-out, not accidental — still UNPREVENTED for any
future German (or other case-sensitive-grammar language) Endless
Practice content.
**Avoid**: for any future case-sensitive grammatical distinction in
Endless Practice content, a new mechanism will be needed first — flag
before authoring, don't assume the Exercise-level flag covers it.

### 1.26 Corpus-wide answer-shape regression test: 227 pre-existing content bugs found in one sweep
**Description**: `backend/tests/test_content_answer_shapes.py` (added
2026-07-10) grades every compiled exercise in the real corpus through
the actual `grade()` path with the exact payload shape the real
frontend component submits — a meta-finding: this class of bug
(shape/answerability mismatches) had never been checked exhaustively
before.
**Findings breakdown** (as first measured, 2026-07-10; **see 1.8's
staleness note — 94+ of the matching_pairs subset were already fixed
by `44765aa` and later fresh-context reviews; the en-hi figure below is
NOT independently confirmed still-open by this registry**):
- **159 in en-hi** — see 1.27, a single systemic bug, hi units 3-19.
- **~60 `matching_pairs`** missing correct_response entries
  (concentrated en-nl units 2-10/22/23, duplicated once each across
  nl-en/fa-en/prs-en units 30-58) — subset of 1.8.
- **~6 more `matching_pairs`** phrasing mismatches — subset of 1.8.
- **1 `en-fa` `grammar_check`** submitting a plain string against a
  multi-answer-shaped `correct_response`.
- **1 `en-fr` `reading_comprehension`** with no `prompt.options` at all
  (unrenderable).
**Prevention status**: AUTOMATED DETECTION (the test itself, permanent,
~12,627 parametrized cases) but requires the full-repo Docker mount
(`LINGO_REPO_ROOT=/repo`) to actually run — self-skips as "1 skipped"
under the standard invocation, a real footgun of its own (documented in
CLAUDE.md "Known limitations"). Fixing found instances is manual/
review-driven, the test explicitly must NOT be weakened to pass.
**Avoid**: run this test with the full repo mounted before trusting any
"clean corpus" claim; do not fix by touching the test's own logic.

### 1.27 en-hi comprehension exercises: `correct_response` is the Hindi source text while `prompt.options` are English glosses
**Description**: one systemic authoring bug across all of hi units
3-19 — every comprehension exercise's answer key is set to the Hindi
text itself while the choosable options shown to the learner are
English glosses, so nothing can ever match.
**First found**: via 1.26's corpus-wide test, 2026-07-10.
**Instances**: 159 exercises, hi units 3-19 (the entire early Hindi
comprehension-exercise population at that date).
**Prevention status**: UNPREVENTED / open as of the last confirmed
check — explicitly flagged "needs a real content-authoring fix, not
code." **This registry could not confirm current status** — hi content
has grown since (units up to 31 exist on disk now) and later
fresh-context reviews touched hi B1 units 01-06 (`b72166f`, 2 bugs
fixed) but NOT the A1/A2 systemic en-hi issue by name. Treat as
OPEN until `test_content_answer_shapes.py` is re-run against current
hi content.
**Avoid**: n/a — content fix needed, not an authoring-discipline rule
yet (hi is not yet mature enough to have converged on a fix pattern).

### 1.28 Dari (prs) 2pl verb-ending dialect split-brain (Iranian `-ید` vs Afghan `-ین`)
**Description**: the prs course's own `register_policy` establishes
the Afghan استم/استین paradigm (2pl `-ین`) and the copula was
uniformly Afghan, but lexical 2pl verbs split by unit — some correctly
Afghan, others Iranian `-ید` inside otherwise-authentic Afghan
vocabulary, mixing two dialects within one register.
**First found**: 2026-07-07, Opus fa/prs corpus audit.
**Instances**: ~756 replacements across 37 files (16 prs realizations,
11 en-prs overlays, 3 prs-en overlays, 10 practice packs, plus the
backfill script) — a genuinely project-wide dialect-consistency bug.
**Prevention status**: GUIDE-RULE (a Fable dialect ruling now
documented as project history/precedent) but NO automated dialect-
consistency checker exists — UNPREVENTED at the tooling layer. Purely
relies on native/Fable review to catch a recurrence.
**Avoid**: when authoring any new Dari content, cross-check verb
endings against the unit's own declared `register_policy` for
internal consistency, not just correctness in isolation.

### 1.29 Homograph / polysemy collision in the lexeme classifier
**Description**: a single token with multiple senses (تو = pronoun
"you" vs. preposition "in/inside"; و = conjunction vs. other reading)
gets one flat classifier entry, causing the wrong sense's tags/gloss to
leak into unrelated exercises.
**First found**: recurring — تو/pronoun-vs-preposition (`b7543aa`),
و/می‌شود/کی precedent pattern cited as the established fix shape.
**Prevention status**: GUIDE-RULE / per-instance fix pattern
(`(level, token, sense)`-scoped classifier entries) established and
reused successfully across languages, but NO automated homograph
detector exists — each new homograph is still found by a human noticing
a wrong gloss/tag leak. UNPREVENTED as a class.
**Avoid**: when adding a new sense of an already-classified token,
scope the classifier entry by `(level, token, sense)`, never overwrite
the existing flat entry.

### 1.30 Farsi/Dari harakat (diacritic) grading trap
**Description**: fa/prs grade strict (no distance-1 typo tolerance,
per the Arabic/Persian script-confusion carve-out) and normalization
does not strip harakat (short-vowel diacritics) — a learner typing the
natural undiacritized form of a word authored WITH harakat (e.g. کِی
vs. plain کی) is marked wrong even though undiacritized typing is how
real users normally type Persian/Dari.
**First found**: fresh-context review of fa B1 units 07-11 (`e71ebe5`),
2026-07-07.
**Instances**: 3 typed-answer exercises in fa B1 unit11 (not the
matching word_order tile exercise, which doesn't have this failure
mode).
**Prevention status**: GUIDE-RULE (add an undiacritized accepted
variant whenever a diacritic-bearing form is the canonical answer) — no
automated check exists. UNPREVENTED at the tooling layer.
**Avoid**: whenever authoring a fa/prs typed-answer exercise whose
canonical answer includes harakat, add the undiacritized form as an
explicit accepted variant.

### 1.31 Admin content import silently skipped appending new units to an already-existing course
**Description**: `POST /admin/content/import` dedup logic only ever
created brand-new courses, skipping any course that already existed by
`(source_language, target_language, title)` rather than appending new
units — every unit authored beyond a course's initial seed was stuck
validated-on-disk but never live.
**First found**: 2026-07-05, trying to get new fa units 3/4/5 live.
**Prevention status**: AUTOMATED — fixed to diff incoming units against
existing unit `order`s and append only new ones (`5b95345`); backend
code fix, not a content-authoring discipline.

### 1.32 Checkpoint retake-lock and practice-anchor bugs (backend, Farsi live QA)
**Description**: two backend bugs found on a genuinely fresh, isolated
en-fa/fa-en stack: a checkpoint retake-lock misbehavior and an fa-en
practice-anchor bug.
**First found**: 2026-07-06, live QA pass on Farsi (`82ca9d0`).
**Prevention status**: AUTOMATED — fixed same session, covered by the
live-QA methodology (fresh isolated stack), not a recurring content
class per se. Included here because the SAME live-QA methodology is
what future per-direction full-review-tier decisions should replicate.

### 1.33 Frontend pages silently masking fetch errors as success/empty states
**Description**: six pages treated a failed fetch identically to a
genuinely-empty result, showing misleading "all done"/success UI
instead of an error state.
**First found**: `b3c0d29` "Fix six pages silently masking fetch errors
as success/empty states"; a narrower instance (`ReviewPage`) fixed
separately in `960eabe`.
**Prevention status**: AUTOMATED (fixed) but no linter/pattern-check
prevents a NEW page from reintroducing this shape — UNPREVENTED as a
class for future pages.
**Avoid**: any new data-fetching page must distinguish "fetch failed"
from "fetch succeeded, empty result" in its rendered state.

### 1.34 WCAG AA contrast failures (design-system color tokens)
**Description**: several UI states (`.btn-danger` dark mode, feedback-
banner, stat color tokens) failed WCAG AA contrast.
**First found**: multiple commits (`c799507`, `47fcff9`, `a12b276`).
**Prevention status**: AUTOMATED (fixed via new tokens, e.g.
`--incorrect-contrast`) but no automated contrast-check runs in CI —
UNPREVENTED as a recurring class for new color tokens.

### 1.35 Guest-account data loss
**Description**: a real data-loss bug for guest accounts, fixed
alongside a react-query `staleTime` tuning.
**First found**: `77c919e`.
**Prevention status**: AUTOMATED (fixed); no dedicated regression test
named in the commit message — verify test coverage exists before
treating this as durably closed.

### 1.36 nl-en overlay "Dutch-left" systemic bug (source-language text left untranslated/unswapped in an X-en overlay)
**Description**: a systemic class in nl-en overlay authoring where
Dutch-side text was left in place (not correctly swapped/translated)
when generating the en-target overlay from the nl-source realization —
the class that drove nl-en's "Full review" tier recommendation in
Section 2 for several review rounds.
**First found**: prior nl-en overlay review rounds (see Section 2 nl-en
row history); closed 2026-07-12.
**Prevention status**: AUTOMATED (fixed) — fix landed plus a regression
test added 2026-07-12 (see Section 4 log entry same date). This is the
first nl-en review round with both the fix AND a durable regression
test in place; treat as CLOSED pending confirmation the test actually
runs in CI/verify.sh (not independently re-verified by this entry).

### 1.37 Script-constraint two-layer requirement for new languages (DB check constraint + Pydantic literal must both be updated)
**Description**: adding a new language's script value requires updating
TWO independent places — the Postgres check constraint on the relevant
column AND the Pydantic literal/enum in the backend schema — updating
only one silently leaves the other layer rejecting or miscategorizing
the new script.
**First found**: 2026-07-12, during ko/ja groundwork (script constraint
migration 0025 mentioned in root CLAUDE.md history).
**Prevention status**: UNPREVENTED — no single-source-of-truth or
validator catches a partial update; discovered via review, not
automated. **Next step**: either derive the Pydantic literal from the
DB constraint (or vice versa) at build/migration time, or add a
compiler/backend startup check that diffs the two lists and fails
loudly on mismatch. **Lane**: Codex (backend/migrations).

### 1.38 Romanized-source trap for ko/ja (source material teaches romanization, app must teach native script)
**Description**: public-domain/reference source material for Korean and
Japanese commonly teaches via romanization (romaji/romanized Hangul)
rather than native script — naively adapting such sources risks
authoring content that teaches romanization instead of native
Hangul/kana/kanji, which is wrong for this app's goals.
**First found**: 2026-07-12, ko/ja groundwork planning.
**Prevention status**: UNPREVENTED — no automated check exists (or
could easily exist) for this; it is a sourcing-discipline item.
**Avoid**: any ko/ja content authoring must render/grade in native
script by default; treat any source that presents romanization as the
primary form as needing an explicit conversion step, not a direct
adaptation. **Lane**: content-lane authoring discipline (ko/ja, not yet
in production content — groundwork stage only per root CLAUDE.md).

### 1.39 Devanagari OCR trap (scanned Hindi sources OCR unreliably)
**Description**: scanned/OCR'd Hindi source material is unreliable —
combining vowel signs, virama, and conjunct consonants are prone to
OCR misread or silent corruption, compounding with the existing 1.24
Devanagari tokenizer fragmentation issue at the compiler layer.
**First found**: 2026-07-12, noted alongside ko/ja groundwork review
(Devanagari-adjacent sourcing risk).
**Prevention status**: UNPREVENTED — no automated OCR-quality check
exists. **Next step**: prefer non-OCR (born-digital/Unicode) Hindi
sources where available; if OCR sourcing is unavoidable, add a manual
native-reviewer spot-check step before authoring from OCR'd text.
**Lane**: content-lane sourcing discipline (Hindi).

### 1.40 English "the X" lexeme glosses on bare-noun answers (en-nl practice translation)
**Description**: en-nl lexemes for nouns carry an English gloss with the
article ("the room", "the help", "the flower") while the token is the bare
Dutch noun (`kamer`). A bare-word `translation` practice template shows the
gloss and accepts only the token, so the natural answer "de kamer" /
"het station" is graded wrong (≥2 edits). Same family: a gloss naming a
contraction ("can't", "isn't") or a phrase ("wake" → "wakker worden" when the
learner types "wake up") in nl-en, and bare-verb glosses on inflected forms
("have" for `heb`, "can" for `kun`, "good" for `goede`).
**First found**: 2026-10-10, Dutch-direction review backlog (reported by 8
of 20 practice-pack reviewers independently).
**Instances**: course-wide in en-nl A1-B2 (dozens of noun lexemes); ~40
nl-en lexemes across A1-B2 (see the 2026-10-10 Section 4 entries).
**Root cause**: glosses written for recognition display, reused verbatim as
production prompts; practice translation templates carry exactly one answer
string (no `accepted` list).
**Prevention status**: UNPREVENTED. Worked around per pack where possible
(prompt suffix "(the Dutch noun only, without de/het)", slot narrowing).
**Fix options (needs a decision)**: (a) backfill glosses without the article
for nouns, or (b) grading/engine: accept an optional leading article on
bare-noun translation answers and contraction expansions on English answers.
**Lane**: backfill scripts (Codex) or backend grading (Codex).

### 1.41 Practice `feedback_frame` claims false at Endless-Practice (course) scope
**Description**: practice feedback frames assert provenance ("{item} is a
word from this dialogue", "...belongs to this unit's florist vocabulary",
"...is een woord uit deze les") that is false for most candidates once the
slot pool widens to the whole CEFR level (or the whole unit for
lesson-anchored templates).
**First found**: 2026-10-10, Dutch-direction review backlog (~150 frames in
en-nl alone; fixed in every reviewed Dutch pack).
**Learner impact**: currently LATENT — reviewers confirmed `feedback_frame`
is stored but never read by `backend/app/practice/service.py` or rendered by
`frontend/src`. It becomes live the moment feedback is wired up.
**Prevention status**: UNPREVENTED for unreviewed directions (fa-en, prs-en,
en-fa, en-prs packs still carry the pattern). **Avoid**: feedback frames must
be true for every course-scoped candidate ("The Dutch word is {item}.").
**Lane**: content (packs); a validator could flag frames containing
"this dialogue/lesson/unit's" over non-single-member slots.

---

## Section 2: Per-language/direction ledger

Directions with content on disk (2026-07-11): `en-nl`, `nl-en`, `en-fa`,
`fa-en`, `en-prs`, `prs-en` (the 6 launch-gate directions, mandatory
full review per CLAUDE.md's Tiered review policy until launch);
`en-de`, `de-en`, `en-es`, `en-fr`, `en-hi`, `en-pl`, `en-ro` (post-launch
drip content, in-flight).

| Direction | Bug classes hit (see §1 IDs) | Instance count (approx, cumulative) | Review-tier recommendation | Justification |
|---|---|---|---|---|
| en-nl | 1.7, 1.8(subset), 1.9, 1.10, 1.16, 1.17, 1.19, 1.20, 1.21, 1.22, 1.26 | ~150+ across all classes (largest, most mature corpus, 88 units) | **Full** (launch-gate, mandatory until launch) | Still finding real content bugs on recent passes (1.22 regressed 2026-07-09); largest corpus = largest absolute defect surface even if defect *rate* is falling. |
| nl-en | 1.7, 1.8 (94-fix batch concentrated here), 1.9, 1.16, 1.18, 1.21, 1.36 | ~120+ (heaviest hit by 1.8's matching_pairs left-text bug: 10+ units in one review round alone) | **Full** (launch-gate) | `test_content_answer_shapes.py`'s 60+ unresolved matching_pairs instances were concentrated here as of last measurement — do not downgrade until a fresh corpus-wide re-run shows 3 consecutive zero-defect reviews. **2026-07-12 update**: the 1.36 "Dutch-left" systemic class is now fixed + regression-tested (see Section 4 log), but nl-en remains launch-gate content and stays **Full** review regardless per policy §3 — this closes one bug class, it does not change the direction's tier. |
| en-fa | 1.5, 1.8, 1.12, 1.16, 1.18, 1.20, 1.29, 1.30 | ~60-80 across rounds | **Full** (launch-gate) | fa is the mandatory RTL/script-strict grading target; 1.30 (harakat) is fa/prs-specific and still uncaught by any validator. |
| fa-en | 1.7, 1.8, 1.16, 1.18, 1.28, 1.29 | ~60-80 | **Full** (launch-gate) | Same corpus family as nl-en/prs-en for shared-English bugs (1.8); 1.28's dialect fix touched fa-en overlays too. |
| en-prs | 1.5, 1.16, 1.20, 1.28 | ~40-60 (incl. 756-replacement dialect fix) | **Full** (launch-gate) | Mandatory RTL/virtual-keyboard target; 1.28 (dialect split-brain) is prs-specific and was project-wide when found — highest-severity single incident of any direction. |
| prs-en | 1.7, 1.8, 1.16, 1.18, 1.28 | ~60-80 | **Full** (launch-gate) | Same shared-English-content family as nl-en/fa-en. |
| en-de / de-en | 1.22 (17 instances), 1.25 | ~20-30 | **Full** — new territory (German just started, only 10 units) | Per policy §3, new languages get full review regardless of other lanes' maturity; 1.25 (case_sensitive) is de-specific and genuinely novel. |
| en-hi | 1.24, 1.26, 1.27 | 159+ (single systemic bug dominates) | **Full**, and BLOCKED from downgrading until 1.27 is confirmed fixed | 1.27 alone (159 unanswerable exercises, hi units 3-19) is the single largest unresolved defect count of any direction in this registry — do not sample this lane. |
| en-ro | 1.10-class (word-order/answer-shape), plus 1 confirmed grammar bug (plece 3sg/3pl syncretism distractor, `329ca85`) | 1 confirmed | **Sample** candidate once ≥3 consecutive zero-defect reviews land (currently 1 review, 1 bug found — not yet eligible) | Recipe reused from nl-en/fa-en/prs-en pattern (mature), but ro itself has had only 1 fresh-context review round so far. |
| en-pl | genitive-case grammar bug (`974d00c`, `665aa31`) | 1 confirmed | **Sample** candidate, not yet eligible (only 1 review round) | Same status as ro — mature recipe, immature per-language review history. |
| en-es / es-en | 1.2 residual (legacy dialogue format fixed `2ea892e`), parked per CLAUDE.md scope decision | low (content frozen, not actively growing) | **Validator-only** | Explicitly parked ("finish in-flight units, then park until nl is done") — no active authoring means no new-defect risk; existing content already compiler-clean. |
| en-fr / fr-en | 1.23 (apostrophe-elision, fr-specific) | 1 confirmed + 13 cosmetic | **Validator-only** (same parked status as es) | Same parked status; 1.23 is closed for the one real instance found. |

**Pack-authoring lane (cross-direction, tracked separately from the
per-direction rows above)**: the "pack-authoring" lane (Endless Practice
template packs, not overlay/realization content) has now logged 3
consecutive zero-defect fresh-context reviews as of 2026-07-12 — **per
CLAUDE.md's Tiered review policy, this lane is now ELIGIBLE to drop to
1-in-3 sampling** (reviewer's choice of which 1-in-3, not the author's).
This is a lane-level (recipe + authoring model) downgrade, distinct
from the per-direction table above; it does not change any individual
direction's launch-gate "Full" status where that direction's content
also happens to include packs. (Not recorded: the specific commit hashes
of the 3 qualifying zero-defect reviews — cross-reference BUILD_LOG/
git log around 2026-07-11/12 pack-authoring review commits if needed.)

**Caveat on this table**: instance counts are reconstructed from
BUILD_LOG/commit-message language, not a fresh corpus query — several
entries (notably en-hi's 159 and nl-en's matching_pairs count) have
documented staleness (see 1.8, 1.26, 1.27). Before acting on a
downgrade recommendation, re-run `test_content_answer_shapes.py`,
`_fill_in_blank_ambiguity_check.py`, and `_practice_content_integrity_check.py`
against current content for that direction.

---

## Section 3: Top gaps (UNPREVENTED classes, ranked by expected recurrence risk)

1. **1.22 — `listen_select` same-speaker distractor (unanswerable
   listening exercises).** Already regressed once after being fixed
   once (nl units 44-50 after an earlier W6 fix). Highest recurrence
   risk of any class in this registry — proven to recur under
   overnight/fast-paced authoring specifically. **Next step**: build a
   corpus-wide checker (sibling to `_practice_content_integrity_check.py`)
   that cross-references every `listen_select`/`dialogue_response`
   distractor against the full transcript of its own `media_asset_key`
   audio for the same speaker. **Lane**: compiler validator = Codex;
   the checker script pattern itself (script-only, no schema change)
   could also be built content-lane-side as an interim measure, same
   as `_fill_in_blank_ambiguity_check.py` was.
2. **1.10 — word_order/listen_order `accepted_answers` in scrambled
   (not sentence) order.** The compiler's multiset check cannot
   distinguish this from a correct answer by construction; only found
   via full fresh-context review (15 instances in one 5-unit review).
   **Next step**: a corpus-wide script comparing each `word_order`/
   `listen_order` `accepted_answers` sequence against a
   grammaticality heuristic, or — more reliably — flagging any
   template where `accepted_answers` token order exactly equals
   `word_bank` display order (a strong scrambled-copy signal).
   **Lane**: content-lane script (pattern precedent:
   `_fill_in_blank_ambiguity_check.py`).
3. **1.27 — en-hi systemic comprehension-answer bug (159 instances).**
   Largest single unresolved defect count in the corpus, status
   unconfirmed. **Next step**: re-run
   `test_content_answer_shapes.py` against current hi content
   immediately, then dispatch a dedicated fresh-context content-fix
   pass. **Lane**: content lane (Hindi authoring), verification =
   Claude session.
4. **1.24 — Devanagari tokenizer fragmentation.** Structural compiler
   gap, actively costing extra iteration time on every Hindi
   authoring round. **Next step**: fix `TOKEN_RE` (or add a
   Devanagari-aware tokenization path) in `scripts/compile_content.py`.
   **Lane**: Codex (compiler).
5. **1.12 — YAML boolean-coercion gap on title/gloss fields of
   vocabulary teaching items.** Confirmed gap, not yet closed; explicit
   backlog item named in CLAUDE.md's own Tiered review policy adoption
   note ("Known validator backlog"). **Next step**: widen the existing
   boolean-coercion validator to cover `title`/`gloss` specifically.
   **Lane**: Codex (compiler).
6. **1.20 — Wrong/contradictory `media_asset_key`.** No permanent
   validator exists (the 2026-07-06 sweep used a throwaway script).
   **Next step**: promote that comparison script (transcript-vs-
   `tested_text` word-level match) into a permanent corpus-wide checker
   alongside `_practice_content_integrity_check.py`. **Lane**:
   content-lane script initially, candidate for Codex compiler
   integration later.
7. **1.28 / 1.29 — Dialect split-brain and homograph collisions
   (fa/prs).** No automated dialect-consistency or homograph detector
   exists; both rely entirely on native/Fable review. **Next step**: at
   minimum, a script cross-referencing verb-ending suffixes against
   each unit's own declared `register_policy` for internal consistency
   (catches 1.28-shaped bugs specifically). **Lane**: content-lane
   script; full homograph detection (1.29) is likely infeasible to
   fully automate and should stay a review-discipline item.
8. **1.30 — Farsi/Dari harakat grading trap.** No automated check for
   "canonical answer has harakat but no undiacritized accepted
   variant exists." **Next step**: a corpus script flagging any fa/prs
   typed-answer exercise whose sole accepted answer contains a harakat
   character with no diacritic-stripped sibling variant. **Lane**:
   content-lane script.
9. **1.4 — Exercise-type registration drift.** Currently a pure
   manual-discipline rule (`comm` diff). **Next step**: a CI/verify.sh
   step that runs the same `comm` diff automatically after any
   exercise-type-touching change, failing the build if a used type is
   unregistered in `ExerciseRenderer.tsx`. **Lane**: frontend/Claude
   session (verify.sh is INFRA/Claude-owned tooling).
10. **1.19 — matching_pairs minimum scale.** GUIDE-RULE only, no
    compile-time enforcement of a minimum pair count. **Next step**: add
    a minimum-pairs-count check to the compiler validator (mirrors the
    existing candidate-count floor already enforced for
    multiple_choice/listen_select). **Lane**: Codex (compiler).

---

## Section 4: Maintenance rule

**Every future fresh-context review report must append its findings
here** — as a new dated entry under a running "Recent review yield log"
subsection (create it the first time this rule is exercised, below this
line), in the form:

```
### YYYY-MM-DD — <direction> <units> (<reviewer/session>)
Bug classes found: <§1 IDs, or "none — 0 defects">
New bug class discovered: <yes/no; if yes, add a new §1 entry and reset
  that lane's review tier to full per the Tiered review policy>
Instance count: <N, including 0>
```

**Zero-yield entries are data, not noise** — three consecutive
zero-defect reviews in a lane is the trigger to downgrade that lane to
1-in-3 sampling per CLAUDE.md's Tiered review policy. Do not skip
logging a clean review just because there's nothing to fix; the
absence of a bug is exactly the evidence a tier-downgrade decision
needs. Whoever runs `codex:rescue`, a fresh-context review dispatch, or
any manual review pass is responsible for this entry before closing out
that task — not a follow-up chore for someone else.

### Recent review yield log

(none logged yet under this rule as of 2026-07-11 — this registry's own
creation predates the rule's first live use)

### 2026-07-12 — nl-en overlays (coordinator/session, "Dutch-left" fix pass)
Bug classes found: 1.36 (new class — nl-en overlay "Dutch-left"
systemic bug)
New bug class discovered: yes; added as §1.36 above. CLOSED this
round: fix landed plus a regression test added (not merely a one-off
content fix), per SESSION_HANDOFF_2026-07-12.md. nl-en itself stays
**Full** review tier regardless (launch-gate content, policy §3) — this
entry records the class closure, not a tier change for the direction.
Instance count: (not recorded — see BUILD_LOG/commit history around
2026-07-12 for the exact fix commit if needed)

### 2026-07-12 — pack-authoring lane (3rd consecutive review)
Bug classes found: none — 0 defects (3rd consecutive zero-defect
fresh-context review in this lane)
New bug class discovered: no
Instance count: 0
**Tier action**: per Tiered review policy §2 (3 consecutive zero-defect
reviews → eligible for 1-in-3 sampling), the pack-authoring lane is now
ELIGIBLE to drop to 1-in-3 sampling. See Section 2 pack-authoring-lane
note above. (Not recorded: commit hashes of the 3 qualifying reviews.)

### 2026-07-12 — ko/ja groundwork review (script-constraint + sourcing discovery)
Bug classes found: 1.37 (script-constraint two-layer requirement), 1.38
(romanized-source trap for ko/ja)
New bug class discovered: yes (both); added as §1.37 and §1.38 above.
Neither is a content-authoring-tier issue per se (ko/ja are still at
groundwork stage, no production content authored yet), but both are
UNPREVENTED classes to guard against before ko/ja content authoring begins.
Instance count: (not recorded — discovered during groundwork/planning,
not a corpus review of existing content)

### 2026-07-12 — Devanagari OCR-sourcing discovery (Hindi, adjacent to ko/ja review)
Bug classes found: 1.39 (Devanagari OCR trap for scanned Hindi sources)
New bug class discovered: yes; added as §1.39 above. Related to the
existing §1.24 Devanagari tokenizer fragmentation compiler gap but
distinct (sourcing-quality risk vs. compiler tokenization bug).
Instance count: (not recorded — a sourcing-discipline finding, not a
corpus defect count)

### 2026-07-12 — fa B1 units 12-16 (fresh-context review, Codex gpt-5.5)
Bug classes found: 3 fixes found and all reviewed (per commit `3693bed`
message: "fa B1 12-16 (3 fixes, all reviewed)"). Specific §1 bug-class
IDs not individually identified in the commit message — (not recorded
which existing §1 classes, if any, these map to; treat as low-yield,
NOT zero-defect).
New bug class discovered: no (not indicated in commit message)
Instance count: 3
**Tier note**: this is a low-yield (not clean) review round for this
lane/direction — does not count toward a 3-consecutive-zero-defect
downgrade; resets any such streak for fa B1 content if one was being
tracked.

### 2026-07-12 — en B1 units 07-11 (fresh-context review, Codex gpt-5.5)
Bug classes found: listen-audio fixes found (per commit `3693bed`
message: "en B1 07-11 (listen-audio fixes, all reviewed pending
overlay-dependent checks)"). Likely relates to §1.20 (wrong/
contradictory `media_asset_key`) and/or §1.22 (`listen_select`
same-speaker distractor) given the "listen-audio" description, but the
commit message does not specify which — (not recorded, needs
confirmation against the actual diff before closing out §1.20/1.22
status for this direction).
New bug class discovered: no (not indicated in commit message)
Instance count: (not recorded — "fixes" plural, exact count not in
commit message)
**Status caveat**: explicitly "all reviewed **pending overlay-dependent
checks**" per the commit message — this review round is not fully
closed out; do not treat en B1 07-11 as a clean pass until the
overlay-dependent checks referenced in the commit are confirmed done.

### 2026-07-12 — it A1 units 01-03 (fresh-context review, Claude Opus; first-ever Italian content)
Bug classes found: 2 minor/cosmetic (one awkward learner-facing
matching label reworded; one §16 undersized matching_pairs expanded
with genuinely-taught digits). No hard/blocking defects, no grading
impact, no new bug class.
Instance count: 2 (unit01=0, unit02=1, unit03=1)
**Tier note**: new-language lane — stays Full review regardless
(policy §3, first batches of a new recipe). Quality of the
Sonnet-adaptation-from-FSI-FAST recipe looks strong on first evidence.

### 2026-07-12 — ru A1 units 01-03 (fresh-context review, Claude Opus; first-ever Russian content)
Bug classes found: 1 recurring class, 4 instances — `listen_order`
exercises wired to a nearby `media_asset_key` that does not speak the
tested sentence (audio containment violation; same family as §1.20 /
the listen_select same-speaker rule). All 4 fixed by adding dedicated
pending_generation assets. Russian grammar/register/ё/stress-stripping
all clean.
Instance count: 4 (unit01=1, unit02=1, unit03=2)
New bug class discovered: variant of known family — **validator
backlog item: extend the audio-containment check to `listen_order`**
(currently only the listen_select same-speaker rule is on the backlog).
**Tier note**: new-language lane — Full review stays. The bug is
mechanical wiring, not language competence.

### 2026-07-12 — en-it overlays A1 01-03 (fresh-context review, Claude Opus; first en-it overlays)
Bug classes found: **NEW SYSTEMIC CLASS** — overlay matching_pairs
`accepted_answers` diverging from the realization's `pairs` (frontend
shows realization tiles, grading compares overlay accepted_answers →
exercise ungradeable-incorrect regardless of learner input). 5
instances (English rights vs Italian tiles, swapped/mistranslated pair,
5-of-11 pair subset, decimal point vs Italian decimal comma). Plus 1
listen_select spoken-substring distractor violation.
Instance count: 6 (u01=1, u02=2, u03=3)
New bug class discovered: YES — **validator backlog (Codex lane,
HIGH PRIORITY): compiler must cross-check every overlay matching_pairs
accepted_answers left/right set equals its realization pairs set
(count + exact strings)**; a green compile let all 5 through.
**Tier note**: en-it overlays stay Full review — high first-batch yield.

### 2026-07-12 — en-ru overlays A1 01-03 (fresh-context review, Claude Opus; first en-ru overlays)
Bug classes found: 1 low-severity display-integrity defect (a
"mirrored glyph" MCQ distractor that renders identical to the correct
Cyrillic letter in plain text). Fixed. Glosses, distractor-vs-audio,
matching_pairs mirrors, YAML hygiene all clean.
Instance count: 1 (u01=1, u02=0, u03=0)
New bug class discovered: minor variant — "distractor that cannot be
rendered distinctly in text" (script-ramp letter exercises); note for
future script-ramp authoring (ko/ja/ar).
**Tier note**: en-ru overlays stay Full review (new lane).

### 2026-07-12 — it/ru A1 units 04-06 realizations + overlays (fresh-context reviews, Claude Opus)
Realizations: 0 correctness defects both languages (4 ru §16
matching_pairs poolings applied — ru author systematically under-sized
where the it author pooled correctly). Overlays: 0 defects, all six
files, all priority classes (pairs-mirror, distractor-vs-audio,
render-distinct) checked mechanically and clean.
Instance count: realizations 0+0 (4 quality poolings), overlays 0.
New bug class discovered: no.
**Tier note**: it/ru realization + overlay lanes each now have a
zero-correctness-defect streak forming (overlay lane: 2 consecutive
clean units-batches for ru, 1 for it after its unit01-03 6-defect
batch). Both lanes stay Full review (new language) but the recipe
with the inline pairs-mirror + audio-containment rules is holding.

### 2026-07-12 — nl-en / fa-en / prs-en B1 overlays 07-11 (fresh-context reviews, Claude Opus; authored by Codex gpt-5.5)
Yields: nl-en 0 defects / 5 files; prs-en 0 defects / 5 files (Dari
register fully clean); fa-en 1 defect / 5 files — one listen_select
same-speaker distractor (unit11: "the design course" is spoken by the
tested speaker). Exactly the known not-yet-compiler-enforced §1.22
class; validator dispatch is in flight (task-mrhf0qrp).
Instance count: 1 total across 15 files.
New bug class discovered: no.
**Tier note**: launch-gate — all three lanes stay Full review until
launch regardless of streaks. The Codex-B1-overlay recipe (pairs-mirror
+ sibling-isolation rules inline) is performing at near-zero yield.

### 2026-07-12 — it/ru A1 units 07-09 realizations + overlays (fresh-context reviews, Claude Opus)
Realizations: 1 defect / 6 files (ru unit08 unrealistic price in
learner-facing dialogue, fixed; no grammar/containment/gradability
defects). Overlays: 0 defects / 6 files, all mechanical checks clean.
New bug class: minor — "real-world realism" (prices/facts) worth a
reviewer-checklist line, not a validator.
**Tier note**: both lanes remain Full (new language); recipe holding at
near-zero yield with validators now enforcing pairs-mirror + containment.

### 2026-07-12 — it/ru A1 units 10-12 realizations + overlays (fresh-context reviews, Claude Opus)
Realizations: 0 correctness defects both languages (5 ru §16
matching_pairs poolings — the ru-author-undersizes pattern recurred a
third time; overlay/realization recipe prompts should carry the §16 aim
explicitly for ru). Overlays: 0 defects / 6 files.
**Tier note**: en-it and en-ru overlay lanes now at 2-3 consecutive
zero-defect batches; realization lanes near-zero. Still Full review
(new language) but both lanes are candidates for 1-in-3 sampling once
each hits 3 consecutive clean batches AND validators cover the recurring
classes (pairs-mirror + containment now compiler-enforced).

### 2026-07-12 — en-fa §16 retrofit (25 exercises) fresh-context review (Claude Opus)
0 defects: every pooled pair verified taught-in-unit, glosses correct,
0 Arabic-character hits, mirrors compiler-confirmed. One PRE-EXISTING
flag (not this change): fa u37 lesson03 match_asking_color_words has
two synonym lefts both glossed "What color is it?" — technically
ambiguous in a matching UI; small-fix backlog.

### 2026-07-12 — German lane recovery (fixes + fresh-context review, Claude)
Dead session's WIP landed; 23 unique validator errors fixed (13
same-speaker distractors, 5 pairs-mirror, en-de+de-en). Fix diff
fully reviewed (Opus): all new distractors verified absent from audio,
natural, plausible-wrong; mirrors character-exact. 0 defects in review.
Both directions now validate 0 errors → full-corpus content validation
GREEN for the first time. Note: first fixer attempt FALSELY self-
reported success (validated wrong file set) — coordinator re-validation
caught it; acceptance commands must be verbatim in fixer prompts.

### 2026-07-12 — en A1 units 59-63 + it/ru units 13-15 (+overlays) reviews (Claude Opus)
en 59-63 (launch-gate X→en expansion): 1 cosmetic content_key fix +
1 non-blocking dialogue-logic note (unit62), otherwise clean; all
reviewed. it/ru 13-15 realizations AND overlays: 0 defects across all
12 files. it/ru overlay lane now at 3+ consecutive zero-defect batches
with the two big classes compiler-enforced → per policy §2, eligible
for 1-in-3 sampling from the units 16+ waves onward (coordinator
decision applied going forward; realization lane likewise eligible).

### 2026-07-12 — X→en A1 units 59-63 wave (en realizations + 3 overlay sets)
en realizations (Opus review): 1 cosmetic content_key fix + 1
non-blocking note. nl-en overlays: 0 defects. prs-en overlays: 0
defects (Dari clean). fa-en overlays: **NEW CLASS — lane register
divergence** (Codex authored formal Persian; lane norm colloquial).
Reviewer correctly escalated instead of auto-fixing; converted by a
dedicated worker (~255 forms), second-round review found 3 leftover
formal forms in u63 (fixed) and 0 over-conversion errors.
PREVENTION: per-lane register pins added to docs/content/CLAUDE.md —
every new authoring dispatch must quote the lane's pinned register.
**Tier note**: fa-en overlay lane resets to full review (new class);
nl-en/prs-en remain full (launch-gate).

### 2026-07-12 — X→en A1 units 64-68 wave (en realizations + 3 overlay sets)
en realizations: 0 defects (1 borderline dialogue phrasing noted, not
tested). nl-en overlays: 0 defects (4+ consecutive clean batches).
fa-en overlays: 0 defects — the register pin quoted verbatim in the
Codex dispatch PREVENTED a recurrence of the register-divergence class.
prs-en overlays: 1 gloss-faithfulness defect (علامه "eminent scholar"
for علامت "symptom", 11 occurrences in u66, fixed in review) — real
Persian-orthography confusable; lane stays full review.
Process note: two of three Opus reviewers this round committed DIRECTLY
to master (worktree isolation not honored — known footgun, commits
verified clean); coordinator diffed git log per standing rule.

### 2026-07-12 (evening) — en B1 12-14, ru A1 16-18, it A1 16-18 (fresh-context reviews, Claude Opus)

**Yields — the sampling experiment FAILED and was reversed:**
- **en B1 12-14** (launch-gate, shared spine for nl-en/fa-en/prs-en; full
  review): **9 defects** (u12: 4, u13: 1, u14: 4). Incl. a genuinely
  unanswerable matching exercise (4 interchangeable glosses) and 3
  underdetermined production prompts where 3 of 4 correct answers would
  grade WRONG. Character continuity vs u09-11 verified clean.
- **ru A1 16-18** (1-in-3 SAMPLE): **4 defects**, one a NEW bug class —
  a dialogue teaching card attributed Дима's line to Настя (she asked how
  many rooms were in her own apartment), contradicting the unit's own
  audio; a second unit skipped an audio turn, leaving a tested word
  untaught. Fired twice in one wave. Author's two self-flagged Russian
  concerns (formal вы register, на кухне idiom) verified CORRECT.
- **it A1 16-18** (was set to merge on VALIDATORS ALONE; pulled back to
  full review because the ru sample found a new class): **10 defects, all
  compiler-invisible — it validated at 0 errors before review.** Three
  graded a CORRECT learner answer as WRONG (a fill-in yielding "e il il
  bagno"; an instruction demanding "three words" whose answer had five; a
  prompt whose own feedback showed a different string than the accepted
  answer). Plus a cross-unit character-canon break (Sam is an engineer
  since u02; u17 made him a teacher) — which would have been RECORDED as
  audio, since audio_manifest.py pulls dialogue text into the record queue.

**Tier ruling: it/ru RESET to full review. Sampling was misapplied** — a
lane is mature per-RECIPE, and these units moved to NEW TOPICS
(health/work/housing), which policy already classes as new territory.
Rule now written into root CLAUDE.md §Tiered review 4.

**New rule-shaped classes → validators (Codex, dispatched same session):**
1. `untaught_vocabulary` only checked `tested_text`, NOT
   `prompt.target_blocks` — **the gap that caused defects in BOTH waves.**
   Must resolve taught tokens CUMULATIVELY over prior units (an author
   wrongly dropped a valid pair believing "non" untaught — taught since u12).
2. Duplicate/confusable matching_pairs LEFTs (duplicate RIGHTs are LEGAL —
   many-lefts→one-right is intentional; frontend fixed 2026-07-12).
3. Underdetermined production prompts (word-count contradiction;
   feedback string ≠ accepted answer).
4. Dialogue teaching cards vs the dialogue audio's speaker-labelled turns.

**Frontend bug found live the same day (not a content defect):**
`MatchingPairs.tsx` keyed/disabled right tiles by TEXT VALUE, so nl A1
u13's 3×"lekker"/3×"leuk" exercise disabled all matching tiles on the
first pick → Check never enabled → **lesson impossible to complete** in the
en-nl launch pair. Fixed to index-keying (`ba804a7`), verified live.
Affected 5 exercises across nl u11/u12/u13 and it u01.

### 2026-07-12 (night) — nl-en/fa-en/prs-en B1 overlays 12-14 (fresh-context reviews, Claude Opus ×3)
Bug classes found: nl-en: none — 0 defects (72 exercises). fa-en: 2 (one
ambiguous MC distractor — a second option also satisfied the stated
criterion, §1 answerability class; one garbled Persian instruction,
doubled verb). prs-en: 1 (same ambiguous defining-clause MC distractor
class — TWO distractors also satisfied "defining clause, no commas").
New bug class discovered: no (ambiguous-MC-distractor is the known
answerability class; note it recurred INDEPENDENTLY in two lanes on the
same realization exercise — en.b1.unit13.lesson02.exercise01 invites it
because overlay authors must invent distractors for a grammar-form
question; distractor sets for form-identification MCs are a recurring
weak point that no validator checks).
Instance count: 3 across 9 files. All fixed by coordinator (reviewer-
specified single-field edits), re-validated 0 errors, merged.
Preflight-checklist note: first wave with AUTHORING_PREFLIGHT.md pasted
verbatim — yield fell from 23 (previous wave, 3 lanes) to 3, and zero
findings in every class the checklist names except item 1 edge case
above.

### 2026-07-13 — en B1 realizations 15-17 (fresh-context review, Claude Opus)
Bug classes found: 1 — prompt/answer wording mismatch (u16 l03 ex05:
prompt said "the other project", sole accepted answer said "the other
one"; correct learner graded wrong). Known underdetermined-prompt
sub-class.
New bug class discovered: no
Instance count: 1 across 3 files. Fixed by coordinator (prompt aligned
to accepted answer), merged. Units 15 and 17: zero defects.
NOTE: compiler validation still pending — requires the first X→en
overlay for these units; reviewer reproduced the mechanical validators
by hand (cumulative token coverage clean across b1 01-17).

### 2026-07-13 — en B1 realizations 18-19 (fresh-context review, Claude Opus)
Bug classes found: 3 — two prompt/accepted-answer wording mismatches
(u18 l03 ex05 "Daniel" vs "He"; u19 l02 ex05 "the team is" vs "we are")
and one confusable matching_pairs LEFT pair (u19 "in summary" vs "in
short" glosses did not discriminate — blocking, unanswerable). All known
classes; the confusable-lefts hit was pre-flagged by the AUTHOR's own
preflight self-report, which the reviewer confirmed.
New bug class discovered: no
Instance count: 3 across 2 files. Fixed by coordinator, merged.
Compiler validation still pending first X→en overlay for these units.

### 2026-07-13 — nl-en/fa-en/prs-en B1 overlays 15-17 (fresh-context reviews, Claude Opus ×3)
Bug classes found: none — 0 defects across all 9 files (63 exercises/lane).
One optional strengthening applied (prs-en u17 choose_procrastinate:
"delay" distractor semantically overlapped the Dari prompt's wording —
swapped for "regret"). One judgment item flagged for Ramin, no change
made: nl-en u15 complaint-LETTER glosses use formal "u" (reviewer judges
correct Dutch business register; learner-facing instruction voice stays
jij).
New bug class discovered: no. First corpus compile of units 15-17 found
1 realization defect ("leading" forward-referenced, fixed 9ff6886) —
5 other standalone-run errors were cumulative-vocabulary false positives.
Instance count: 0 overlay defects. The form-identification-distractor
warning quoted verbatim in these dispatches returned zero findings —
consistent with the preflight-verbatim effect (23→3→0 over three waves).

### 2026-07-13 — nl-en/fa-en/prs-en B1 overlays 18-19 (fresh-context reviews, Claude Opus ×3)
Bug classes found: nl-en: none — 0 defects. fa-en: none blocking; 1
optional strengthening applied (u19 l04 ex01 distractor was the OTHER
speaker's real line — legal but borderline; swapped for fabricated).
prs-en: 2 — Iranian-register leak (می‌خوام ×5 in u18, lane pin is Dari;
fixed to می‌خواهم) and a cue/answer mismatch (u19 l02 ex04 Dari cue said
"in short" while only the "In summary" answer was accepted — correct
learner graded wrong; cue realigned).
New bug class discovered: arguably one AUTHOR-side sub-class worth a
rule: a production prompt's SOURCE-LANGUAGE cue must use the gloss of
the same discourse marker the accepted answer uses (cue/answer marker
mismatch). Added to no validator (semantic); reviewers now watch it.
Instance count: 3 fixed + 1 strengthening across 6 files.
First corpus compile of units 18-19 found 1 realization defect
("months" untaught, fixed 181af98) — the second time the first overlay
compile caught a realization token gap (see "leading", 9ff6886).

### 2026-07-13 — media_asset_key validator first corpus sweep (Codex validator + Codex triage)
Bug classes found: 6 genuine wrong media references (class 1.20) — 4 in
en-fr A1 (salade/matin/gare/dimanche cards playing a different clip),
2 in en-nl A1 (u32 Fenna, u33 Sander listen_selects playing a related
but different sentence → unanswerable by listening). All fixed by
pointing at (or adding) the correct asset. 32 other warnings judged
heuristic false alarms (paraphrase/summary/contraction) — warning level
is correct; do not escalate to errors.
New bug class discovered: no (1.20 was a known unprevented class; it is
now validator-covered: dangling refs hard-error, mismatches warn).
Instance count: 6 fixed across 6 files.

### 2026-07-14 — B2 en units 01-03 fresh-context review (Codex review of Codex-authored first-ever B2 wave)
Bug classes found: ~17 findings across all three files, high yield as
predicted for a NEW CEFR tier. Dominant classes: (a) underdetermined
production prompts (known class, at least 7 instances — B2's nuance
makes it structurally worse: hedged instructions admit many defensible
answers); (b) NEW class: unit under-covers its own spine outcome's
production requirement (all 3 units drill components but never require
the full sustained argument/speculation/modulation the outcome names);
(c) vocabulary-example sentences using unit-specific terms before they
are taught (multiple per file); (d) media_assets dialogue text baking
speaker names inline ("Mia: ..."), cross-file; (e) may-vs-might
matching lefts too close to discriminate; (f) meta/coursebook-stilted
dialogue ("What are you hedging?") — register defect at a tier where
naturalness IS the content.
New bug class discovered: yes — outcome-production under-coverage (b);
consider a spine-outcome production-requirement checklist line in the
authoring preflight for B1+ tiers rather than a validator (judgment
call, not rule-shaped).
Instance count: fixes dispatched to Codex same session; re-review
required before status: reviewed.

### 2026-07-14 — B2 en units 01-03 RE-review + second fix round (Codex both)
Bug classes found: 10 residual findings, all in the two known classes —
untaught-vocabulary-in-example-sentences (6) and underdetermined
production prompts (4). Structural checks (spine alignment, pacing,
dialogue attribution, character canon, register, boolean coercion) came
back clean. All 10 fixed via the reviewer's own suggested wording;
coordinator diff-verified each against the finding list. Units flipped
to status: reviewed.
New bug class discovered: no.
Instance count: 10 fixed across 3 files. Lane yield trajectory for the
first B2 wave: ~17 -> 10 -> 0 outstanding.

### 2026-07-14 — nl-en B2 overlays u01-03 fresh-context review + fix (Codex both)
Bug classes found: 9 — 3 stale accepted_answers (overlay authored against a
realization sentence the coordinator subsequently fixed — sequencing
artifact, not an authoring defect class; lesson: re-sync overlays after ANY
realization edit), 3 two-correct-answer multiple_choice (distractor also
satisfied the instruction; fixed by narrowing the Dutch instruction to name
the exact modal/form — the right fix at B2 where near-synonymous forms are
the teaching point), 3 calqued/drifted Dutch glosses (incl. "betrokkenheid"
for stance-commitment → "stelligheid"). Reviewer confirmed genuine
interference-error work (not a translation layer) in all three files.
New bug class discovered: no (all known classes or sequencing artifacts).
Instance count: 9 fixed across 3 files; compiler 0 errors; wired as
nl-en-b2 manifest course; verify.sh --content-only PASS on full corpus.

### 2026-07-14 — fa-en + prs-en B2 overlays u01-03 review + fix (Codex, sibling-isolated)
Bug classes found: fa-en 15 (gloss naturalness/fidelity majority; 1
exercise-level: listen_select with ALL distractors heard in the audio —
the known class 1.x same-speaker/heard-distractor rule, still validator
backlog; fixed with not-heard wrong options), prs-en 8 (natural-Dari
wording — میعادها→مهلت‌ها class calques; 1 thin-interference note fixed
with a contrastive article/word-order gloss). fa-en got a second
fresh-context pass (because of the exercise-level bug): CLEAN, flipped
reviewed. prs-en closed on coordinator diff-verification (wording-only
findings). Both wired as fa-en-b2 / prs-en-b2 manifest courses;
verify.sh --content-only PASS on full corpus.
New bug class discovered: no. Reminder: the heard-distractor validator
(listen_select) remains the top validator-backlog item — it caught a
real instance again.
Instance count: 23 fixed across 6 files.

### 2026-07-14 — heard-distractor validator lands (class closed) + 8 corpus repairs
The long-backlogged listen_select/dialogue_response rule ("a distractor
must never be something the tested speaker says anywhere in that audio")
is now a compiler validator: same-speaker match = hard error,
other-speaker match = warning, full-turn/sentence granularity (no
substring over-triggering). 11/11 unit tests incl. armed test;
coordinator-verified. First corpus sweep found 8 REAL pre-existing
defects across nl/fa/prs-en a1_21, en-de u06/08, de-en u06/08/10/11/12 —
all repaired (distractors replaced with not-heard options), corpus PASS.
The validator backlog from the tiered-review policy is now EMPTY again.
Instance count: 8 fixed across 10 files (three a1_21 overlays share one
English audio).

### 2026-07-14 — B2 en units 04-08 fresh-context review + fix (Codex both)
Bug classes found: 4 total across 5 units (vs 17 in the units 01-03
wave — the preflight item-7 production-requirement rule and the wave-1
lesson list in the dispatch prompt measurably worked; units 04 and 07
came back CLEAN on first review). Findings: register-naturalness
("To whom it may concern" too stiff for the scenario; unquoted embedded
written sentences in dialogue), one introduced_tokens wiring mismatch
(qualify vs qualification), one dialect slip (UK "judgement" in an
en_US_neutral course — NEW small class: dialect-consistency; watch for
it, probably not validator-worthy yet). All fixed and coordinator
diff-verified; all five units flipped to reviewed.
New bug class discovered: dialect-consistency (minor).
Instance count: 4 fixed across 3 files.

### 2026-07-14 — nl-en B2 overlays u04-08 review + fix (Codex both)
Bug classes found: ~9, ALL natural-Dutch wording/grammar class ("duwde
terug" calque, singular/plural agreement around "het hoofdprobleem",
"in Engels" -> "in het Engels" article slips). Zero exercise-level or
answerability defects — the heard-distractor validator plus the
enumerated-answers rule in the dispatch prompt appear to have prevented
the structural classes entirely. Reviewer confirmed genuine
interference work per unit (perfectum-vs-simple-past, register-as-
phrasing-not-pronouns, directness softening, linker discipline).
All fixed with reviewer wording, coordinator diff-verified, flipped
reviewed; nl-en-b2 manifest course extended 3 -> 8 units; corpus PASS.
New bug class discovered: no.
Instance count: ~9 fixed across 5 files.

### 2026-07-14 — fa-en + prs-en B2 overlays u04-08 review + fix (Codex both)
Bug classes found: all register/gloss-nuance wording (Persian register
cleanup across units, one real polysemy defect: در اصل glossing
"in principle" can read "actually/originally"; Dari spelling notes).
Zero structural/answerability defects — same pattern as the nl-en
04-08 wave: validator + prompt-side prevention hold. All fixed with
reviewer wording, coordinator-verified (compiles 0 errors, script
purity clean, no disagreements); flipped reviewed; fa-en-b2 and
prs-en-b2 manifest courses extended 3 -> 8 units; corpus PASS.
New bug class discovered: no.
Instance count: ~20 wording fixes across 10 files.

### 2026-07-15 — it/ru A1 19-24, de A1 11-16, ar A1 04-09 review + fix (Codex both)
Yield per lane: it 7, ru 9, de 19, ar 12 (~47). Dominant classes:
heard-distractor listen exercises (de-heavy — including two NEW validator
gaps: unlabelled single-voice audio skipped entirely, and
dialogue_comprehension type not covered), accepted_answers not matching
the displayed correct_option (grades a correct click WRONG — new class,
now hard-errored), underdetermined production prompts (all lanes), Arabic
gender agreement (قال ليلى -> قالت, 6 units), MSA ordinal clock times.
Fix round + re-review: ru/de/ar ALL RESOLVED; it had 1 residual dialogue
coherence defect (fixed by coordinator directly). All 48 files flipped
reviewed; 4 manifest courses extended (it/ru -> 24, de -> 16, ar -> 9).
New bug classes discovered: accepted-answer/option mismatch (validator
built); unlabelled-audio heard distractor (validator built).
VALIDATOR FALLOUT: ungating the new checks exposed 938 unique latent
corpus defects (nl-en 604 lines / fa-en 544 / prs-en 512 error lines,
plus en-de/de-en/es/fr/nl/ro) — all repaired mechanically (single-item
audio assets; unspoken distractors; accepted-answer alignment), corpus
PASS at 0 errors 0 warnings under the ungated validator. NOTE: Codex's
validator draft shipped with a language-scope gate {ar,de,it,ru} + a
"legacy" exemption that masked exactly those 938 — reinforces the
standing rule: never accept a Codex validator without running it
ungated on the full corpus yourself.
Known remaining debt: en-de old units 01-10 + their overlays are still
status unreviewed from the original de lane opening (pre-existing).
Instance count: 47 review findings + 938 validator-driven repairs.

### 2026-07-15 — wave 2: es/fr A2 completion, it/ru A2 tier opened, de A1 17-22, ar A1 10-15 (Codex both)
Yield per lane: es 13, fr 7, ar 7, de 10, it-A2 12, ru-A2 15 (~64).
ZERO listen-audio/answerability defects in ANY lane — first wave authored
with the new validator rules quoted in the dispatch prompt; prevention
confirmed again. Dominant classes: underdetermined exact-string production
prompts (all lanes), untaught-in-tier tokens on the two NEW A2 tiers
(it 16 / ru 54 compile errors pre-review — the A2-course-validates-
STANDALONE rule; both repaired via refresher cards), dialogue-card/audio
discipline (es u22), wording/idiom.
Fix rounds verified by separate fresh-context verification tasks: fr/ar/de
ALL RESOLVED; es 1 residual accepted by coordinator judgment (re-shuffled
sequence distractors are listening-distinguishable, validator-compliant);
it 3 + ru 2 residuals fixed directly by coordinator. All 64 files flipped
reviewed; manifests: en-es-a2 -> 10u, en-fr-a2 -> 10u, en-de -> 22u,
en-ar-a1 -> 15u, NEW courses en-it-a2 (6u) + en-ru-a2 (6u). Corpus PASS.
New bug class discovered: untaught-in-tier tokens at tier opening (process
fix: tier-opening dispatch prompts must state the standalone-tier rule and
use tier-only acceptance commands).
Instance count: ~64 review findings + 70 tier-token compile errors.

### 2026-07-15 — wave 3: it/ru A2 complete (10u tiers), de A1 complete (24u), ar A1 16-21, es/fr B1 tiers opened (Codex both)
Yield: it+ru 9, de+ar ~8, es+fr B1 8 (~25 across 44 files — roughly a
third of wave-2's per-file rate). ZERO standalone-tier compile errors
(wave-2's process fix — tier rule + tier-only acceptance commands in the
dispatch prompt — eliminated that class entirely; es/fr B1 openings
compiled clean first pass). Dominant classes: compound-outcome
under-coverage in culminating productions at B1 (preflight item 7 at new
depth), underdetermined exact-string prompts, naturalness (ar عندي صداع
framing, MSA suggestion forms). NEW REVIEW-ONLY CLASS: cross-language
audible distractor (English comprehension option semantically matching
Arabic audio — string-matching validators cannot catch this; reviews
must). Fix-verifications: it/de/es/fr ALL RESOLVED; ru 1 + ar 1 residuals
fixed directly by coordinator. All flipped reviewed; manifests: en-it-a2
& en-ru-a2 -> 10u (tier complete), en-de -> 24u (A1 complete), en-ar-a1
-> 21u, NEW en-es-b1 (3u) + en-fr-b1 (3u). Corpus PASS.
Instance count: ~25 findings.

### 2026-07-15 — wave 4: es/fr B1 +3u, it/ru B1 opened, de A2 opened, ar A1 core-24 complete (Codex both)
Yield: es+fr ~6, it+ru ~6, de+ar ~10 (42 files). All tier chains compiled
0 errors first pass again. Dominant: compound-outcome delivery at B1,
naturalness in new-construction units (it regret construction "Sarebbe
bisognato" was UNGRAMMATICAL — caught by fix-verification after the fix
task SILENTLY SKIPPED it), ar dialogue-card/audio turn mismatches.
PROCESS FINDING: a fix task can report done while skipping findings —
the separate fix-verification stage caught 5 skipped it/ru items; a
scoped round-2 fix closed them. Keep fix-verification mandatory for
new-tier waves. es/fr/de/ar ALL RESOLVED first verification.
Manifests: en-es-b1/en-fr-b1 -> 6u, en-ar-a1 -> 24u (core-24 COMPLETE),
NEW en-de-a2 (6u), NEW en-it-b1 + en-ru-b1 (3u each). Corpus PASS.
Instance count: ~22 findings + 5 round-2 items.

### 2026-07-15 — wave 5: es/fr B1 -> 8u, it/ru B1 +3u, de A2 tier COMPLETE (10u), ar A2 opened (Codex both)
CORRECTION (same day): "B1 complete" was wrong — the canonical en B1 tier has
19 outcomes, not 8 (coordinator sliced the spine grep with head -8). es/fr
are at 8/19, it/ru 6/19. Wave 6+ continues the B1 grind.
Yield: es+fr small (wording/gloss/mood), it+ru moderate (narrator
attribution, aspect glosses), de+ar largest (ar A2 opening). All chains
compiled 0 errors first pass (5th consecutive wave). The "do not skip —
verification checks each finding" prompt line worked: ALL SIX languages
came back ALL RESOLVED on the FIRST verification (vs wave-4's 5 skipped
items). Manifests: en-es-b1 & en-fr-b1 -> 8u, en-de-a2 ->
10u (A2 COMPLETE), en-it-b1/en-ru-b1 -> 6u, NEW en-ar-a2 (3u). Corpus PASS.

### 2026-07-15 — wave 6: FIRST CLAUDE-SUBAGENT WAVE (Sonnet author / Opus review / Sonnet fix; Codex exhausted until Jul 21)
es B1 34-37, fr B1 33-36, it B1 41-44, ru B1 41-44, de B1 OPENED (35-37,
Konjunktiv II), ar A2 28-30. All 6 chains compiled 0 errors (es needed a
coordinator 2-token boolean rescue after its author died on a connection
error mid-report — partial work was complete on disk).
Yields: es 2 (incl. a reported-speech DEIXIS error in the culminating —
tienes/tengo — the subtlest grading-wrong-answer class yet), fr 4 (TWO
character-canon violations: apprentice Inès cast as bakery owner and as
Mathieu's trainer; two compound-outcome gaps), it 0, ru 0 hard + 2
native-flags (coordinator resolved: Коллега register -> вы; instrumental
хорошей variants added to accepted answers), de 2 (1 coherence: regret
attributed to the wrong character), ar 4 (single-variant culminating
grading, calqued gloss, borderline distractor echoes).
OBSERVATION: Opus reviewers catch subtler language classes (deixis,
cross-unit canon, predicate-case grading coverage) than the Codex
reviewers did; Sonnet authors' grammar was clean (Konjunktiv II, ли,
чтобы+past, MSA agreement all correct first pass). Fix agents applied
ALL findings first pass (no skips) with quoted-diff reports.
Manifests: en-es-b1/en-fr-b1 -> 12u, en-it-b1/en-ru-b1 -> 10u, NEW
en-de-b1 (3u), en-ar-a2 -> 6u. Corpus PASS.
Instance count: ~14 findings, 2 coordinator-resolved flags.

### 2026-07-15 — wave 7 (Claude pipeline, 2nd wave): es/fr B1 -> 16u, it/ru B1 -> 14u, de B1 -> 6u, ar A2 tier COMPLETE (10u)
60 files; all 6 chains 0 errors first pass (es 32 pre-existing pool-size
warns). Yields: it 1 real + 3 flags, ru 1 real + 4 flags (coordinator
resolutions: FEMININE past-tense variants added to free-text answers —
new fairness class; ungrammatical distractor replaced; тебе стоит pair),
es 1 (passage misattributed to Mateo — person/canon deixis class again),
fr 2 real (pervasive third-person self-address "Même si Mathieu a raison"
-> "tu as raison" — naturalness deixis; untaught matching pair) + 2 minor,
de 1 minor (instruction parenthetical contradicted its own deixis rule)
+ flags, ar 1 medium (weekday-activity distractors audible in clip —
swapped for unmentioned activities) + minors (fixed directly).
PATTERN: the recurring Claude-wave defect class is PERSON DEIXIS /
self-address naturalness (3 waves running) — added to prompts; also
gender-variant acceptance for first-person past Russian is now standing
practice. Manifest counts: en-es-b1/en-fr-b1 16u, en-it-b1/en-ru-b1 14u,
en-de-b1 6u, en-ar-a2 10u (COMPLETE). Corpus PASS.
Instance count: ~7 real + ~12 flags/minors.

### 2026-07-15 — wave 8 (Claude pipeline, 3rd wave): es/fr/it/ru B1 TIERS COMPLETE (19u/19 outcomes each), de B1 -> 10u, ar B1 opened
68 files. All chains 0 errors first pass. INCIDENT: ar author FALSELY
self-reported script purity — 6 Persian ک codepoints in 3 files, caught
by the coordinator's own sweep (never trust self-reports, again);
review prompts now demand codepoint re-verification.
Yields: es/fr ZERO content defects (first fully-clean pair review of the
Claude era — tier-completing units), it 2 minor, ru 1 grading (feminine
предложила variants missing in ONE unit — the outlier; siblings handled
it) + 1 minor, de 1 moderate (comma-variant grading on ALL FOUR
culminating writes — distance-2 class) + 3 minor, ar 1 moderate (лов...
counterfactual presupposed failure of an interview the unit keeps open —
internal-timeline class, retargeted to a past exam) + 2 flags.
Manifest: en-es-b1/en-fr-b1/en-it-b1/en-ru-b1 -> 19u (B1 COMPLETE),
en-de-b1 -> 10u, NEW en-ar-b1 (3u). Corpus PASS.
Instance count: ~9 real + flags; 3 coordinator-direct fix rounds.

### 2026-07-15 — wave 9 (Claude pipeline, 4th wave): de B1 -> 14u, ar B1 -> 6u, pl/ro/hi B1 lanes REOPENED (+3u each)
Yields: de 0, ar 1 (speaker/gender deixis self-contradiction — a feminine-
addressed question attributed to the woman being addressed), pl 13, ro 5,
hi 9. The reopened lanes ran ~9x hotter than the practiced ones — per-
recipe maturity holds across ENGINES, not just languages: a lane's first
Claude wave is new territory even when the recipe is proven elsewhere.
WORST FINDING OF THE SESSION (hi u09, HI-7): the author invented a wrong
agreement rule ("hota agrees with the speaker") for the ergative
construction, wrote it into the answer policy AND feedback, and accepted
two UNGRAMMATICAL किया-होती strings as correct answers — a false
"feminine-variant" self-certification (the pl u08 author made the
opposite false claim: said variants were included, they weren't). Both
caught only by fresh-context review. NEW pl classes: grammar_check items
presenting CORRECT Polish as broken (3x); English text inside
language_code: pl blocks; quote-vs-report deixis on reply exercises (3x).
All fixed (Sonnet fix agent, 140 tool calls), verified, flipped.
Manifests: en-de-b1 14u, en-ar-b1 6u, en-pl-b1 8u, en-ro-b1 9u,
en-hi-b1 9u. Corpus PASS.
Instance count: 28 findings.

### 2026-08-03 — nl A1 reading-track tap-to-gloss (units 06-72, 62 units) fresh-context review

Extended the reading tap-to-gloss track to the ENTIRE nl A1 tier (previously
0% glossed), authored by Codex in 7 waves and reviewed by 4 fresh-context
Claude agents (waves 1 / 2-3 / 4-5 / 6-7). Total review yield across all 62
units: **1 real learner-facing defect + 1 clarity note**, both fixed.
- Defect: a1_unit30 `eruit`->"like" — it is the separable particle of
  *eruitzien* ("Hoe zie jij eruit?" = what do you look like), not a standalone
  word. Fixed to "(part of 'eruit zien' = to look/appear)".
- Clarity note: `half` glossed "half past / half to the next hour" is ambiguous
  (Dutch half+N = half TO N; half acht = 7:30). Reworded across u10/u11.
Homograph handling was consistently correct throughout the tier (`was`=wash/
laundry not past-tense, `zin`=desire not sentence, `haar`=hair not her,
`brand`=fire, `Band`=music-group, `Regel`=rule, `lengte`=height, `Roman`=novel,
`boeken`=books-noun, `lijn`=leash) — the highest-risk class stayed clean. The
gloss recipe (established across A2/B1/B2, now proven on A1) is effectively
mature: ~1.6% defect rate, all low-severity. Validator: 0 errors / 0 gloss-key
warnings every unit. Commits: 00662de8, 437a79ef, 708d0c66 (+ 57523635, eruit fix).
Instance count: 2 findings (1 defect, 1 clarity).

### 2026-08-03 — en-es + en-fr reading tap-to-gloss (cross-language expansion) fresh-context review

Extended the reading tap-to-gloss track to Spanish (es: A1 13u + A2 10u + B1 16u
= 39 units) and French (fr: 9 units), authored by Codex, reviewed by 3 fresh-context
agents. **Total review yield: 0 defects across all 48 units.** Homograph/accent
senses all correct — es (`entre` subj vs prep, `mañana` morning/tomorrow, `fui` ir
not ser, `cuenta` account, `como`), fr (`est/et`, `a/à`, `ou/où`, `son/sont`,
`la/là`), B1 subjunctive/conditional forms (`sea`, `tuviera`, `pediría`, `hubiera`,
`viajaría`) all sense-accurate. The gloss recipe (nl-proven) transfers cleanly to
new Latin-script languages: cumulative ~1 defect / 150+ units across nl+es+fr.
Commits: es reading (pilot/w2/a2/b1), fr reading; dictation separate. b1_unit26 es
has no reading card (not glossed — none exists).
Instance count: 0 findings.

### 2026-08-03 — PRE-EXISTING es/fr realization debt surfaced (NOT introduced here)

Glossing/dictation surfaced pre-existing "tests tokens not introduced" realization
errors (a real content bug — exercises test un-taught words): es a1_unit09 (y),
a1_unit12, a1_unit13, a1_unit14 (quiero/un/tiene), es b1_unit27 (cita/documento),
b1_unit36 (que); fr a1_unit05 (oui). These predate this session and are unrelated
to the reading/dictation work; flagged for a separate es/fr realization fix. es A1
dictation for u09/u14 was SKIPPED (clean placement impossible while the debt exists).

### 2026-08-03 — en-ro + en-hi reading glosses fresh-context review (0 defects)

Romanian (12 units) and Hindi (30 units) reading tap-to-gloss reviewed by fresh-context
agents: **0 defects each.** ro: subjunctive `să`/conditional `ar`/imperfect-perfect forms
+ `nouă`/`noua` homograph all correct. hi (Devanagari): verb gender/number agreement
(गया/गई, करता/करती), polysemy (कल yesterday/tomorrow, पता address/know), compound-verb
scoping all correct. Cumulative reading-gloss review yield across nl+es+fr+ro+hi:
**~1 defect / ~180 units** — the recipe is language-agnostic and effectively mature for
tap-to-gloss on any whitespace-segmented script (Latin, Cyrillic-adjacent, Devanagari).

### 2026-08-03 — CORRECTION: the "token not introduced" debt was a phantom (validation-methodology artifact)

The two entries above recording "pre-existing es/fr realization debt" (and the
1441-error corpus scan behind them) were WRONG. Those scans validated each unit
IN ISOLATION; the introduced-token check is COURSE-cumulative, so single-unit
validation fabricates "tests tokens not introduced" errors for every word taught
in an earlier unit (es a1_unit09's `y` is taught in a1_unit02 `treinta y cuatro`).
The authoritative manifest-driven run (`verify.sh --content-only`) reports
**content: pass, ZERO not-introduced errors corpus-wide** — there is NO deploy-
blocking token debt in any language. Consequences fixed: es a1_unit09/14
dictations (skipped over phantom errors) restored; footgun recorded in
docs/content/CLAUDE.md ("validate the COURSE, not the unit, before acting on
token-coverage findings"). Codex's fake-teaching-card behavior remains a real
footgun regardless (fabricated introduced_tokens are wrong even when the error
they silence is phantom). All 0-defect gloss/dictation review results above are
unaffected (phantom errors only add false positives, never mask real ones).

### 2026-08-03 — en-de A1 units 01-10 fresh review (Opus) + same-day fix round

Fresh-context review found **10 findings (6 MAJOR / 4 MINOR)**. Units 02-05
were clean for unit-specific findings; they were affected only by the systemic
classes. The systemic grading class was missing ae/oe/ue/ss accepted-answer
variants for free-text answers containing German umlauts or ß (dictation stays
orthography-strict). The forward-reference matcher class placed lesson02/03
material in lesson01 matchers before it was taught. New author-side pattern:
matching_pairs LEFT/RIGHT descriptions authored in untaught target-language
German instead of the source language (units 06-10; units 01-05 correctly used
English). The same-day fix round added the transliterated free-text variants,
removed off-spec `correct_option` fields from all nine dictation overlays,
repaired the register distractors, converted affected matcher descriptions to
English, made the price-sign matcher coherent, and removed forward-referenced
rows where no later matcher slot existed to reuse. Fix round applied 2026-08-03.
Instance count: 10 findings (6 MAJOR / 4 MINOR).

### 2026-08-03 — token-debt fix (20 realizations + 22 overlay syncs, including launch-gate fa/prs) fresh-context diff review
Bug classes found: none blocking — **SHIP**; 2 LOW naturalness notes
New bug class discovered: no
Instance count: 2 LOW notes; 0 blocking defects

### 2026-08-03/04 — dictation wave fr/it/ru/de B1 + es A2 (113 exercises) fresh-context reviews
Bug classes found: none in scope — **SHIP all lanes**; 2 real out-of-scope
finds: Cafe/Café inconsistency in de B1 units 40/49, and the pre-existing
dictation terminal-punctuation mismatch class
New bug class discovered: no
Instance count: 0 in-scope defects; 2 out-of-scope findings

### 2026-08-04 — dictation gap-fill nl/de/es A1 + fr/it/ru A2 (36 exercises) fresh-context reviews
Bug classes found: none — **SHIP all 6 lanes**, 36/36
New bug class discovered: no
Instance count: 0

### 2026-08-04 — ar A1 dictation (12 exercises) fresh-context review
Bug classes found: none — **SHIP**, 12/12
New bug class discovered: no
Instance count: 0

### 2026-08-03 — matcher rewrite v1 (151 clues) fresh-context review
Bug classes found: validator-gaming variant — all 151 clues were letter-blank
answer-redactions; **REJECTED** and diff discarded. Mechanics were clean across
1,142 synchronization checks.
New bug class discovered: yes — constrained-authoring stylistic escape-hatch
degeneracy; recorded in the root CLAUDE.md footgun
Instance count: 151 rejected clues

### 2026-08-03/04 — matcher rewrite v2 (49 clues) fresh-context review + targeted v3 fix
Bug classes found: 40/49 clues good; 9 symbolic-notation clues rejected
(≠/</+/→). **FIX-FIRST narrow**: structure was clean across 188 synchronization
checks; the 9 clues were fixed in targeted v3 and shipped as `c8c3800a`.
New bug class discovered: no — second form of the matcher-rewrite
validator-gaming class found in v1
Instance count: 9 rejected and fixed clues

### 2026-08-04 — three new validators review-yield takeaway
Bug classes found: the validators surfaced **491 + 315 + 11 latent defects**
that no prior human pass caught. The 315 dictation-punctuation fixes remain
pending a grading-policy decision by Ramin.
New bug class discovered: no — aggregate validator yield and pending-policy record
Instance count: 817 latent defects surfaced; 315 fixes pending policy

### 2026-08-04 — dictation-tolerance grading diff (adversarial fresh-context review)
Bug classes found: **FIX-FIRST** — 4 findings: missing Arabic comma behavior
versus CONTRACT, dropped ZWNJ forgiveness, a missing empty-normalization guard,
and out-of-sync feedback. All four were fixed the same night; caller tracing
confirmed **NO scope leak**. Final verification passed with every item VERIFIED
by execution. One LOW CONTRACT harakat-example misstatement was also found and
fixed. Shipped as `4994f12d`.
New bug class discovered: no
Instance count: 4 grading findings + 1 LOW documentation finding, all fixed

### 2026-08-04 — content-import dictation exemption (`service.py`) fresh-context review
Bug classes found: none remaining — **VERIFIED**. Root cause was that the import
validator predated the dictation exercise type, producing a 422 during the
10-course dev sync.
New bug class discovered: no
Instance count: 1 systemic import-validation defect affecting the 10-course sync

### 2026-08-04 — pairs-override compiler feature fresh-context review
Bug classes found: none blocking — **SHIP**. The answer side was verified against
content, frontend, and grading behavior; both desynchronization guards were
present and verified. Shipped as `4c6c2c24`.
New bug class discovered: no
Instance count: 0 blocking findings

### 2026-08-04 — nl-en L1 pilot v1 fresh-context review
Bug classes found: **FIX-FIRST / BLOCKER** — mixed spine-pair orientation meant
that localizing `right` removed the English target from approximately 57
exercises. The reviewer found the defect by reading the frontend renderer's
contract; the Dutch language itself was excellent.
New bug class discovered: yes — display-affecting content changes can be locally
valid in YAML while violating the renderer's pair-orientation contract
Instance count: ~57 affected exercises
**RULE NOTE**: content reviews of display-affecting changes must include the
renderer’s contract, not just the YAML.

### 2026-08-04 — en spine orientation normalization (101 transposes) fresh-context review
Bug classes found: none — transpose-audited with zero warning deltas. **SHIP**.
Shipped as `81d01723`.
New bug class discovered: no
Instance count: 0 findings across 101 transposes

### 2026-08-04 — nl-en L1 pilot v2 fresh-context review
Bug classes found: none blocking — **SHIP**. All 65/65 exercises had the correct
orientation; 4 pre-existing instruction bugs were fixed. Unit 03 digit matchers
were deliberately left unlocalized. Shipped.
New bug class discovered: no
Instance count: 4 pre-existing instruction bugs, fixed; 0 orientation defects

### 2026-08-04 — fa-en L1 wave fresh-context review
Bug classes found: none blocking — **SHIP**. All 63/63 exercises passed, with
0 RTL defects and a clean colloquial register. The unit 20 comparative-degree
fix was applied post-review. Native-review queue notes: unit 18 `saw` gloss and
unit 12 circular definitions.
New bug class discovered: no
Instance count: 1 post-review comparative-degree fix + 2 native-review notes

### 2026-08-04 — prs-en L1 wave fresh-context review
Bug classes found: none blocking — **SHIP**. All 63/63 exercises passed, with
0 RTL defects and **ZERO Iranian-Farsi contamination**.
New bug class discovered: no
Instance count: 1 native-review NIT — bike-pedal phrasing

### 2026-08-04 — native-review queue
- Dutch A1 matcher clues: 63 exercises awaiting Ramin's native pass.
- Farsi A1 matcher clues: 63 exercises awaiting Ramin's native pass.
- Dari A1 matcher clues: 63 exercises awaiting Ramin's native pass.

### 2026-08-04 — de-en A1 German + nl/fa/prs-en A2 L1 matcher-clue wave (fresh-context review)
Bug classes found: none — **SHIP all 4 lanes**. Orientation 13/13 + 48/48
byte-parity, RTL clean, register separation verified. Shipped as `29fc6660`.
New bug class discovered: no
Instance count: 0

### 2026-08-04 — nl/fa/prs-en B1/B2 L1 wave + spine pair restoration (fresh-context review)
Bug classes found: none — **SHIP both parts**. 195/195 overlay parity, 38
spine exercises restored with 0 consumer coverage gaps, all 75 restored words
traced to the pre-drop base (0 smuggled), colloquial-Farsi vs Kabuli-Dari
separation verified by differential lexeme scan. Shipped as `1be1f49f`.
New bug class discovered: no
Instance count: 0
**MILESTONE**: the matching_pairs untaught-token defect class (§1.7/1.8/1.19/
1.23 lineage) is EXTINCT corpus-wide, validator-enforced against regression.

### 2026-08-04 — process note: Auvel rebrand caught only by live browser render
Bug classes found: none new — process note, not a content review. Full build
+ grep were green while the login h1 still rendered the old brand; the string
lived in `packages/shared` i18n locales, outside the change-agent's scope, and
was caught only by live browser render.
New bug class discovered: no
Instance count: 1 process-verification gap (build/grep clean, live render stale)
**RULE NOTE**: reinforces "reading a diff is not verification" — live browser
render is the only backstop for strings living outside a change agent's
declared file scope.

### 2026-08-04 — native-review queue (update)
Supersedes the queue recorded in the 2026-08-04 "native-review queue" entry
above. Current state: nl/fa/prs ~62 localized matchers per lane (A1-B2) +
de-en A1 (9) — all awaiting Ramin's post-hoc native-language audit.
New bug class discovered: no
Instance count: 0 (queue status update, not a review)

### 2026-09-29 — fa A1 dialogue-audio pointers (PR #10, 42 items; fresh-context review)
Bug classes found: 1.22 (distractor weakened/made contestable by newly attached
dialogue audio) — 2 nits (unit41/unit42 distractors); plus 1 out-of-scope
finding: fa unit01 `listen_who_welcomes` had no question (prompt-less item).
0 blocker, 0 should-fix. All fixed in commit b80c9044.
New bug class discovered: no
Instance count: 3 (2 nits + 1 out-of-scope), all fixed
**RULE NOTE (candidate)**: audio added to an existing item can make a
distractor true — re-review distractors whenever audio is attached.

### 2026-09-29 — prs A1 dialogue audio (PR #11, 14 items; fresh-context review)
Bug classes found: 1.22 — 1 should-fix, pre-existing: prs unit15 distractor
made TRUE by the attached audio (mirrored in fa unit15); 2 nits (1 fixed: false
"in Kabul" feedback). 0 blockers. Fixed in commit b80c9044.
New bug class discovered: no
Instance count: 3 (1 should-fix + 2 nits; fa unit15 mirror fixed with it)
**RULE NOTE (candidate)**: same as above — re-review distractors whenever
audio is attached to an existing item.

### 2026-09-29 — es-b1 + de-b1 CI corpus test (answer-shape corpus test)
Bug classes found: 1.26 (answer-shape corpus regression) — 2 real defects:
es.b1.unit40 reading_comprehension had no options; de.b1.unit42
matching_pairs had casefold-duplicate right items. Fixed in commit fa44f6a1.
New bug class discovered: no (instances of §1.26; compiler-invisible, caught
only by the answer-shape corpus test once the dictation shape was added)
Instance count: 2

### 2026-09-29 — fa+prs A2 dialogue-audio pointers (PR #13, 32 items; fresh-context review)
Bug classes found: none — 0 defects (8 items skipped at authoring; the 4
unit14 job-interview items are now wired, the ZWNJ speaker-label blocker being
fixed in commit 5a4ab3c1; a fresh review confirmed the audio supports each
correct option and no distractor)
New bug class discovered: no
Instance count: 0

### 2026-09-29 — nl C1 production rewrite (PR #16, 112 items; fresh-context review)
Bug classes found: missing natural accepted variants on underdetermined
production items (word order / synonym / optional particle -- e.g. op-particle
placement, benoemen for noemen, wellicht for misschien, ook after daarbij) ;
feedback/grading contradiction (unit06 lesson02 accepted a non-standard direct
quote while feedback claimed direct quotes work); dictation internal-punctuation
strictness (unit04 lesson06 two-sentence dictation, ". Toch" vs ", toch" is a
false-negative risk under strict grading). 0 blocker, 7 should-fix, 5 nit.
All fixed in this change (dictation cut to one sentence; instruction pinned to
"behoorlijk" in unit02 lesson04; "Say" -> "Write" on a writing_prompt).
New bug class discovered: no (instances of underdetermined production and
dictation punctuation strictness)
Instance count: 12 (7 should-fix + 5 nits), all fixed
Note: unit07 lesson06 dictation keeps the optional comma before "maar" (nit 8);
removing it would change meaning/audio, left as is.

### 2026-09-29 — prs توانستن full-form standardization (PR #19; fresh-context review)
Bug classes found: register/form standardization incomplete across the verb's
derivatives -- PR #19 converted the present tense to the full form but left
the past/negative past contracted. 3 learner-facing should-fix: (1) b1_unit01
teaching notes made false by the form change (نتانستم "negates می‌توانستم",
"add -ستم to می‌توان ... نتانستم", grammar_review) ; (2) rule/answer-key
disagreement on the negative past (canonical answers accepted only the
contracted نتانستم/نتانست while the present was full) ; (3) en-prs b1_unit02
grammar_agreement claimed the باید endings "م/ی/ه/یم/ین/ن" were what
"you already know from می‌توانم" (false: full form is م/ی/د/یم/ین/ند). 2 nits:
DARI_REGISTER_REPAIR.md mapping table still mapped to می‌تانین/می‌تانم; stale
می‌تانم/می‌تانین YAML comments in practice a1_unit10/21/23. All fixed in this
change (past + negative past converted to full forms with contracted forms kept
as extra accepted answers; b1_unit03 negation note also updated).
New bug class discovered: no (instance of a form-change consistency defect)
Rule candidate: a register/form standardization must include every
tense/derivative of the verb and every note that references the old form.
Instance count: 5 (3 should-fix + 2 nits), all fixed

### 2026-10-10 — en-nl C1 practice packs + C1 lexeme backfill (8 packs, 174 templates; fresh-context review)
Scope: the first C1 practice tier (docs/content/practice/en-nl/c1_unit01-08) and
the C1 extension of scripts/backfill_lexemes_en_nl.py (676 C1 lexemes). One
read-only reviewer per unit (content-reviewer.md), zero access to authoring.
Per-unit yield (findings / blockers): u01 8/1, u02 17/5, u03 16/7, u04 12/3,
u05 12/3, u06 15/5, u07 17/7, u08 20/4 -- total 117 (35 blocker, 82 minor).
Bug classes found (all slipped a 0-error practice-validate):
- **Typed-translation synonym ambiguity** (dominant): a bare-word translation
  shows the gloss and grades the typed token by exact match, so any gloss an
  equally correct Dutch word also answers fails correct learners (wellicht /
  misschien, noodzakelijk / nodig, serieus / ernstig, helder / duidelijk,
  chef / baas, ga / gaan, "maak (with je)" -> je maakt). Includes the
  CROSS-UNIT form: two C1 lexemes with identical glosses in a course-scope pool.
- **Open fill_in_blank**: the runtime shows no English cue, so a blank that is
  not inside a fixed idiom admits several correct words (dat zegt
  genoeg/alles/veel). Fixed by converting to word_order on the same anchor.
- **Self-quoting glosses**: backfill glosses carrying their own idiom in Dutch
  ("lines (in 'in grote lijnen')") give the answer away in MC/matching/
  translation; identical cognates (plan, mild, warm, ring) likewise.
- **Under-pinned fixed-sentence translations** (besluit/beslissing, bezorging/
  levering, werkende mensen/werkenden).
- **Over-claiming feedback_frame** ("{item} is a word from Omar's speech" for
  pool members that are not).
All fixed (regloss where an honest gloss pins the token, otherwise the token
leaves the translation pool via curated c1u<NN>_ tags); a pool-level scan of
every gloss-showing slot at unit and whole-C1 scope confirms 0 self-quoting,
0 duplicate glosses, 0 typed-translation tokens sharing a gloss with another C1
lexeme. Re-review not yet run on the fixed packs.
New bug class discovered: no new class -- but **rule candidates** for the
validator backlog (Codex lane): (1) practice-validate should flag a gloss that
contains its own token; (2) it should flag a bare-word translation slot whose
course-scope pool has two members with identical glosses; (3) it should flag
fill_in_blank frames whose single anchor is not inside a declared fixed idiom
(or simply warn on every fill_in_blank, since no cue is shown).
Tooling gaps confirmed: _practice_content_integrity_check.py /
_fill_in_blank_ambiguity_check.py still glob a*_unit*.yaml and skip every
c1_ pack (defect-1.14 self-reference checked by hand: 0 instances).
Instance count: 117, all addressed.

### 2026-10-10 — Dutch-direction review backlog: 161 files (fresh-context review, 34 parallel reviewers; branch content/review-backlog-dutch)
Scope: every `review.status: unreviewed` file in the Dutch directions except
the shared English realizations — practice/en-nl 64, practice/nl-en 36,
overlays/nl-en 27, overlays/en-nl 17 + realizations/nl 17. fa/prs untouched;
en-nl C1 practice packs and lexemes untouched (owned by another session).
Checklist: `.claude/agents/content-reviewer.md` + OVERLAY_REVIEW_INSTRUCTIONS
+ PRACTICE_PACK_RECIPE; practice pools checked against real `iter_specs()`
data at unit AND course scope.
Bug classes found: 1.21 (missing valid accepted answers: contractions,
V2/word-order variants, je/jij, taught synonyms — the largest class, ~120),
underdetermined production prompts (instructions that never named the
content/form graded, ~35), confusable matching_pairs sides (omdat/want,
allebei/beide, stijgen/groeit, although/even though, envelope/mailbox, ~15),
1.17-family double-correct distractors and synonym pools (moet/moeten,
betalen/afrekenen, rooster/agenda, Appartement/appartement, city/town,
bakker/bakkerij, ~25), 1.16 ambiguous fill_in_blank frames (~12), untaught
vocabulary in practice frames (~10), ungrammatical rendered frames ("I'd
like a bread", "Het is kwart over 14", "Ze vinden mijn.", "a the coat", ~15),
wrong glosses/senses (postbus, opwarmen, daarentegen="on the contrary",
works="komt uit", Van="Of", calm definition, ~20), keyed answers false
against the text/audio (en-nl b2_unit05 read_signal and
comprehend_register_fit), distractors also true per the audio (1.22, 4),
character-canon (en-nl a1_unit17 "Lotte werkt als kok"), false grammar notes
(~10), 1.12 unquoted booleans (2), and new classes 1.40 and 1.41 (~150
feedback frames).
New bug class discovered: yes — §1.40 (article/contraction glosses vs single-
answer practice translations) and §1.41 (false practice feedback frames,
latent). Pack-authoring lane note: the 2026-07-12 "3 consecutive zero-defect
reviews → eligible for 1-in-3 sampling" call for the pack lane does NOT
survive this review (~180 pack defects across 100 packs); keep packs at Full.
Instance count: ~383 fixed (en-nl practice 138, nl-en practice 39, nl-en
overlays 115, en-nl overlays + nl realizations 91), 35 native-judgment flags
recorded in the files' notes for Ramin's pass, deferred items below.

Per direction/level (files reviewed → fixed):
- en-nl practice: A1 39 → 90 · A2 7 → 15 · B1 10 → 13 · B2 8 → 20
- nl-en practice: A1 19 → 24 · A2 8 → 8 · B1 1 → 3 · B2 8 → 4
- nl-en overlays: A1 11 → 34 · A2 8 → 45 · B1 8 → 36
- en-nl overlays + nl realizations: A2 (unit78 pilot) 2 → 1 · B2 16 → 64 · C1 16 → 26

**Deliberately NOT fixed (deferred), 2026-10-10** — each is recorded in the
affected file's `review.notes`:
1. *Lexeme glosses in `scripts/backfill_lexemes_en_nl.py` (off-limits to this
   run; en-nl C1 lexemes are owned by another session)*: §1.40 "the X" noun
   glosses (course-wide); `gedaan`/`klaar` both "done"; `schrijf` "prescribe;
   write"; `bakken`/`bak` "bins/bin" in the cooking unit; `Ze` "she" (rejects
   zij); `bakker` "the bakery" = `bakkerij`; `Politie`, `Telefoon`,
   `Medewerker`, `Huisarts`, `Vrijdag`, `Jij`, `Je` capitalised duplicates;
   `Opa` in the person_name pool; `voor` lacks "in front of"; `aankleden`
   "to get dressed" (needs zich); `bezoek` noun gloss in a verb unit;
   `één` renders "one euros"; `Kan`/`Zullen` vs kun/zal; `zoekt`; `kent`/`weet`;
   `Van` "Of" (u73, worked around); `Kan`/`kunt`; `goede`/`belangrijke`,
   `ga`, `heb`, `kun` bare glosses on inflected forms; `vragen`, `agenda`
   senses (B1); `moet`/`moeten`, `ben`/`zijn` overlapping glosses (B1/B2);
   `jou`, `Beste`/`Geachte`, `alleen` "alone" (taught "only"), `helft`,
   `beide`/`allebei`, `wat` "what" (taught "something"), `zit`, `vast`/`zeker`,
   `misschien`/`wellicht`, `zin`, `best`/`nogal`, `vertrok`/`vertrokken`,
   `miste`/`gemist`, `was`/`heb`/`gekomen` (B2). `waar` "where" is still in the
   data but no reviewed template can reach it.
2. *Lexeme glosses in `scripts/backfill_lexemes_nl_en.py`*: A1 `wake`, `up`/`on`
   ("op"), `usually`/`mostly`, `1pm`, `6pm`, `maybe`/`might`, `love` ("graag
   willen"), `don't` ("niet leuk vinden"), `doesn't`, `need`, `if`/`as`,
   `directions` ("route"), `slowly` ("langzamer"), `speak` ("praten"), `about`
   ("wat dacht je van"), `meeting` ("afspraak"), `test` ("examen/toets"),
   `max's` lowercase, `waste`, `kinds`, `loved`, `view`, `being`; A2 `next`
   ("naast"), `small` ("kleine maat"), `looking`, `too` ("ook"), `staying`,
   `post`, `lot`, `effects`, `pick`, `shouldn't`, `fixed` ("vast"), `yet`,
   `put`, `sent`, `can't`/`won't`; B1 `desk` ("balie"), `works` ("komt uit",
   worked around), `coworker`/`colleague`; B2 `like`, `quarter`, `meeting`,
   `review`, `claim`, `looking`, `must`, `run`, `rules`, `might`, `cannot`,
   `tentative`, `gone`, `been`, `present`, `written`, `different`, `isn't`,
   `moved`, `entered`, `got`, `had`, `rain`, `simple`, `shift`, `person's`,
   `push`, `account`, `name`, lowercase weekday tokens.
3. *Engine limitation*: practice `translation` templates hold one answer
   string, so equally correct word orders / synonyms / contractions are
   rejected in ~15 fixed-sentence templates (listed per pack in notes).
4. *Shared English realization (`realizations/en/**`, consumed by nl-en,
   fa-en, prs-en, de-en — out of this run's scope)*: a1_unit30 "watch video
   games", "goes painting"; a1_unit40 match_post_words confusable meanings;
   a1_unit41 "This soup needs you to add some salt."; a1_unit42 calm
   definition and Mia asking "What's he like?" about her close friend
   Daniel; a1_unit45 ungrammatical ", and send" accepted answers;
   b1_unit13 who/that match rights; b1_unit15_complaints is itself still
   unreviewed (63 English realizations remain `unreviewed`).
5. *Content calls left for a decision*: British spelling ("favourite colour")
   not accepted anywhere in nl-en (course teaches US English); en-nl
   b2_unit04 listen_wekker distractor and "too late for the station" gloss;
   en-nl c1_unit05 Omar's five-years-ago Amsterdam job vs his Utrecht
   timeline (soft canon tension); en-nl a1_unit42 lesson05 fill "op de ___"
   (markt also fits); 9 matching_pairs sets still below the 6-pair floor
   where the unit pool is too small (en-nl a2_unit75/77, nl-en a1_unit08).
6. *Tooling*: `_practice_unit_scope_check.py` (like the integrity and fill
   checks) globs `a*_unit*` and silently skips every b1/b2 pack.

### 2026-10-11 — en-nl C1 practice packs + C1 lexemes: SECOND fresh-context review (8 packs; branch content/en-nl-c1-review2)
Scope: docs/content/practice/en-nl/c1_unit01-08 and the C1 block of
scripts/backfill_lexemes_en_nl.py, re-reviewed after the 2026-10-10 fixes. One
fresh reviewer per unit with NO access to the authoring notes or the first
review (review.notes stripped, registry/git history off-limits), working from
real course-scope candidate pools rendered from iter_specs(); then a third
fresh-context verification pass on the fixed packs.
Second-review yield (findings / blockers): u01 24/10, u02 16/3, u03 19/3,
u04 28/13, u05 15/2, u06 18/4, u07 9/0, u08 17/5 -- total 146 (40 blocker).
Third-pass yield on the fixed packs: u01 7/2, u02 3/0, u03 4/0, u04 9/1,
u05 5/0, u06 2/0, u07 4/0, u08 0 -- total 34 (3 blocker), all fixed.
By category (second review, approx.): typed-translation alternatives ~95
(of which the "the X" article gloss class in every unit, ~150 lexemes),
lexeme gloss/sense/POS ~25, false feedback ~10, word_order alternative
orders ~20 (deferred, engine), open fill blanks 3 (+1 native flag), duplicate pools 3,
gloss-reveals 3, wrong English/grammar feedback 3.
Bug classes: no new class. The dominant class is again typed-translation
synonym ambiguity -- the first review's fix pass fixed the listed tokens but
the same class remained in ~60 other pool members, i.e. the first pass fixed
instances, not the class. Also 1.40 confirmed in C1 (every unit).
Fixes: (1) C1-scoped backfill rule nl_c1_bare_gloss drops a leading English
"the" from every C1 noun gloss (151 lexemes; A1-B2 specs verified byte-
identical); (2) ~75 tokens taken out of translation (or matching) pools (kept for MC and
matching where safe) and ~70 glosses narrowed; (3) 3 open fill_in_blank frames converted
to word_order (u05 lesson03/06, u06 lesson01), 3 fixed sentences pinned; (4) duplicated
template pools split (u02 by part of speech, u03 and u05 by lesson half);
(5) false feedback and grammar notes corrected. Pool scan after fixes: 0
duplicate glosses in any MC/matching/translation pool, 0 self-quoting
glosses, 0 translation tokens sharing a gloss alternative with another C1
lexeme except form-cued pairs (vaste/vast, moet/moeten).
Status: u08 -> reviewed (third pass clean). u01-u07 stay unreviewed: their
third pass found defects (fixed), so each needs one more clean pass.
Native-judgment flags for Ramin are recorded per pack in review.notes.

**Deliberately NOT fixed (deferred), 2026-10-11:**
1. *Engine limitation*: practice word_order and fixed-sentence translation
   accept one string. Equally valid alternative orders remain graded wrong
   (the word_order hint line shows the expected order, which mitigates):
   u01 lesson01.order.002 / lesson06.order.003; u03 lesson05.order.004 /
   lesson03.order.003; u04 lesson04.order.002 / lesson05.order.002 /
   lesson02.order.003; u05 lesson02.order.003 (feedback softened);
   u06 lesson04.order.003 / lesson03.order.002; u07 lesson03/05/06 order
   templates; u08 lesson01.order.003 / lesson02.order.002 / lesson04.order.003.
   Fix needs an `accepted` list on practice templates (Codex lane).
2. *Stray generic semantic tags on C1 lexemes* (ordinal_number on -de/-te
   words such as wilde, woonde, belangrijkste, waarde, Beste; weather on weer;
   work_vocab on beroep): latent, no C1 template selects them. A C1 template
   that ever selects those tags would leak them -- clean up in nl_agreement_tags.
3. *u02 lesson01.choose.001* (c1u02_kern, all parts of speech) still overlaps
   the other u02 MC pools (repetition only, nothing graded wrong).
4. *Out of scope (overlay)*: overlays/en-nl/c1_unit06 lesson02 dialogue line
   renders Dutch "chef" as English "chef" (false friend; means boss).
5. *Tooling (unchanged)*: _practice_content_integrity_check.py /
   _fill_in_blank_ambiguity_check.py / _practice_unit_scope_check.py glob
   a*_unit* and skip every c1_ pack.
Rule candidates (validator backlog, Codex lane): flag a bare-word translation
gloss that starts with "the"; flag a C1 translation pool member whose gloss
alternative equals any gloss alternative of another lexeme in the course.

### 2026-10-17 — remaining review backlog: en-de/it/ru/ro/es/fr + shared English (87 commits, fresh-context review; branch content/review-backlog-rest, PR #31)
Scope: the `review.status: unreviewed` backlog outside the Dutch directions
and outside the en-nl C1 packs — overlays + realizations for en-de (A1
u01-10, B1 u35-53, B2, C1), en-it (A1 u19-24, A2, B1, B2, C1), en-ru (A1
u19-24, A2, B1, B2, C1), en-ro (A1 u20, A2 u21-26, B2, C1), en-es (A1
u04-15, A2 u16-21, B2 u01-03, C1 u02-04 + u08), en-fr (A1 u04-14, A2 u15);
the shared English realizations (`realizations/en/**`, A1 u01-68, A2
u25-40, B1 u15-19) with their nl-en/fa-en/prs-en/de-en overlays; plus
en-nl practice A1 u12-13. ~660 files touched.
Checklist: `.claude/agents/content-reviewer.md` + OVERLAY_REVIEW_INSTRUCTIONS
+ PRACTICE_PACK_RECIPE.
Bug classes found: reading/comprehension questions that never showed the
notice, sentence or passage they ask about (the most widespread class, every
direction); 1.21 missing valid accepted answers (word-order variants,
gender/formality variants, du/ihr, ё/е spellings, taught synonyms,
contractions); underdetermined open speak/write prompts graded against one
exact text (now pinned or given the model text); answers given away by the
prompt, the option's punctuation or by being the only plausible option;
1.17-family second-correct distractors and interchangeable matching pairs;
wrong comprehension keys and listen distractors the audio actually says
(1.22); false grammar/register notes (en-de Präteritum/Perfekt
"background/foreground" rule, en-ro -ul vs -i and puteți "conditional",
en-es quisiera, en-fr partitive, en-ru register claims); illogical or
garbled lines (en-de "noch nicht zu Hause", "kommt an auf"); character-canon
slips (en-es Elena location, en-fr contradictions); translation
target_blocks that printed the answer (shared English A1 u39-68); missing
overlay entries and internals/placeholder `review.notes` rewritten.
New bug class discovered: no — all instances fit existing classes.
Instance count: 842 fixes counted in commit subjects (59 commits); 28 further
commits (all en-es and en-fr, most en-ru B1 u40+, en-ro C1 u04-08 and B2
u06-08, two notes/answer-leak sweeps) list fix categories but no count.

Per direction/level (commits → fixes counted in subjects; "+n" = commits
without a count; mixed-level commits shown under both levels joined):
- shared en (+ nl/fa/prs/de-en overlays): A1 10 → 148 (+1) · A1+A2 1 → 13 ·
  A2 2 → 19 · B1 1 → 9 — total 189
- en-de: A1 3 → 53 · A1+B1 1 → 19 · B1 5 → 48 · B1+B2 1 → 11 · B2 2 → 65 ·
  B2+C1 1 → 6 · C1 3 → 56 — total 258
- en-it: A1 2 → 27 · A2 3 → 18 · A2+B1 1 → 9 · B1 6 → 32 (+1) · B1+B2 1 → 21 ·
  B2 2 → 47 · B2+C1 1 → 27 · C1 2 → 18 — total 199
- en-ro: A1+A2 1 → 38 · A2 1 → 20 · A2+B2 1 → 24 · B2 2 → 12 (+1) ·
  C1 3 → 12 (+2) — total 106
- en-ru: A1 2 → 12 · A2 3 → 36 · A2+B1 1 → 22 · B1 5 → 12 (+4) · B1+B2 (+1) ·
  B2 (+2) · B2+C1 (+1) · C1 (+2) — total 82
- en-es: A1 (+4) · A2 (+2) · B2 (+1) · C1 (+2) — no counts in subjects
- en-fr: A1 (+3) · A1+A2 (+1) — no counts in subjects
- en-nl practice: A1 1 → 8

Remaining: en-fr A2 u16 onward through C1 (~47 units), not reviewed — run
cut off.

### 2026-10-17 — en-fr review backlog completed: A2 u16-20 + B2 u01-08 (fresh-context review; branch content/review-backlog-en-fr, PR #32)
Scope: continues the 2026-10-17 section above, which ended "en-fr A2 u16
onward through C1 (~47 units)". On disk, the actual `review.status:
unreviewed` en-fr set was 26 files (13 units: A2 u16-20 and B2 u01-08,
realization + overlay each). en-fr B1 u25-43 and C1 u01-08 were already
`reviewed`, and en-fr has no practice packs, so "~47" overcounted. All 26
files are now `reviewed` (`required_next_reviewer: native_speaker_pass`
kept where present), and each has a dated paragraph in `review.notes` with per-fix detail,
native flags and deferred items.
Checklist: `.claude/agents/content-reviewer.md` +
OVERLAY_REVIEW_INSTRUCTIONS. Five fresh (non-fork) reviewers, one per batch
of 2-3 units, run in parallel on disjoint files. Each reviewed and fixed its
own files and ran the course-scoped validator. The coordinator committed
each batch with explicit pathspecs.
Instance count: 135 fixes.
- A2 u16-18: 27 (u16 11, u17 9, u18 7)
- A2 u19-20: 19 (u19 10, u20 9)
- B2 u01-03: 34 (u01 10, u02 13, u03 11)
- B2 u04-06: 28 (u04 9, u05 12, u06 7)
- B2 u07-08: 27 (u07 18, u08 9)
Categories (approximate, from the reviewer reports):
- 1.21 missing valid accepted answers: ~47. Covers gender agreement
  (convaincue, productive, impressionnée), on/nous, ça/cela, tu/vous where
  the prompt left register open, clause/word order, taught synonyms (ensuite,
  alors que, je voudrais, Ça fait...que), and with/without Bonjour.
- Underdetermined open prompts pinned to the form they grade: ~22.
- False or incomplete grammar/usage notes and glosses: ~26. Examples:
  - "vous forces inversion"
  - je crains que ne...pas called an expletive
  - si + present -> conditional as "the standard si-clause"
  - sans doute = "almost certainly"
  - the passé composé for "il était huit heures"
  - je trouve que "never" subjunctive
  - enroué agreement
  - "ça fait trois jours que" glossed backwards
  - depuis hinted as "(since)"
  - il faudrait que = "someone would need to"
  - avant que with the same subject in both clauses
- Reading questions that never showed their passage: every B2 unit's
  lesson05 read_* set (8 units, ~32 exercises) plus A2 u20's job posting.
  This is the same top class as the earlier section.
- Confusable matching_pairs lefts / second-correct distractors /
  give-aways: ~14. Includes cependant vs pourtant, assez vs plutôt,
  par contre vs en revanche, A2 u19-20 options where only the key appeared
  in the prompt sentence, and "Bises, Inès" printed in its own prompt.
- Listen/audio mismatches: A2 u19 listen_eau_chaude heard "d'eau chaude";
  in B2 u07 a distractor was something Lefebvre actually says.
- Unnatural French: amener -> apporter for documents (the u15 carry-over in
  u17), "Bonjour Mademoiselle", "Pourriez-vous m'expliquer si", a double
  "Mais...cependant", and a certes...mais line that did not push back.
- Canon: the A2 u17 bank advisor was "Camille", who is Inès's sister in A1
  u03. Renamed to Mme Garnier; the reviewer's first pick, "Lefèvre", is a
  homophone of her boss Lefebvre. Also fixed: "Inès's shop" (she works for
  Lefebvre), "early twenties" (canon: 31), and B2 u02 reading questions
  about Inès, who is not in that text.
- Learner-visible leaks: "flagged for native review" in a B2 u05 note,
  internal "unit01-14" references in A2 u20 notes, and false "first A2 unit"
  / "first vous" claims.
New bug class discovered: no. All instances fit existing classes.

**Deferred (not fixed):**
1. *B2 u07 Sunday logic/canon.* Lefebvre proposes making up hours "le
   dimanche", but the unit's own card says "Le dimanche, la boutique est
   fermée", and A2 u20 settled Sundays off. The authoring notes say Sunday
   was meant to be considered and declined. Inès's refusal ("pas possible
   pour moi") sidesteps the closed-shop fact, so this is a native/owner call.
   Rewording spans dialogue, audio and several tested_text/accepted
   answers.
2. *B2 u01 "cela n'empêche pas que" + indicative* ("tu peux") runs through
   the reading, dialogue, audio and word_order tiles. Careful French wants
   "tu puisses"; the note now says so, but the switch needs a native call.
3. *A2 u20 story order.* The job interview comes after u17-19, where Inès
   already holds the apprenticeship. The description was reframed as a
   look back; a reorder or reframe is structural.
4. *Engine limitation.* Alternative word_order answers raise compiler
   warnings, so valid alternative orders were not added there (B2 u01).
5. *Course-wide pattern.* Context-sentence MC items (A2 u16 l01/l02 ex01)
   show the keyed phrase inside the prompt sentence. Kept, as in the u15
   review.
6. Only the first overlay's course.description is used by the compiler.
   The u16-20 descriptions were fixed anyway, but are not learner-visible.
7. A2 u20 `answer_policy.formal_register` still says "unit01-14" (grading
   metadata, not learner-visible).
Native flags for Ramin are recorded per file in `review.notes`. The main
ones:
- calques: "désolé d'entendre ça", "je comprends ton point"
- "De l'autre côté" with no "d'un côté"
- "Il peut être dans les embouteillages"
- the French grammar_certitude text still ranking sans doute above
  probablement
- expletive ne at A2 ("avant que vous ne receviez")
- "vous vous reposiez la voix"
- libre = tu / disponible = vous presented as a rule
- B2 u04 pendant que / alors que pair (both "while")

Remaining: the en-fr unreviewed backlog is now empty (A1-C1). No en-fr
file has had a native-speaker pass. Many carry a `required_next_reviewer`
value naming that pass or a native-French priority list.

### 2026-10-17 — it + ru review backlog, round 2: en-it/it and en-ru/ru A1 u19 → C1 u08 (fresh-context review; branch content/review-backlog-it-ru, PR #33)
Scope: every file whose top-level `status` was still `unreviewed` — 43
realizations + 43 overlays per language (86 Italian, 86 Russian): A1 u19-24,
A2 u25-34, B1 u35-53, C1 u01-08. Earlier rounds had already filled
`review.notes` and set `review.status: reviewed` but never flipped the
top-level `status`; this round re-reviewed each unit in a fresh context (one
worker per batch of 3-4 units, realization + overlay together) and set
`status: reviewed`. Checklist: `.claude/agents/content-reviewer.md`.
Bug classes found: 1.21 missing valid accepted answers (by far the most
common: alternate word orders, "Здравствуйте"-vs-"Добрый день" greetings,
article-less / comma / ё-е spelling variants, pronoun-less ru forms);
confusable matching_pairs (it B1 u38, C1 u04, u05); distractor that is also a
correct answer (it A1 u23 "chi parla?"); untaught words in teaching-card
examples (it B1 u41-42; ru A1 u19-21); orthography ("dì che" for "di' che",
it A2 u25/27/31/32/34); prompts that gave the answer away or described it
underdeterminately (ru C1 u03, u04); instruction/answer-key person mismatch
(it A2 u33); misleading gloss (ru B1 u50 "Could you (not)"); content_key typo
(it A2 u33 `exercise01_choose_weekend`). New bug class discovered: no.
Instance count (fixes per level; commit subjects carry the per-batch counts):
- en-it/it: A1 1 · A2 11 · B1 6 · C1 5 — total 23
- en-ru/ru: A1 17 · A2 12 · B1 7 · C1 16 — total 52
Deferred / owner decisions (not fixed here):
- ё/е equivalence is absent from grading (`backend/app/review/grading.py`);
  strict dictations containing ё (ru A2 u25/27/29, B1 u43/46, C1 u03/u05/u06)
  mark an е-typist wrong. Backend lane decision.
- Unused dialogue-audio assets with incoherent text or wrong voice_hint
  (it A1 u19 `viaggio_roma`, A1 u24 `pagare_carta`); ru B1 u50 card names Дима
  with a female voice; ru B1 u53 lesson03 needs audio + 4 exercises changed.
- it C1 u02 / ru C1 u02 need a re-author (structure, CEFR fit, key naming);
  ru C1 u02 Дима/Настя canon slip needs regenerated audio.
- Dictation overlays using `correct_option` instead of `correct_response`
  (it A2 u29-30, u34) — matches earlier units; shape normalization pending.
- Italian writing_prompt target_blocks use untaught meta-words; it C1 u08
  four copy-task writing prompts; ru B1 grammar-card metalanguage tokens.
Native-speaker flags (recorded in each file's review.notes): it B1 u35
"avrei potuto fare in modo che … ricevesse", u46 "se ero in te", u53 "capisco
il tuo punto"; it C1 u01 "fa bene", u04 "pesa meglio"/"il remoto"; ru B1 u46
"Я хочу, чтобы вы…" register, u51 вы/ты scene logic; ru C1 u05 narrative
coherence, u06 "avere le mani in pasta"-type idiom nuance (it) / snow idiom
(ru), u08 "Здесь дышит весь район".
Remaining: nothing unreviewed in en-it/it or en-ru/ru.

### 2026-10-17 — en-pl / pl review backlog: 104 files, 52 units (fresh-context review, 15 parallel reviewers; branch content/review-backlog-polish, PR #34)
Scope: every `review.status: unreviewed` file in `docs/content/overlays/en-pl/`
and `docs/content/realizations/pl/`. That is A1 u01-19, A2 u21-26, B1 u09-19,
B2 u01-08 and C1 u01-08, each unit's realization and overlay reviewed
together (52 units, 104 files). Note: 44 realizations used the quoted form
`status: "unreviewed"`, so a grep for the unquoted form undercounts this
backlog as 44 + 8. All 122 en-pl/pl files are now `reviewed` with
`required_next_reviewer: native_speaker_pass`.
Checklist: `.claude/agents/content-reviewer.md` + OVERLAY_REVIEW_INSTRUCTIONS.
Every batch was validated course-scoped (validate + compile, 0 errors).
Two coordinator follow-ups also touched 9 already-reviewed files (A1 u20,
B1 u01-08), for the same defect classes.
Bug classes found:
- Multiple-choice prompts that printed their own answer (largest class, new
  to en-pl). In every A1/A2/B1 `select_*` multiple_choice, `prompt.target_blocks`
  was the correct option. The compiler renders target_blocks as visible
  `text_blocks` above the options (confirmed in compiled output and
  MultipleChoice.tsx). 329 items in 45 files: 22 fixed by a reviewer, 307
  by a scripted sweep (A1 133, A2 42, B1 132; 64 of the 307 in the 9
  previously-reviewed files).
- 1.21 missing valid accepted answers: Polish word-order variants,
  feminine/masculine speaker forms, Pan/Pani, pronoun-dropped forms,
  kiedy/gdy, aspect and short-reply variants.
- Underdetermined production prompts: "write about your own…" or "write the
  exact model sentence" graded against one string; unpinned speaker gender.
  The English task text sat in pl target_blocks in B1 u07-11 and u16-19.
- Comprehension without its text: B2 u01-08 lesson05 reading items showed
  only the English question; A2 reading items showed only a question; C1
  `recognize_calosc` said "Listen" with no audio or text.
- C1 teaching-card glosses that repeated the Polish verbatim (all 8 units,
  ~90 cards). Learners were never told what the phrases mean.
- False grammar notes. Examples: dom→domu "ends in a consonant"; może
  "unrelated to" mogę; gender past "by person"; "Gardło boli" and other
  grammatical sentences presented as errors in A1/A2 grammar_checks; mógłby
  "used by a man"; kiedy=moment vs gdy=habit; "no ordinal platform numbers";
  comma rules for chociaż/więc/poza tym.
- Character canon:
  - Ewa = coffee and Marek = tea, swapped in A1 u13-14.
  - Marek's house vs Ewa's flat in A2 u25.
  - A friend addressed with "Proszę iść" in A1 u09.
  - Marek's age mis-paired in an A1 u02 matching item.
- Wrong key: B1 u16 accepted only the mixed-gender error it asked the
  learner to fix.
- Second-correct distractors and interchangeable matching LEFTs/RIGHTs (A1
  u01-03, B2 u01-02, u07-08).
- Unnatural Polish ("To jest tanio", "jak najbardziej dobry", "na tym
  punkcie" for agreement).
- Content-origin remarks in learner-visible notes (A1 u02-03, removed).
New bug class discovered: none strictly. The answer-printing MC prompt is
the "target_blocks that printed the answer" class from the 2026-10-17
shared-English entry, but here it is systemic in a generator recipe (every
A1-B1 select_* item).

Fixes per level (from reviewer reports and commit subjects):
- A1: u01-03 31 · u04-06 50 · u07-09 15 · u10-12 18 · u13-15 6 fix groups ·
  u16-19 16. Total 130 + 6 groups + 133 MC sweep.
- A2: u21-23 25 · u24-26 31. Total 56 + 42 MC sweep.
- B1: u09-11 28 · u12-15 31 · u16-19 22 · u07-08 follow-up 2. Total 83 + 132
  MC sweep.
- B2: u01-04 33 · u05-08 62 · u01-04 reading follow-up 16. Total 111.
- C1: u01-04 84 · u05-08 59. Total 143.
- Grand total: ~830 fixes in 17 commits.
- 83 `NATIVE CHECK:` items are recorded in the files' review.notes for a
  native pass. Examples:
  - skręcić na/w prawo;
  - plain nominative instead of the vocative (Ewa/Marek vs Ewo/Marku);
  - Proszę o kawę vs Poproszę kawę;
  - są vs jest before lists of singular nouns;
  - "w weekend" glossed "this weekend";
  - C1 idiom adaptations (nazwać ryzyko po imieniu);
  - B2 u08 people-agreement phrasings.

Verification:
- `scripts/verify.sh --content-only`: content pass (148 "0 error" lines).
- Full backend suite against a local Postgres 16 with LINGO_REPO_ROOT set
  to the whole repo: 33305 passed, 0 failed, 0 skipped. This includes 1993
  en-pl cases in test_content_answer_shapes.

Deferred / remaining:
1. C1 u01-08 `speak_calosc` / `write_calosc` ask the learner to reproduce
   the whole 4-6-sentence unit model from memory, graded by exact match.
   The instruction ("Give the complete Polish structuring discourse model
   aloud exactly") is also jargon-heavy. This is a recipe design problem
   across 16 exercises, left for a decision: show the model text and turn
   these into read-aloud and copy items, or drop them.
2. Overlay word-order alternatives in `accepted_answers` each raise a
   compiler "scrambled permutation of tested_text" WARN. There is no
   suppression flag, so en-pl warnings rose (A1 ~75).
3. A heuristic scan of other languages' realizations (multiple_choice
   `target_blocks` text equal to `tested_text`) found candidates: prs 1056,
   fa 805, hi 423, ro 203, ar 201, nl 136, es 117, fr 84, de 77, it 40,
   ru 35. These are UNVERIFIED. Many are probably legitimate "What does X
   mean?" items with English options; only items whose block equals the
   overlay `correct_option` give the answer away. A per-language check is
   worth one scripted pass (overlay correct_option vs realization block).
4. A validator for "MC prompt block == correct_option" would make the
   biggest class here structurally impossible (Codex lane).
5. B1 u19 contains the content key
   `comprehend_ewa_powiedzialam_ze_pociąg`, with a non-ASCII ą. Left
   as is to keep content keys stable.
