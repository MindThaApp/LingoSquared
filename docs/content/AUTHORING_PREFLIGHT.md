# Authoring pre-flight checklist (PASTE VERBATIM INTO EVERY AUTHORING DISPATCH)

**Why this file exists.** On 2026-07-12 three fresh-context reviews found 23
defects across three content waves. Every single one was a class the dispatch
prompt did NOT mention. The one class that WAS quoted verbatim in those same
prompts (duplicate/gloss-sharing matching_pairs lefts) came back with **zero**
findings in both reviews — after needing 5 fixes in the previous wave.

The lesson: authors do not reliably apply rules that are merely "binding" in
an auto-loaded doc. They apply rules that are in front of them while writing.
**Cost consequence:** a cheap author + this checklist + validators is far
cheaper than an expensive reviewer finding the same bugs afterwards. Paste
this block into the dispatch prompt itself — do not link to it.

---

## THE CHECKLIST (author: you must self-report on EVERY item before claiming done)

### 1. Every exercise has exactly ONE defensible correct answer
- No distractor may also be correct.
- Read each exercise as a smart learner who knows the material: could they
  justify a different answer? If yes, it is broken.

### 2. matching_pairs
- **No duplicate LEFT item. No two lefts sharing the same gloss/answer.** The
  lefts are the learner's ONLY discriminator — they must discriminate on real
  meaning, not be interchangeable paraphrases ("a polite way to ask for a
  change" vs "a polite way to ask someone to do something" = unanswerable).
- **Duplicate RIGHT values are FINE and intentional.** Many lefts → one right
  is valid pedagogy (nl u13: 3 items → "lekker", 3 → "leuk"). Do not "fix" it.

### 3. Production prompts (writing_prompt / dialogue_response / free text)
- If the instruction is satisfiable by MORE THAN ONE taught form but you grade
  against ONE exact string, correct learners get marked WRONG. **Name the form
  the prompt wants.**
- If the instruction states a word count ("three words"), the accepted answer
  MUST have exactly that many words.
- The feedback/example you display MUST be the same string you accept. Showing
  one model answer and grading against another fails the learner who copies you.

### 4. Prompts must not contain untaught vocabulary
- The compiler historically checked only `tested_text`, NOT
  `prompt.target_blocks`. **Hand-check target_blocks.**
- **Vocabulary is CUMULATIVE across the course, not unit-local.** A token
  taught in unit 12 is legitimately usable in unit 17 — do not drop good
  content believing otherwise. Check prior units before assuming "untaught".
- Do not forward-reference a word from a LATER lesson in the same unit.

### 5. Dialogue cards must match the unit's own AUDIO
- Enumerate the audio asset's speaker-labelled turns. Enumerate your teaching
  cards. Then verify: every turn is taught, and **every line is attributed to
  the speaker who actually says it.**
- Real failure: a card made Настя ask how many rooms were in her OWN apartment,
  because Дима's line was put in her mouth.
- Never bake a name into a card's `text` — use `TextBlock.speaker`.

### 6. Character canon is cross-unit — GREP BEFORE YOU WRITE
- Recurring characters have established facts. Italian unit17 made Sam a
  teacher; unit02 had pinned him as an engineer. No validator catches this,
  and the wrong line would have been sent to the audio RECORDING queue.
- Before writing any dialogue: grep the established profile of every character
  you use, and state in your report what you found.

### 7. Register
- Quote the lane's register pin (docs/content/CLAUDE.md) and follow it exactly.
- Keep register internally consistent within a unit, and correctly conjugated.

---

## REQUIRED SELF-REPORT

Before you claim the task is done, walk items 1–7 and state, per item, what you
checked and what you found. "Followed the guide" is not a self-report. If you
found nothing for an item, say so explicitly — a false "clean" is worse than a
flagged uncertainty, and the reviewer WILL check.

Then run the acceptance command verbatim and paste its REAL output. Never
report a pass you did not personally run.
