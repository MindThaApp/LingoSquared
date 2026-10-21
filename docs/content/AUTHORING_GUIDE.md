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
  `بلی`/`نخیر`), and register. Never reuse the actual fa/prs *text* across
  the two — that already caused a real, shipped bug this session (Afghan
  verb endings leaking into Iranian Farsi content).
- **Do reuse *structure*, not text, for efficiency (explicit standing
  policy, decided 2026-07-06).** A scenario's characters, which grammar
  point a unit targets, its exercise-type pacing, and its spine-outcome
  sequencing are all fair game to reuse between fa and prs — that's real,
  legitimate time saved. What must always be authored fresh, independently,
  per dialect: every word of the actual Farsi and actual Dari text itself.
  Skeleton-share; never sentence-share. Verify real usage, or explicitly
  flag uncertainty for review, rather than guessing at either dialect.
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
  Never write both keys on one exercise: `correct_response` silently wins
  and drops every `accepted_answers` variant, so the compiler rejects the
  combination as an ERROR. Put the canonical answer first in
  `accepted_answers` instead.

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

**Update 2026-07-10: Ramin approved CC-licensed sourcing in principle**
(public-domain government works are no longer the only permitted
source type — see CLAUDE.md's "Sourcing policy widened" entry). That
doesn't change anything below: the practical blockers here (empty CC0
pool for launch languages, no attribution-credit surface built yet)
are still real and still apply. This section remains the authoritative
detail; CLAUDE.md's entry now points back here rather than duplicating
policy that could drift out of sync with it.

**Tatoeba: still reference-only — now a settled decision with data, not
a placeholder (investigated and closed 2026-07-07).** The main corpus is
CC-BY 2.0 FR (per-sentence contributor attribution required — tracking
not built, deliberately: see below). A CC0 1.0 subset exists
(`sentences_CC0.tar.bz2` on tatoeba.org/downloads, no attribution
needed), and it was actually downloaded and measured rather than
assumed useful: of ~559k CC0 sentences, two-thirds are Kabyle/Berber;
the launch/near-launch languages get **Dutch 50, Spanish 37, Farsi 0,
Dari 0** (French 14,201 and English 41,501 are the only real pools).
So the CC0 subset is effectively empty for every language this project
currently needs, and building CC-BY attribution infrastructure
(schema + learner-facing credit surface + per-sentence bookkeeping)
would buy unreviewed sentences that still require the full
spine-fit/adaptation/fresh-context-review pipeline — the sentence text
is the cheapest part of an exercise; slots, accepted-answer variants,
distractors, feedback, and lexeme wiring dominate the cost. Decision:
keep reference-only. Don't re-investigate without new information
(e.g. the CC0 subset growing dramatically in a needed language).

### Verified public-domain / open-license source map (2026-07-07)

Investigated, verified, and decided in one pass — check here before
hunting for external corpora again:

- **fa**: FSI Persian Basic Course (1963, PD, `pdfinfo` Author: US
  FSI) — in active use, the original §10 precedent.
- **prs**: Peace Corps Dari materials (PD, PDF-only, no audio) — in
  active use.
- **nl**: FSI Dutch Basic Course (PD, with audio) — in active use
  (15 of 28 nl realization units carry its provenance as of this note).
- **es** (lane parked until nl is done — do not start early): FSI
  Spanish Basic Course verified available, PD — 4 volumes, 55 units,
  drills + audio, on Live Lingua / fsi-language-courses.org. Peace
  Corps Spanish also exists. Ready to scaffold the moment es resumes.
- **fr** (lane parked, same rule): FSI French Basic Course verified
  available, PD — 2 volumes (~476 + 577 pp) with audio. Additionally
  **COERLL's "Français interactif" (UT Austin) is CC BY 3.0 —
  commercial use allowed** — a genuinely modern (not 1960s) full
  course; usable ONLY once a real attribution credit (course-level
  credit surface naming COERLL/UT Austin per CC BY) is actually built
  and shipped — attribution is a hard precondition of first import,
  not a follow-up task.
- **FSI pattern/substitution drills** may also inform Endless Practice
  template *frames* (they are natural sentence frames with slot
  substitutions) — but note honestly: the frame text is the cheap
  ~10% of a practice template; slot presets, lexeme-pool wiring, and
  review dominate, so this is an authenticity aid, not a volume
  multiplier.
- Cross-language note: FSI courses were independently authored per
  language, so scaffolding each language from its OWN FSI course does
  not reintroduce the "structurally identical dialogues across two
  languages" review-failure anti-pattern. Never scaffold two languages
  from the same source's structure.

**Categorically ruled out — do not import from these regardless of how
accessible they look:**

- **DLI GLOSS / Headstart2** (dliflc.edu): US-government *hosted* but
  NOT clean — lessons embed third-party copyrighted media (news
  articles/broadcasts) used under DoD-specific permissions;
  DLIFLC's own media-copyright page requires copyright-owner consent
  for reuse. Looks like FSI, isn't.
- **Any CC-BY-SA source** — Trayectos/Hecho en Texas (es, COERLL),
  Wikibooks, Wiktionary, Wikipedia sentences: share-alike would force
  every derived lesson to itself be licensed BY-SA (anyone could then
  legally copy that part of the content corpus). FSI Spanish (true PD)
  strictly dominates Trayectos anyway.
- **OpenSubtitles-derived corpora** (legally murky derivatives of
  copyrighted films), **Anki shared decks** (user-uploaded, routinely
  scraped from copyrighted textbooks/apps), and **anything from
  commercial apps, textbooks, or proprietary courses** — categorically
  unsafe for a shipping product, full stop.
- **Pre-copyright-era (pre-1930) readers/phrasebooks**: legally fine,
  pedagogically useless here — archaic register fails this guide's own
  §3/§10 modernization bar at A1/A2.
- **Mozilla Common Voice** (CC0 audio): unmatched crowd-read clips
  can't be spliced to authored content — same shape as the closed FSI
  audio investigation (see CLAUDE.md Secrets section); don't reopen.

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
the DOM, no network request even attempted for audio (correct behavior
at the time: fa/prs had zero TTS voices from any provider then, so the
frontend correctly skipped the fetch), and the wrong-answer feedback's
only clue was the answer text itself, revealed *after* the learner
already failed. The exercise was solvable only by a learner who
happened to already know the correct response, which defeats the point
of a listening exercise. This was different from (and narrower than)
the Endless Practice engine's own `listen_select`-for-fa exclusion (a
generator-side guard) — this is hand-authored LESSON content using
`listen_type`, which had no equivalent guard.

**Revised 2026-07-06: this restriction is now prs-only, not fa+prs.**
Azure Cognitive Services Speech shipped real Farsi neural voices the
same day (see `docs/BUILD_LOG.md`'s Azure TTS entry) — `fa` now has
working TTS via the exact same `/tts` endpoint every other listen-type
exercise already uses (`SpeakButton`/`speak()` don't know or care which
provider answered), so `listen_type`/`listen_select` lesson content for
**Farsi is safe to author again**. The Endless Practice engine's own
`listen_select` generator gate was updated to match
(`app/practice/service.py` now checks the combined `TTS_SUPPORTED_
LANGUAGES`, not the Google-only set) — verified live: en-fa's practice
pool currently has zero authored `listen_select` templates (this was
never a dormant-content bug, just a now-stale restriction), so this is
a real, if modest, opening for new template authoring, not something
that changes existing generated practice on its own.

Until real recorded audio or a working TTS voice exists for a given
**Dari (prs)** phrase (Dari still has zero coverage from any
provider — see §10 and `docs/BUILD_LOG.md`'s audio-manifest/Phase D
notes; browser `speechSynthesis` fallback quality for `fa-AF` is
itself uncertain, "may produce no sound or wrong accent"), **do not
author `listen_type` (or any other exercise type whose only prompt is
audio, e.g. bare `listen_select`/`listen_order` items with no
text_blocks fallback) for prs lesson content.** Use `translation`,
`dialogue_response`, `writing_prompt`, or another type that gives the
learner a real, visible prompt to work from instead. Once a phrase has
a genuine recorded asset (`media_asset_key` resolves) or Dari gets a
real TTS voice from some provider, authoring `listen_type`/
`listen_select` against it is fine — the gap is specifically
"audio-only prompt with no working audio," not the exercise type
itself.

### 14a. `dictation` (added 2026-08-03) — same audio-availability rule, plus it is graded strict

`dictation` (hear a TTS target-language sentence → type it, no source text
shown) is an **audio-only-prompt** type, so the §14 rule applies in full: **only
author `dictation` for a target language that has a working TTS voice.** Today
that means **nl** (Google) and **fa** (Azure, once `AZURE_SPEECH_KEY` is set) —
**NOT prs** (Dari has zero coverage from any provider; a dictation item there is
a silent, unanswerable play button). Full spec: `docs/DICTATION_EXERCISE_SPEC.md`.

Authoring shape (realization): `type: dictation`, `tested_text:` the exact
sentence (already-taught vocab only), `media_asset_key:` its audio, `prompt:
{target_blocks: []}` (empty, so only the audio button shows). Overlay:
`correct_response:` **byte-matching** `tested_text`, `orthography_strict: true`,
a short `feedback:`, and **no** `options`/`distractors`. Note: dictation is
graded **orthography-strict by type** — a one-character misspelling is marked
wrong (unlike `listen_type`, which is typo-tolerant on Latin scripts). So the
`tested_text`/`correct_response` must be the single canonical spelling.
**Boundary-punctuation exception (approved 2026-08-04):** grading now
tolerates a leading/trailing punctuation mismatch (`. ? ! … ¿ ¡ ؟ । ۔ ،` —
the `backend/app/review/grading.py` constant is authoritative) between the
learner's typed answer and `correct_response`/`tested_text` — terminal
punctuation no longer has to match byte-for-byte for GRADING. Authors
should still byte-match `correct_response` to the audio asset's text
regardless: the compiler validator tolerates boundary-only differences, but
any INTERNAL difference between the two is still a defect.

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

**Exception: single-answer `feedback` that quotes one target-language
line (e.g. `dialogue_response`).** The compiler treats a lone
`*emphasized*` span in a single-answer exercise's `feedback` as the
answer being shown, and fails validation when it differs from the
accepted answer. In a `dialogue_response` the accepted answer is the
source-language option while the feedback quotes the speaker's
target-language line, so they always differ. Leave that one quote
unwrapped: `"Sara says: آره، فکر کنم باید بمونم و کار کنم."`, not
`"Sara says: *آره، ...*."` (found 2026-10-20 in en-fa B1 u01/u03).
Feedback with two or more wrapped spans, or a quote that matches the
accepted answer, is not affected.

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

### Localizing matching-pair clues in an overlay

An exercise overlay may provide `pairs:` in the same list-of-`{left,
right}` shape as the realization. The compiled course then displays the
overlay pairs, and that overlay's `accepted_answers` must mirror those
effective pairs. The `left` side is the taught-vocabulary answer side: its
values and order must be byte-identical to the realization, and the pair
count must stay the same. Only the `right` clue text may be localized:

```yaml
exercises:
  de.a1.unit01.lesson01.exercise03.match_greetings:
    pairs:
      - {left: "Guten Morgen", right: "localized source-language clue"}
    accepted_answers:
      - value:
          - {left: "Guten Morgen", right: "localized source-language clue"}
        status: correct
```

## 17. A `fill_in_blank` slot's candidates must not be true synonyms of
each other, or mark them `interchangeable: true`

A real user report, 2026-07-06 (en-nl Endless Practice): a generated
`fill_in_blank` item rendered "Ben ___ nieuw hier?" with the instruction
"Complete the Dutch sentence" — genuinely unanswerable with certainty,
since the slot (`informal_address`: jij/je) is a true synonym pair, both
meaning the exact same "informal you" in this exact question, and only
whichever one the generator happened to sample was marked correct. This
is narrower and subtler than §13's bare-slot bug: real surrounding text
survives masking, but it can't disambiguate between two (or more)
candidates that mean literally the same thing here — a distinct bug
class from the ordinary case of an open vocabulary slot (country,
person_name, greeting, weekday, ...) where candidates are genuinely
*different* words and recalling the one that was actually taught is the
whole point of the drill.

**When authoring a `fill_in_blank` template (lesson content or a
practice template), check whether the slot's full candidate pool
contains members that are true synonyms/register-variants of each
other with nothing else in the frame able to prefer one over another**
(seen so far: je/jij, alsjeblieft/alstublieft, and a three-way
mijn/je/jouw possessive case where the frame never establishes whose
object is being discussed). If so, either rewrite the frame to add a
real disambiguating anchor (rarely possible when the pool members are
genuinely synonymous — there's nothing left to distinguish), or mark
the template's `answer_derivation` with the additive `interchangeable:
true` flag: `{kind: slot_text, slot: item, interchangeable: true}`.
`build_prompt()` (`backend/app/practice/service.py`) then accepts ANY
of the slot's own constraint-matching candidates as correct, using the
same generic `{"canonical", "accepted"}` multi-answer shape `grade()`
(`app/api/router.py`) already supports for hand-authored content — zero
frontend changes needed. Only set this flag when you've confirmed by
hand that every pool member really is interchangeable in that specific
frame; it must never be used to paper over an ordinary open-vocabulary
slot, which needs a single correct answer to keep testing real recall.
`scripts/_fill_in_blank_ambiguity_check.py` flags every single-slot
`fill_in_blank` template whose full course-wide candidate pool has more
than one member (a superset — it deliberately does not distinguish true
synonym pairs from ordinary vocabulary recall, since that judgment call
needs a human read of the actual frame) as a starting point for that
by-hand review.

**Enforced automatically since 2026-07-07: `scripts/compile_content.py`'s
`practice-validate`/`practice-compile` now hard-fail any single-slot
`fill_in_blank` template whose real course-wide candidate pool (computed
via the exact `lexeme_matches()` the standalone audit script already uses,
imported not reimplemented) has more than one distinct token and isn't
marked `interchangeable: true`** — this is what `scripts/verify.sh`'s
content stage runs on every check, so this bug class can no longer ship
silently. A second visible slot in the same multi-slot frame is only
WARNED on (not hard-failed), since it may legitimately narrow the answer
and that judgment still needs a human read. See
`docs/BUILD_LOG.md`'s "Corpus-wide fill_in_blank ambiguity audit, pass 2"
entry for the sweep this closed out and how the check was verified (a real
pre-fix instance re-validated to confirm it fails, full clean-corpus
`verify.sh --content-only` re-run to confirm zero false positives).

## 18. Reusing an already-classified tag across a course-level boundary
(A1 → A2) breaks `multiple_choice`/`listen_select`'s candidate floor

Found live 2026-07-07: a real depth-authoring technique (reusing an
already-classified, course-wide semantic tag — e.g. `weekday`,
`possessive`, `identity`, `politeness` — against a NEW unit's own real
taught sentence, instead of only ever pairing a tag with the exact unit
that first introduced it) is genuinely valuable for adding practice
variety without inventing vocabulary. But it has one failure mode that's
easy to miss: **A1 and A2 are separate `Course` rows in the database**
(`backend/app/practice/service.py`'s `_material()` scopes both
`PracticeTemplate` and `Lexeme` queries by `course_id`) — a real learner
enrolled in the A2 course NEVER sees A1's lexemes, no matter how
thematically continuous the two feel. `scripts/_practice_slot_check.py`
checks candidate-count sufficiency by pooling every spec `iter_specs()`
yields (A1 and A2 together), which is MORE PERMISSIVE than real runtime
scoping — a tag can look like it has plenty of candidates in that pooled
count while having far fewer (sometimes below the `multiple_choice`/
`listen_select` 3-candidate floor) once correctly restricted to only the
A2 course's own lexemes. A corpus-wide audit this same day found 25 real
instances of this exact gap across nl-en/fa-en/prs-en's A2 units (an
audit of en-nl's own A2 units, built without crossing the course
boundary, came back completely clean — proof this is avoidable, not
inherent to the technique).

**When reusing an already-classified tag against a NEW unit's real
sentence, check whether the tag's full candidate set was established in
the SAME course level (A1 or A2) as the template you're authoring.** If
yes, `multiple_choice`/`listen_select` are safe. If the tag crosses the
A1/A2 boundary (established in A1, template being authored for A2, or
vice versa), only use exercise types with no minimum-candidate floor —
`word_order`, `translation` — for that specific template; don't use
`multiple_choice`/`listen_select` unless the tag's candidates are
independently re-established within lessons of the SAME course level the
template belongs to. `iter_specs()` in every backfill script already
tags each spec with `level: "a1"`/`"a2"` — filter on that field to get
a properly-scoped candidate count before deciding, don't trust the
pooled count from `_practice_slot_check.py` alone for this specific
judgment call. Full detail, the exact 25 instances found, and how each
was fixed (converted to a floor-free type, or removed outright when a
sibling template in the same lesson would otherwise become a pure
duplicate) in `docs/BUILD_LOG.md`'s "Course-scoping audit result" entry.

## 19. Every `kind: vocabulary` teaching card needs an example sentence
on the card itself — never a bare word with a gloss

Direct product-owner feedback, 2026-07-07 (Ramin): teaching cards that
are just a target-language word, an English gloss, and a one-line note
("*medicine* bedeutet Medizin") don't teach — "if it's going to be
single word, it needs to be with more context and gamified to engrain
it in the person's memory." A corpus-wide survey the same day confirmed
how pervasive this was: of 951 `kind: vocabulary` cards across all 7
realization languages, 913 (96%) had no sentence context on the card,
and 690 of those never had ANY later same-lesson teaching card reuse
the word in a sentence — the word was introduced in isolation, full
stop. Even nl, the native-reviewed reference language and by far the
best case, left ~28% of its bare vocabulary cards with no sentence
follow-up; every other language was 80%+ uncovered.

**The rule: every `kind: vocabulary` teaching card must carry an
`example:` field — a real, natural target-language sentence using the
card's word — plus a matching `example_gloss:` on the overlay's
teaching entry.** Realization side, same text-block shape as `target:`:

```yaml
- content_key: nl.a1.unit01.lesson02.teach.prima
  kind: vocabulary
  target: {text: "Prima", language_code: nl, direction: ltr}
  introduced_tokens: [Prima]
  example: {text: "Prima, en met jou?", language_code: nl, direction: ltr}
```

Overlay side, on the same content_key's teaching entry:

```yaml
nl.a1.unit01.lesson02.teach.prima: {title: "Great", gloss: "great / fine",
  note: "…", example_gloss: "Great, and with you?"}
```

`example:` may also be a **list** of text-block mappings (with
`example_gloss:` a positionally-matched list of strings) — use this for
merged multi-word cards ("jij, je, u"), ideally one sentence per member
so each word is seen in context. The compiler pairs each example with
its gloss into the compiled card's additive `examples` array (see
`docs/CONTRACT.md`'s "Vocabulary-example addition"), and the frontend
renders them inside the same card with per-sentence TTS — the learner
sees word, meaning, and real usage in one glance with zero extra
"Next" clicks (deliberately NOT a separate follow-up card: card-count
bloat is its own documented complaint, see the nl unit01 review note
about merging cards).

Authoring rules for the example sentence itself:

- **It must be a genuinely natural sentence a speaker would say** — not
  a dictionary frame ("This is a table"-style filler is only acceptable
  when it really is the natural beginner sentence, e.g. for
  demonstratives). All existing rules apply in full: dialect
  authenticity (§3), no verbatim source-material imports (§10).
  Asterisk-marking (§15) doesn't apply here — the example is its own
  language-tagged block, not inline mixed text.
- **Prefer vocabulary the learner has already been taught** (this
  lesson or earlier), plus transparent items (names, cognates, numbers
  already covered). The example must be comprehensible from the gloss
  alone — it teaches context; it must not itself need a second
  explanation. Examples do NOT feed `introduced_tokens` and never make
  a word fair game for exercises; only `introduced_tokens` does.
- **The sentence must actually contain the card's word** — the exact
  surface form where the language allows it; an inflected form is fine
  when that's what's natural (the compiler warns, not errors, when it
  can't find the token, precisely for the inflection case — treat that
  warning as "confirm by eye," not noise).
- `kind: phrase`/`dialogue`/`reading` cards are exempt (they already
  ARE sentence-level). If a "vocabulary" card's target is somehow
  already a full sentence, it should almost certainly be `kind: phrase`
  instead. `example:` is allowed but not required on other kinds.

**Compiler enforcement, version-gated per file** (`scripts/
compile_content.py`, `validate_vocabulary_examples`): a vocabulary card
with no `example:` is a **warning** in files at `schema_version: "1.0"`
(the pre-rule corpus, pending retrofit) and a **hard error** in files
at `schema_version: "1.1"` or later. **All new realization/overlay
files must be authored at `schema_version: "1.1"`.** Retrofitting an
existing file means adding examples+glosses to every vocabulary card
AND bumping that file's (and its overlay's) `schema_version` to "1.1",
which locks the rule in mechanically for that file forever. Shape
problems are hard errors regardless of version: a single-word
"example," an example identical to the card's own target text, a wrong
`language_code`, an `example_gloss` with no matching realization
`example`, or mismatched example/gloss list lengths. Script-purity and
direction checks apply to example blocks automatically (they walk the
whole document). Overlay-side gloss presence is gated on the OVERLAY
file's own `schema_version` the same way — a 1.1 realization paired
with a still-1.0 overlay validates with warnings on the gloss side
only, so the two sides of a direction can be retrofitted independently
without ever hard-blocking each other.

**What this rule deliberately does NOT add: a new gamification
mechanic at the teaching moment.** The "engrain it in memory" half of
the feedback is already served by real, shipped mechanisms — the
lesson's own exercises begin immediately after the teaching stack and
are required (§2) to hit the same tokens recognition-first, missed
exercises recycle to the end of the queue (Phase B), lexeme-level SRS
resurfaces every taught word on its own schedule (Phase A), Endless
Practice regenerates it in fresh frames, and unit checkpoints re-test
it (Phase F). The genuinely missing piece was context at the moment of
introduction, which this rule fixes on the card itself. Don't bolt a
micro-quiz onto teaching cards without new evidence it's needed — it
would duplicate the exercise phase immediately following and worsen
the documented click-density complaint.

## 20. Fresh-context review methodology (how to replicate a Fable-grade
review without language-specific priors)

Distilled 2026-07-11 from a real Fable review of nl B1 units 01-05
(`docs/content/realizations/nl/b1_unit0{1..5}_*.yaml` +
`docs/content/overlays/en-nl/b1_unit0{1..5}.yaml`, commit `2535730`)
that found and fixed 8 real bugs a Sonnet authoring pass had missed,
including one shape the compiler cannot catch at all. Written so any
model (Sonnet, Opus, a future reviewer) can reproduce this quality bar
on any language, including ones the reviewer has no fluency in — every
check below is either mechanical (grep/script) or a nameable grammar
pattern, not "does this sound right."

**Order of operations — each stage feeds the next, don't skip ahead:**

1. **Read this file and CLAUDE.md in full before touching content.**
   The numbered rules above (§3 register, §5 instruction↔answer
   coherence, §11 cross-fact consistency, §12 multi-clause answer
   variants, §16 matching-pairs scale, §19 vocabulary examples) are the
   literal checklist — most real findings map to one specific §.
2. **Read one full realization+overlay pair together before judging
   anything.** The realization holds prompts/tested_text/pairs/
   word_banks; the overlay holds instructions/distractors/
   accepted_answers/glosses/notes. Many bugs are only visible by
   joining the two — e.g. a "(formal)" instruction in the overlay
   against an informal pronoun in the realization's own dialogue.
3. **Establish what grading actually does before judging
   `accepted_answers`.** Read `backend/app/review/grading.py::
   _normalize` — it casefolds and collapses whitespace but does NOT
   strip punctuation, and typo tolerance is Damerau-Levenshtein
   distance-1 with a 4-char minimum. So a missing comma degrades to
   "almost" (fine), but any word-level variant the course itself
   teaches as interchangeable (e.g. Dutch we/wij, ze/zij, jij/je)
   grades flatly WRONG unless explicitly authored as a variant — that
   line is what separates "typo tolerance covers it" from "needs a
   §12 variant."

**Mechanical sweeps — run these on every review, they catch the worst
bugs and need zero fluency in the target language:**

- **Boolean coercion (the highest-value single check — the compiler's
  own validator does NOT catch every field this can happen on, a
  documented gap in CLAUDE.md's footguns).** `yaml.safe_load` each
  file and recursively walk the parsed structure for
  `isinstance(x, bool)` anywhere outside a genuinely boolean field. A
  matching-pair `{left: waar, right: true}` (meant as the *word*
  "true") silently parses as Python `True` and passes `compile_content.
  py` with 0 errors — only a real type-walk catches it.
- **Snake_case/jargon leak scan** over every `options`/`distractors`/
  `correct_option`/`word_bank` value, plus a grep of learner-facing
  `feedback`/`gloss`/`note` text for internal words ("reviewed",
  content_keys, template names).
- **Title length**: grep for any `title:` field over ~200 chars (the
  `content_items.title VARCHAR(200)` DB crash, §-referenced in
  CLAUDE.md's footguns — passes `validate` clean, crashes on real
  import).
- **Spine outcome existence**: verify every `spine_outcome_id` the unit
  references exists verbatim in `universal_spine.yaml`
  (`grep -c "id: <exact-id>$"`), and that `scripts/content_manifest.
  txt` actually lists the new files.
- **`accepted_answers` shape**: every variant entry (when a dict) must
  have a `value:` key, never `text:` or any other name — a bug that
  passes `validate` clean and only crashes real `compile`
  (`ValueError: accepted answer at index N has no value`).

**Grammar/register red flags — nameable and checkable without native
fluency, using a dictionary/reference grammar:**

- **Register consistency within one scene**: if a unit claims a formal
  register, grep the dialogue for every informal-register form and
  check each hit by hand — fossilized idioms are where informality
  sneaks in even when the author knows the rule (a formal-register
  speaker correctly using formal forms everywhere except one frozen
  idiomatic phrase). Also check that any register *mixing* across
  speakers is intentional (one formal, one informal, is realistic; one
  speaker mixing within their own lines is a bug).
- **Bare-word multiple-choice ambiguity (the single highest-yield
  check across every language reviewed so far).** For any
  `recognize_X`-style exercise whose prompt is a single word with no
  sentence context: list every distinct meaning of that word from a
  dictionary, and confirm no distractor option IS one of those other
  meanings. This fires hardest when an earlier unit taught meaning A of
  a word and the current unit's distractor is meaning B of the *same*
  word — technically correct either way, so the item is unanswerable.
- **Subordinate-clause word order / inversion rules**, if the language
  has them: verify the unit's own claimed grammar point holds in every
  example the unit itself uses to teach it — the unit's own teaching
  material is where a self-inflicted violation is most damaging
  (undermines the very rule being taught).
- **Agreement pairs the unit is explicitly teaching** (e.g. a
  singular/plural conditional-verb contrast): verify every example
  sentence's subject-verb pairing actually matches the rule, one by
  one — don't sample.
- **Anglicism/calque smell test**: flag any sentence that reads as a
  word-for-word translation of the source-language instruction rather
  than a natural target-language sentence, then judge: grammatical but
  stiff → note in the review report for a native pass; actually wrong
  → fix directly.
- **Listening-distractor rule, meaning-level, not just verbatim** (the
  CLAUDE.md `listen_select` footgun, extended): for every
  `listen_select`/`dialogue_comprehension`/similar, read the FULL audio
  text and confirm no distractor is something the tested speaker says
  OR *defensibly implies* anywhere in that clip — apply this at the
  meaning level (a paraphrase or reasonable inference from what's
  actually said is just as unanswerable as a verbatim repeat), not only
  a literal string match.

**Fact/character consistency — exact method:**

- `grep -rn "CharacterName"` across both the target-language
  realizations and the overlays for every named character, including
  inside `distractors` (a distractor naming a character absent from the
  unit's own text is a bug on its own).
- For any established recurring character, find the unit that pinned
  their facts and diff every new claim in the unit under review against
  that established profile before accepting it (job, nationality,
  relationships — whatever the corpus has already committed to).
- Before introducing a new character or reusing a name, verify it's
  genuinely unused corpus-wide (`grep -rl "\b$name\b"` over every
  candidate) rather than assuming a name is free.

**Fix-vs-flag judgment — don't blur this line:**

- **Fix** anything where a learner would be graded wrong on a right
  answer, shown an unanswerable item, or shown broken/artifact text —
  these are objective, no judgment call needed. Fix scoped renames or
  register corrections when every touchpoint is enumerable: grep the
  string, update realization + overlay + tested_text + introduced_
  tokens + feedback together, then re-run the compiler.
- **Flag instead of fixing** anything that's a genuine style
  preference a native reviewer should arbitrate (correct-but-stiff
  phrasing), or a "contradiction" that's really just unresolved tension
  rather than an outright falsification. Inventing new content to
  resolve mere tension is authoring, not reviewing — leave a note in
  the unit's review block and let the content-authoring lane pick it up
  on its own cycle.
- **Don't add unbounded paraphrase variants to `accepted_answers`** —
  only variants a learner following THIS course's own teaching would
  actually produce (if the course explicitly teaches two forms as
  interchangeable, both must grade correct; a synonym using vocabulary
  the course never taught does not need to be added).
- **Re-run the compiler (`validate` AND `compile`, both) after every
  edit, then re-run your own mechanical sweeps.** The compiler passing
  is necessary but never sufficient — it passed every single bug found
  in the case this section is drawn from, including the boolean-
  coercion one.

**What this buys you**: this exact process, applied cold (zero prior
exposure to the language or the unit) by one review pass, found a
compiler-invisible boolean-coercion bug, a register break inside the
unit that was teaching that exact register, two character-consistency
violations, three unanswerable bare-word items, two meaning-level
listening-distractor collisions, and five missing `accepted_answers`
variants — all in five units that had already passed `compile_content.
py` with 0 errors and 0 warnings. Treat compiler-clean as the floor,
never the bar.
