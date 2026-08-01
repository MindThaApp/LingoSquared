# Overlay answer/gloss review — shared instructions (2026-08-01)

You are a fresh-context reviewer. You review **target-language overlay packs**
(`docs/content/overlays/<dir>/<level>_unitNN.yaml`) for **answer correctness and
gloss correctness**. These packs supply the L1 instruction, the accepted answers,
the distractors, and the glosses that sit on top of a shared realization spine.
Roughly 400+ packs have never had an agent review; you are reviewing an assigned
slice. **Report only — do NOT edit any file.** Your output is a structured defect
list the coordinator will triage.

## Grading mechanics that decide what is a REAL defect

- **Free-text (type/speak/dialogue_response) is graded ONLY against the overlay's
  `accepted_answers` for that exercise.** The realization's `tested_text` is NOT
  unioned at runtime. So a valid learner answer that is missing from
  `accepted_answers` is a real, gradeable defect.
- **Latin-script grading** allows small typo tolerance but marks edit-distance ≥ 2
  as incorrect. Farsi/Dari/Arabic targets are graded **exact / non-tolerant**.
- **MCQ (choose/listen/recognize) and matching casefold by default.** A distractor
  that equals the correct answer only by case is graded CORRECT (a real defect).
  `case_sensitive: true` opts a single exercise out of casefolding.
- Overlay exercise keys live under the `exercises:` map; each has some of
  `instruction`, `correct_option`, `distractors`, `accepted_answers`, `feedback`.
- **Feedback text is inert — never rendered to the learner.** Do not rely on
  feedback to "explain away" a wrong/incomplete answer; if the answer set is wrong,
  it is a defect regardless of what feedback says.

## What to check on every pack

1. **Answer correctness (target language).** Is each `correct_option` /
   `accepted_answers.value` actually correct, natural, and register-appropriate in
   the target language for the stated instruction?
2. **Missing valid answers.** For free-text, is there an obvious valid learner
   answer (common variant, un-contracted form, natural synonym) NOT in
   `accepted_answers`? (See latin distance-≥2 rule — a missing variant fails.)
3. **Bad distractors.** Is any distractor accidentally a correct/valid answer, or
   correct-except-for-case under casefolding?
4. **Gloss correctness.** Does each `gloss` / `example_gloss` accurately describe
   the target-language word/phrase it glosses? (Watch for a gloss that displays the
   correct answer, or that means a different word — a known bug class.)
5. **Instruction ↔ answer coherence.** Does the L1 instruction actually ask for the
   answer that is keyed correct? Under-specified role-play prompts (instruction
   states only the prompt-giver's line but the only accepted answer is a full
   multi-turn block) count here.
6. **Register / cross-lane consistency** where visible within the file.

## Out of scope — do NOT report

- Compiler warnings (matching_pairs pool size, missing example_gloss on 1.0 packs).
- matching_pairs `left==right` legit cognates; matching_pairs valid categorization
  duplicates; dialogue_comprehension empty `target_blocks` when a `media_asset_key`
  is present (audio comprehension — answerable by design).
- English-side realization prose (a separate clean review already covered it).

## Output format — structured, one block per defect

For EACH defect, emit exactly:

```
FILE: <relative path>
CK: <exercise or teaching content key>
CLASS: <answer-wrong | missing-answer | bad-distractor | gloss-wrong | instruction-incoherent | register>
LANE: <IN-LANE | NATIVE>
EVIDENCE: <the exact offending value(s) + why it is wrong>
FIX: <concrete proposed change>
```

- **LANE = IN-LANE** when the fix is English-side or mechanical and safe for a
  non-native to apply (e.g. add `case_sensitive: true`, fix an English instruction,
  add an obviously-valid missing Dutch/German/French/Italian variant that a sibling
  file already confirms).
- **LANE = NATIVE** when the fix requires native target-language authoring judgment
  (Farsi/Dari always NATIVE for any sentence-level change; Dutch/German/French/
  Italian answer/gloss rewrites are NATIVE unless a sibling file confirms).

If a pack is clean, emit one line: `CLEAN: <file>`. End with a one-line tally:
`TALLY: <file-count> files, <defect-count> defects (<in-lane> in-lane / <native> native)`.

Be precise and conservative — a false positive that trains the team to ignore the
review is worse than a miss. Quote the exact value you object to.
