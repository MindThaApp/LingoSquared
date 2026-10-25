# Content-authoring prompt templates (for dispatching Codex)

Built by Session 3 (INFRA) so every Codex content dispatch bakes in the
standing rules from `AUTHORING_GUIDE.md` and the hard-won failure modes
in `CLAUDE.md`/`docs/BUILD_LOG.md` by construction, instead of being
reconstructed (and potentially weakened) by hand each time. Fill in the
`{...}` placeholders and pass the result to `codex-companion.mjs` with
`--cwd "$LINGO_REPO"`.

Three templates: target-language realization, source-language overlay,
and fresh-context review. Use exactly one per Codex dispatch — never
combine authoring and reviewing in the same task, that's the whole
point of "fresh context."

---

## Template 1 — author a target-language realization

Use when authoring `docs/content/realizations/{lang}/{unit_key}.yaml`
for a NEW unit (the realization owns scenario, characters, culture,
register — authored target-language-first, not translated).

```
Author a new A1 target-language realization unit for Lingo².

Language: {TARGET_LANGUAGE_NAME} ({target_code})
Unit: {unit_key} — {unit_title}
Spine outcome(s): {spine_outcome_id(s), from docs/content/universal_spine.yaml}
Output file: docs/content/realizations/{target_code}/{unit_key}.yaml

Binding rules (docs/content/AUTHORING_GUIDE.md — read it before writing
anything):
1. One outcome per unit, genuinely — every lesson must serve the
   declared spine_outcome_id. If content doesn't fit, it belongs in a
   different unit; don't force unrelated grammar in via metadata.
2. Script-introduction lessons (if this is the first unit in a new
   script) get spine_outcome_id: null, not a forced communicative label.
3. Exercise pacing within EVERY lesson, no exceptions: recognition
   (multiple_choice) -> drag/matching (word_order, matching_pairs) ->
   production/typing (fill_in_blank, translation, writing_prompt,
   listen_type, dialogue_response, grammar_check-as-free-text). At most
   one typing exercise in a script-introduction lesson, positioned last.
4. Target-language-first: invent your own scenario, character names,
   food, register, and culture for THIS language. Do not template
   structure, dialogue beats, or character arcs off any other
   language's unit, even one covering the same spine outcome —
   structurally identical dialogues across two languages for the same
   node is a validation FAILURE, not efficiency.
5. Verify actual dialect/register, not the "obvious" cognate or a
   guess — flag uncertainty explicitly rather than guessing.
6. Never expose internal authoring artifacts to learners: every
   option/word_bank/correct_response/feedback string is something a
   real person reads. No snake_case tokens, no internal jargon.
7. Check every exercise's instruction text against its own answer data
   — they must test the same thing.
8. YAML footguns: quote "Yes"/"No"/"True"/"False"/"On"/"Off" as strings
   always — PyYAML silently coerces bare versions to booleans. For any
   exercise with genuinely multiple acceptable answers, use the full
   accepted_answers list (status: correct / acceptable_with_note) —
   never a single hardcoded correct_response when more than one
   phrasing is valid.
9. Set answer_language_code explicitly on any exercise where the
   expected answer's language differs from the type-based default
   (e.g. a Latin-letter transliteration exercise for a non-Latin
   target language).
10. Every `kind: vocabulary` teaching card MUST carry an `example:`
    field — a real, natural target-language sentence using that word
    (same text-block shape as `target:`; a list of them for merged
    multi-word cards). Prefer already-taught vocabulary in the
    sentence. Author the file at `schema_version: "1.1"` — the
    compiler hard-fails missing examples at that version. See
    AUTHORING_GUIDE.md #19.
{ADD: script-purity note if non-Latin — e.g. "Use Persian-range
codepoints ک (U+06A9)/ی (U+06CC), never Arabic ك (U+0643)/ي (U+064A)"}

Mark `review: status: unreviewed` when done — a SEPARATE fresh-context
review task (Template 3) must run before this ships, don't self-certify.

{ANY UNIT-SPECIFIC SCENARIO NOTES, CHARACTER CONSTRAINTS, ETC.}
```

---

## Template 2 — author a source-language overlay

Use when authoring `docs/content/overlays/{source}-{target}/{unit_key}.yaml`
against an EXISTING target-language realization.

```
Author a new A1 source-language overlay for Lingo².

Direction: {source_code} -> {target_code} ({source_name} speaker
learning {target_name})
Realization it overlays: docs/content/realizations/{target_code}/{unit_key}.yaml
Output file: docs/content/overlays/{source_code}-{target_code}/{unit_key}.yaml

CRITICAL — sibling-direction isolation: if a sibling-direction overlay
exists for this same unit or language pair (e.g. you are authoring
prs-en and fa-en already exists, or vice versa), DO NOT OPEN OR
CONSULT IT AT ALL, not even "for reference." Treat it as if it does
not exist. Draft entirely fresh from the target realization + the
universal spine. ("Reference only" instructions have failed twice on
this project — first drafts came back 90%+ near-paraphrased of the
sibling file's prose despite the softer instruction. Only the strong
"don't open it" framing has worked.)

Binding rules (docs/content/AUTHORING_GUIDE.md — read it before writing
anything):
1. This overlay's job is explanations, glosses, contrastive grammar,
   and interference-error distractors SPECIFIC to a {source_name}
   speaker learning {target_name} — not a translation layer. A
   {source_name} speaker's likely confusions (false cognates, tense
   mapping, article errors, gender agreement, whatever applies to this
   specific pair) should shape the distractors you write.
2. Same exercise-pacing rule as realizations: recognition -> drag ->
   production within every lesson.
3. Verify actual {source_name} dialect/register (not a guess, not the
   "obvious" related-language template) — flag uncertainty rather than
   guess.
4. Never expose internal jargon to learners (snake_case tokens,
   internal field names) in any learner-facing string.
5. Multi-answer exercises: use the full accepted_answers list with
   status: correct / acceptable_with_note — a single hardcoded
   correct_response silently marks every other valid phrasing wrong.
6. YAML footguns: quote "Yes"/"No"/"True"/"False" always.
7. Set answer_language_code explicitly wherever the expected answer's
   language differs from the type-based default.
8. For every realization teaching card that has an `example:` sentence
   (all `kind: vocabulary` cards in 1.1+ files), add a matching
   `example_gloss:` on that card's overlay teaching entry — a
   {source_name} translation of the example sentence (a positionally
   matched list when the card has multiple examples). Author the
   overlay at `schema_version: "1.1"`. See AUTHORING_GUIDE.md #19.

Mark `review: status: unreviewed` when done — a SEPARATE fresh-context
review task (Template 3) must run before this ships.

{ANY PAIR-SPECIFIC INTERFERENCE-ERROR NOTES, e.g. "Russian speakers
commonly drop English articles — include at least one article-drop
distractor per lesson where natural."}
```

---

## Template 3 — fresh-context review

Use to review ANY realization or overlay file before it ships. Dispatch
as a genuinely separate task/session with zero access to the authoring
task's reasoning or conversation.

```
Fresh-context content review for Lingo². You have NOT seen how this
file was authored — review it cold, as if a stranger handed it to you.

File(s) to review: {file path(s)}
{IF reviewing a source overlay:} Do NOT open any sibling-direction
overlay file for comparison — review this file entirely on its own
merits against the target realization and universal_spine.yaml.

Check specifically, per docs/content/AUTHORING_GUIDE.md:
1. Spine-outcome discipline: does every lesson's content genuinely
   match its declared spine_outcome_id? Read the outcome's own
   description in universal_spine.yaml and check literally.
2. Exercise pacing: recognition -> drag -> production order within
   every lesson, no typing exercise before adequate recognition
   exposure.
3. Dialect/register authenticity: does the language sound native, not
   machine-translated? Any unnatural calques, redundant doubled
   constructions, or overstated absolute grammar rules?
4. Internal jargon leaks: read every learner-facing string (options,
   word_bank, correct_response, feedback, instructions) and ask "would
   a person with zero knowledge of this system's internals understand
   this?" Flag any snake_case token or internal-sounding phrase.
5. Instruction/answer-data coherence: for every exercise, does the
   instruction text actually match what the options/correct_response
   test?
6. Script purity (non-Latin scripts): correct codepoints throughout —
   {name the specific confusable pair if relevant, e.g. Persian ک/ی
   vs Arabic ك/ي}.
7. If this is a source overlay, is it genuinely independently
   authored — or does it read as structurally/texturally templated off
   another language's content for the same outcome? (For overlays: also
   check for near-identical instruction/feedback strings against any
   sibling-direction overlay you have independent access to, if asked
   to do that comparison as an explicit separate check.)
8. Ambiguous items: any multiple-choice question with more than one
   technically-correct answer? Any distractor set unfairly easy or
   confusing?
9. Vocabulary examples (AUTHORING_GUIDE.md #19): does every
   `kind: vocabulary` card's `example:` sentence sound genuinely
   natural (not a dictionary frame), actually use the card's word,
   and stay comprehensible with mostly already-taught vocabulary?
   Does the overlay's `example_gloss:` translate it faithfully?

Report every issue found, however small. Do not rubber-stamp. If the
file is genuinely clean, say so explicitly and recommend
`review: status: reviewed`.
```

---

## Notes for whoever fills these in (Session 2 / CONTENT by default)

- Always pass `--cwd "$LINGO_REPO"` to
  `codex-companion.mjs` — see CLAUDE.md.
- After Codex reports a review pass, still do your own independent
  sweep for the specific bug classes that have shipped before: bare
  snake_case in `options`/`distractors`/`correct_option`, and words
  like "reviewed" leaking into feedback text (both have happened for
  real — see BUILD_LOG.md).
- Run `scripts/verify.sh --content-only` (or add the new unit's
  realization/overlay files to `scripts/manifest.d/content/*.txt` first)
  before considering any unit done.
- Update `scripts/manifest.d/content/*.txt` (and `manifest.d/practice/`
  for practice packs) when a new course-direction or pack is added, so
  `verify.sh` picks it up automatically.
