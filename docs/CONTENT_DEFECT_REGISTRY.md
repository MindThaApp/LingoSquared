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
