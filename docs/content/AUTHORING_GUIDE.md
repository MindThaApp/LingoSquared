# Content Authoring Guide

Reference this for every new unit, in every language pair. It's built from
two sources: what the `en-prs` course (Dari, target-language realization)
already does right, and real bugs found in production this session that
should never recur.

## 1. Spine outcome discipline

Every lesson declares a `spine_outcome_id` from `universal_spine.yaml`. This
isn't decoration — the mastery-tracking system depends on it being accurate.

- **One outcome per unit, genuinely.** If a unit is titled "Greetings and
  first meetings," every lesson in it should serve that outcome. Don't let a
  unit drift into unrelated grammar points (subject pronouns, `do`/`does`
  questions, articles) just because they're beginner-level and have to go
  somewhere. If content doesn't serve the declared outcome, it belongs in a
  different unit with its own correctly-declared outcome — full stop, not a
  metadata workaround.
- **Script-introduction lessons get `spine_outcome_id: null`.** A lesson
  that's purely "learn these letters" isn't a communicative outcome and
  shouldn't be forced into one. `en-prs/a1_unit01`'s `lesson01.script_ramp`
  does this correctly — copy that pattern for every new script-introduction
  lesson (Cyrillic for Russian, Han for Chinese, when those ship).
- Before marking a unit `status: complete_draft`, re-read the outcome's own
  description in `universal_spine.yaml` and check every lesson title against
  it literally. If you can't summarize a lesson's content as "this is the
  outcome, applied," it's out of scope.

## 2. Lesson-internal exercise pacing

Within any lesson — and *especially* the first lesson introducing a new
script — exercises must progress:

**recognition** (`multiple_choice`) → **drag/matching** (`word_order`,
`matching_pairs`) → **production/typing** (`fill_in_blank`, `translation`,
`writing_prompt`, `listen_type`, `dialogue_response`, `grammar_check`-as-
free-text).

Never place a typing exercise before the learner has had multiple
recognition/drag exposures to the specific characters or words being tested.
`en-prs/a1_unit01/lesson01` is the reference: 6 recognition/drag exercises
before the first typing exercise, which comes last. A script-introduction
lesson should have *at most one* typing exercise, positioned last, ideally
optional-feeling (e.g. "copy this word") rather than open-ended recall.

## 3. Dialect and register authenticity

- **Verify the actual target dialect, not the "obvious" cognate.** Dari and
  Farsi share a script but differ in verb endings (`-ین`/`-یم` Afghan forms
  vs. `-ید`/`-یم` Iranian forms), vocabulary (`چاشت` for midday, `رستورانت`,
  `بلی`/`نخیر`), and register. Don't assume one Persian variant's content is
  a safe template for the other — check real usage, or explicitly flag
  uncertainty for review rather than guessing.
- **Avoid machine-translation-style prose.** Concretely: no unnatural
  calques (`پیشنهاد کمک می‌دهد` instead of `پیشنهاد کمک می‌کند`), no
  redundant doubled prepositions (`هنگام ... در وقت`), no vague
  translated-sounding explanations that don't actually explain the grammar
  point (`نشان می‌دهین که شما نیز همین احساس را دارین` doesn't tell the
  learner anything useful about *why* — say what the phrase does, plainly).
- **Don't overstate absolute grammar rules.** If a construction has a
  common form and a valid-but-less-common alternate reading (e.g. `You are
  okay?` as a natural spoken echo question, not just an "incorrect" word
  order), say so — don't teach a rule that's wrong in the exception case
  just because it's simpler to state.
- Correct Unicode codepoints matter and are easy to get silently wrong:
  Persian keheh `ک` (U+06A9) vs. Arabic kaf `ك` (U+0643), Persian yeh `ی`
  (U+06CC) vs. Arabic yeh `ي` (U+064A). Use the Persian-range codepoints for
  fa/prs content; mixing them causes subtly-wrong-looking text that's hard
  to spot by eye.

## 4. Never expose internal authoring artifacts to learners

Every learner-facing string (`options`, `word_bank`, `correct_response`,
feedback, instructions) is something a real person reads. `"null_subject"`
shipped as a literal selectable answer option in production content this
session — that's the failure mode to design against. Before finalizing any
exercise, read every string a learner would actually see and ask "would a
human who doesn't know this system's internals understand this?"

## 5. Exercise instruction ↔ answer-data coherence

Check every exercise's instruction text against its own `options` /
`word_bank` / `correct_response` — they must test the same thing. Two real
bugs from this pass: an instruction asking "what discourse function does
Goodbye serve?" paired with answer options that were plain translations
(testing meaning, not function); an instruction asking the learner to
identify "who shows the room" in a dialogue where no character ever shows a
room. Read the instruction, then read the answer data, and confirm a human
following the instruction would actually produce that answer.

## 6. `answer_language_code` and exercise-type shape

The compiler stamps `answer_language_code` onto every compiled exercise
(used by the frontend's virtual keyboard). Defaults: `target_language` for
most types, `source_language` for `reverse_translation`. Two things authors
must get right:

- For `translation`/`reverse_translation`/free-text exercises, the
  `correct_response` value's actual language must match what
  `answer_language_code` will resolve to. A `translation` exercise (source→
  target direction) must have a target-language answer; don't accidentally
  write a source-language answer for it.
- If an exercise genuinely needs the learner to type in a **different**
  language than the type-based default implies (e.g. a "give the Latin-
  letter transliteration" exercise, where the answer is Latin even though
  the course teaches a non-Latin script), set `answer_language_code`
  explicitly in the overlay entry to override the default — see
  `en-fa/a1_unit01.yaml`'s `romanize_salam`/`romanize_goodbye` entries for
  the pattern.
- `listen_select`/`multiple_choice` exercises are exempt from this concern
  (no virtual keyboard involved), but keep `options` values in whichever
  language actually makes pedagogical sense for a comprehension check —
  usually the learner's source language, since the point is confirming they
  understood the target-language audio, not testing production yet.

## 7. YAML footguns

- **Never write bare `yes`/`no`/`true`/`false`/`on`/`off` as a string
  value** in `correct_option`, `distractors`, `options`, or
  `accepted_answers`. PyYAML's default resolver silently coerces these to
  Python booleans, which either crashes the compiler (if the field expects
  a list of strings) or — worse — silently produces a blank/broken
  learner-facing option with no error at all. Always quote them: `"Yes"`,
  `"No"`. The compiler validates this now (`validate_no_stray_yaml_booleans`
  in `scripts/compile_content.py`) but don't rely on catching it after the
  fact — write it correctly the first time.
- For multi-answer exercises, use the `accepted_answers` list with
  `status: correct` / `status: acceptable_with_note` — don't write a single
  `correct_response` unless there's genuinely only one acceptable answer.
  The compiler needs the full variant list to grade correctly; a single
  hardcoded string means every other valid phrasing gets marked wrong.

## 8. Don't consult sibling-direction files while authoring

If you're authoring the `prs-en` overlay, do not open or reference the
`en-prs` overlay (or vice versa) for structure or phrasing, even "for
reference only" — that instruction isn't strong enough in practice and
produces content that's structurally/texturally templated off the sibling
file rather than authentically authored for its own direction. If a fresh
task needs to compare two directions for consistency, that's a distinct,
explicit task — not something to do implicitly while authoring one side.

## 9. Before marking `review: status: reviewed`

A fresh-context review (a task with zero access to the file being reviewed
being authored, plus explicit instruction not to consult sibling files)
must actually run and its findings must be resolved — not just requested.
Check the file's own `review:` block before treating any unit as done;
`status: unreviewed` in a shipped file means exactly what it says, no
matter how polished the prose looks on a skim-read.

## 10. Public-domain source material: adapt, don't just reference (revised 2026-07-05)

FSI and Peace Corps course material (Persian/Farsi, Dari, Dutch, and
others) is genuinely public domain — US government works, no attribution
or licensing burden, unlike Tatoeba (CC-BY, requires per-sentence
attribution this pipeline doesn't track — still reference-only, not a
direct source). This supersedes the older "reference only, never copy
sentences" line for FSI/Peace Corps material specifically: it may now be
used as a real scaffold — vocabulary progression, grammar sequencing,
authentic dialogue scenarios — not just informational background.

**Never import verbatim.** The source is 1960s-70s diplomatic/Peace-Corps
training material: dated vocabulary, sometimes archaic or overly formal
register, occasional Cold-War-era cultural framing. Every phrase pulled
from it needs an active modernization pass — current spoken register,
current cultural references, current natural phrasing — not a copy-paste
with light editing. If a sentence reads the same after adaptation as it
did in the source, that's a sign the modernization pass didn't happen.
Apply every other rule in this guide (dialect/register authenticity §3,
jargon leaks §4, instruction↔answer coherence §5) to adapted content
exactly as to originally-generated content — adaptation is not a review
shortcut.

**Audio**: FSI/Peace Corps courses include recorded audio. It cannot be
spliced directly into new lessons (wrong phrases, dated pronunciation
conventions in places, mismatched to newly-authored content), but is
worth using as a pronunciation reference during any recording pass,
especially for fa/prs where the project currently has zero TTS coverage.

Tatoeba's CC-BY sentence corpus remains reference-only per the original
policy (attribution tracking not built, content unreviewed) — this
section does not change that.

## 11. Cross-check facts within a lesson, not just each item in isolation

A real bug shipped 2026-07-05: a "choose the cheapest item" exercise was
keyed to Rice ($3/bag) as correct, while the same lesson's own price
labels put Apples at $2/pound — genuinely cheaper. Both the exercise and
the label were individually well-formed; nobody checked them *against
each other*. This is a distinct failure mode from the ones already
covered above (§5 checks instruction against its own answer data; this
is checking a fact against every OTHER fact stated elsewhere in the same
scenario). Before finalizing a lesson, list every concrete fact it
states or implies (prices, times, quantities, names, locations) and
verify they're mutually consistent across every exercise and teaching
card that touches them — not just internally coherent one at a time.
This matters most for exercises with a comparative or superlative answer
("cheapest," "most," "first," "closest") since those are exactly the
ones whose correctness depends on facts stated elsewhere.

## 12. Author every natural multi-clause phrasing, not just one punctuation form

A recurring gap found across many units in the same review pass: answers
combining two natural clauses (e.g. "I come from Egypt. And you?") were
often authored with only ONE joining form accepted — typically the
period-separated version — when comma-joined and "and"-joined variants
("I come from Egypt, and you?") are equally natural and a real learner
would type them interchangeably. This matters more than it looks:
Phase C's typo-tolerance only forgives distance-1 character edits, and a
missing comma or an inserted "and" exceeds that distance, so these gaps
silently produced the "app marked me wrong for a right answer" failure
mode this whole review methodology exists to prevent. When authoring or
reviewing any multi-clause `accepted_answers` list, explicitly write out
the period-joined, comma-joined, and conjunction-joined forms (as
`status: correct`, not `acceptable_with_note` — they're equally correct,
not merely tolerated) rather than defaulting to a single form and
assuming typo-tolerance will cover the rest.

## 13. A blanked slot needs surrounding context, or the exercise is unanswerable

A real bug shipped 2026-07-05: several `fill_in_blank` templates authored
`frame.text` as nothing but the one token being blanked (e.g.
`frame: {text: "{letter}"}`), so masking it left a bare `"___"` with zero
surrounding context — not hard, *impossible*, since there was nothing
left to reason from. This existed across six different language packs,
confirming it's a pattern to actively guard against, not a one-off typo.
When authoring any `fill_in_blank` item (lesson content or a practice
template's `frame`), the frame must contain visible text *besides* the
blanked slot — enough that a learner who already knows the target word
can locate where it goes from context. If the natural sentence really is
just the one word, use a `translation` or `writing_prompt` type instead
of `fill_in_blank`.

## 14. Avoid `listen_type` (and other audio-only-dependent exercise
types) for fa/prs lesson content until real recorded audio exists

A real gap found live 2026-07-05 (Dari QA pass): a `listen_type`
exercise ("Listen and type the conventional response") gave the learner
literally zero visual hint of the target phrase — no text anywhere in
the DOM, no network request even attempted for audio (correct behavior,
not a bug: fa/prs have zero Google Cloud TTS voices, so the frontend
correctly skips the fetch), and the wrong-answer feedback's only clue
was the answer text itself, revealed *after* the learner already failed.
The exercise was solvable only by a learner who happened to already know
the correct response, which defeats the point of a listening exercise.
This is different from (and narrower than) the Endless Practice engine's
existing `listen_select`-for-fa exclusion (a generator-side guard) — this
is hand-authored LESSON content using `listen_type`, which has no
equivalent guard.

Until real recorded audio exists for a given fa/prs phrase (see §10 and
`docs/BUILD_LOG.md`'s audio-manifest/Phase D notes — browser
`speechSynthesis` fallback quality for `fa-AF` is itself uncertain, "may
produce no sound or wrong accent"), **do not author `listen_type` (or
any other exercise type whose only prompt is audio, e.g. bare
`listen_select`/`listen_order` items with no text_blocks fallback) for
fa/prs lesson content.** Use `translation`, `dialogue_response`,
`writing_prompt`, or another type that gives the learner a real,
visible prompt to work from instead. Once a phrase has a genuine
recorded asset (`media_asset_key` resolves), authoring `listen_type`
against it is fine — the gap is specifically "audio-only prompt with no
working audio," not the exercise type itself.

## 15. Mark target-language words with `*asterisks*` inside mixed-language
explanatory text (`note`, exercise `feedback`)

Found live 2026-07-06 (Ramin's nl A1 review): a teaching card's `note`
routinely mixes the target language inline with the source-language
sentence explaining it, e.g. `"Zou + infinitive is the polite
conditional, softer than a direct statement."` or `"Om ... te +
infinitive expresses purpose; me in te schrijven splits the separable
verb inschrijven around the reflexive pronoun."` With no visual
distinction, a learner can't tell at a glance which words are the
language they're learning versus the explanation. The frontend now
parses single-asterisk spans in any `note` or exercise `feedback`
string (`frontend/src/components/EmphasizedText.tsx`) and renders them
italic + bold (`.target-language-span` in `index.css`) — the exact
same convention as Markdown italics, `*word*` or `*multi-word phrase*`.

**When authoring or editing any `note` or `feedback` field that
contains target-language text inline with source-language explanation,
wrap every target-language word or phrase in single asterisks.** Do
not wrap the whole sentence, only the target-language spans; don't use
asterisks for anything else (no bold/emphasis-for-importance
convention piggybacks on this marker, since the frontend has no way to
distinguish intent). Plain notes with no target-language text mixed in
(e.g. a note entirely in English, or a `grammar_note`/`reading` card's
`target.text` block, which is already its own dedicated
`language_code`-tagged block, not a `note`) don't need this — it's
strictly for the inline-mixing case. Existing notes authored before
this convention existed render unchanged (plain text, no emphasis)
until they're touched again; retrofitting them isn't required, but
apply the convention to any note you edit or write for any other
reason.

## 16. `matching_pairs` exercises need real scale — a handful to a dozen
pairs, not 2-3

Found live 2026-07-06 (Ramin's direct feedback): existing `matching_pairs`
exercises across every language pair are consistently tiny — 2 or 3
pairs per exercise, the same underlying problem as §-adjacent density
complaints about teaching-card pagination (too little content per
interaction). Neither the frontend (`MatchingPairs.tsx`) nor the
backend (`app/practice/service.py`) impose any hard limit — pair count
is purely a function of how many entries the content author puts in
`prompt.pairs` (lesson content) or how many slots a template declares
(Endless Practice). A 2-pair matching exercise is barely a game; it
should feel like a real puzzle.

**When authoring or reviewing any `matching_pairs` exercise (lesson
content or a practice template), use as many pairs as the unit's
taught vocabulary genuinely supports — aim for 6-12 where the lesson
or unit has that much real vocabulary to draw from, not the 2-3 that's
been the default.** Don't pad with untaught or unrelated words just to
hit a number — every pair must still be independently valid per this
guide's existing rules (§2 dialect authenticity, no self-reference,
distinct enough to not be confusable). When a single lesson doesn't
have enough vocabulary on its own, pool in vocabulary already taught
earlier in the same unit (or, for a review/practice-pool template,
across the whole course so far) rather than force an artificially
small exercise. This applies going forward to all new authoring; a
follow-up pass is retrofitting existing shipped `matching_pairs`
content across all languages to the same standard.
