# Deriving a new X->T direction from a sibling Y->T

`scripts/derive_direction.py` turns "author a whole direction by hand" into "translate a flat list of strings".
Use it when a direction with the **same target language** already exists (nl-en, fa-en, prs-en, de-en are siblings
of any new X->en). It does not replace native review; it removes the YAML authoring, the plumbing and most of the
agent context re-reading.

## What is (and is not) language specific

A direction = shared target realization (never touched) + overlay per unit + practice pack per unit + lexeme
backfill + manifest files. Only the learner-language strings differ between siblings:

| Artifact | Learner-language strings | Everything else |
|---|---|---|
| overlay | titles, gloss, note, example_gloss, instruction, feedback, option / answer / pair clue texts, accepted-answer notes | ids, structure, English answer sets, statuses |
| practice pack | `frame` / `feedback_frame` / `text_blocks` texts with `language_code == <learner>` | slots, tags, presets, answer derivation |
| backfill | one gloss per English token | POS, tags, plumbing (`_target_lexeme_backfill_common.py`) |

Strings that the same unit of a non-Latin-script sibling also contains (English answers, numbers, names) and
placeholder-only strings are never sent to the translator.

## Workflow

```bash
S=de-en; N=es-en                       # sibling, new direction
python3 scripts/derive_direction.py extract  --sibling $S --new $N --levels a1     # -> .local/derive/$N/
# translate: for every NAME.src.json write NAME.tr.json ({"u1": "...", ...}); read GUIDE.md first
python3 scripts/derive_direction.py status   --new $N                              # coverage per file
python3 scripts/derive_direction.py inject   --sibling $S --new $N --levels a1     # overlays, packs, manifests, backfill
python3 scripts/derive_direction.py validate --sibling $S --new $N --levels a1     # compiler + corpus gates
```

* `extract` is incremental: re-running it after the sibling changed keeps every translation whose source text is
  unchanged and re-queues only the changed strings.
* `inject` refuses to run when a placeholder (`{slot}`) or `*asterisk*` span differs from the source, when the sibling text
  drifted since extract, or when ids are untranslated (`--allow-missing`, `--force` override).
* `inject` writes one file per course group into `scripts/manifest.d/content/<group>.txt` (overwriting only its own files) and
  **merges** `scripts/manifest.d/practice/<pair>.txt` with what is already there (union of pack paths, sorted, no duplicates), so
  injecting A2 after A1 keeps the A1 packs. Parallel directions never conflict on a shared manifest. Readers glob the dirs in sorted order.
* Missing `scripts/manifest.d/content/<new>-<level>.txt` files are created automatically from the sibling's file (the generated
  backfill imports them); no manual seeding is needed. Existing files are never touched until inject writes the real lines.
* Overlays/packs are written with `review.status: unreviewed`, `required_next_reviewer: native_speaker_review`.
  Native review of the translated text is still required (contrastive notes, register, distractor plausibility).
* The generated `scripts/backfill_lexemes_<x>_<t>.py` is a clone of the sibling's backfill (so the sibling must use
  `_target_lexeme_backfill_common.py`, like de-en and the generated ones) with the gloss tables replaced. Levels that were not
  derived get empty tables on the first inject. Re-running inject for another level **merges** into the existing file: `LEVELS`,
  `GLOSSES_BY_LEVEL` and the gloss dicts of levels not being injected are kept verbatim (hand edits survive); only the
  injected levels are added or replaced.

## Adding new units to an already-derived pair (incremental)

Use this when the sibling gained units after the pair was derived (e.g. de-en A1 units 15-17, 22-24, 31, 62, 63, 66,
session 14). `--units` limits extract and inject to the named unit stems; `inject` merges the new units into the existing
`manifest.d/content/<group>.txt` (union, ordered by unit number) and `manifest.d/practice/<pair>.txt`.

```bash
S=de-en; N=es-en; U=a1_unit15,a1_unit16,a1_unit17,a1_unit22,a1_unit23,a1_unit24,a1_unit31,a1_unit62,a1_unit63,a1_unit66
python3 scripts/derive_direction.py extract --sibling $S --new $N --levels a1 --units $U
# translate every NAME.src.json (overlay + pack strings of those units only); ignore glosses.src.json (see below)
# add glosses for the NEW English tokens by hand to scripts/backfill_lexemes_<x>_en.py (A1 gloss dict)
python3 scripts/derive_direction.py inject  --sibling $S --new $N --levels a1 --units $U --no-backfill --allow-missing
python3 scripts/derive_direction.py inject  --sibling $S --new $N --levels a1 --units $U --no-backfill   # 2nd pass: tag filter sees the new lexemes
python3 scripts/derive_direction.py validate --sibling $S --new $N --levels a1
```

* `--no-backfill` keeps the hand-maintained `backfill_lexemes_<x>_<t>.py`; without it `inject` rewrites the A1 gloss
  dicts from `glosses.src.json`, which always covers the whole sibling level (not only `--units`).
* The first inject pass writes overlays, packs and the merged manifest line; the pack-template tag filter reads the
  pair's backfill through that manifest, so run inject a second time once the glosses and manifest are in place.

## Sibling choice

* **de-en is the cleanest sibling for packs**: its packs use only `en_<lvl>_uNN*` / `w_<token>` tags, so they port 1:1.
* nl-en / fa-en packs reference direction-specific `volume_<pair>_*` and `fa_en_*` tags. `inject` drops the templates
  whose tags the new backfill cannot produce (measured on units 01-14: nl-en 43 of 191 templates, fa-en 27 of 184).
  The remaining 78-85 % port as is.
* For the overlay, any sibling works; pick the one whose register matches (tu/usted ~ du/Sie). Contrastive notes
  that name the sibling language are flagged `CONTRAST` for rewrite and counted by `validate`'s leftover scan.

## Language specifics

`LANG` in the script holds the translator notes per learner language (register, script). RTL learner languages
(ar, fa, prs) need no overlay changes; pack text dicts get `direction: rtl`. For prs, `validate` also runs
`check_dari_register.py` (must report 0); derive fa from prs (or the other way) only with that gate and a
Dari/Iranian lexis note in the translator brief.

## Limits

* Only same-target siblings. en->X directions are authored; this is not a way to derive de-en from en-de.
* Native review is not automated. Treat the first derived direction per language like any new-language lane.
* AUTHORING_GUIDE section 8 (do not consult sibling files while authoring) is intentionally bypassed: the translator
  adapts, it does not author. The review pass must therefore look for calques of the sibling's phrasing.

# Deriving a new TARGET course (en->T) from a deeper target course: `scripts/derive_target.py`

`derive_direction.py` reuses one target course across learner languages. `derive_target.py` is the other axis: the learner
language stays English and the **target** language changes. It rebuilds A1 units of a deep course (en-nl: 67 A1 units; the deepest
A1 course, versus es 15, fr 14, de 24, it 24) as units of a thin one (en-es). The English side (glosses, titles, instructions, English
options, pair meanings, accepted English answers) is reused as is; only the target side is translated or authored.

```bash
SRC=en-nl; NEW=en-es; U="a1_unit23_money a1_unit16_health"
python3 scripts/derive_target.py extract --source $SRC --new $NEW --units $U --first-unit 45 --names Lotte=Elena,Omar=Mateo
#   -> .local/derive-target/$NEW/  atoms.src.json (translate)  author.src.json (author)  *.ctx.json  atoms.view.tsv  GUIDE.md
# write atoms.tr.json {id: text} and author.tr.json {slot: text}
python3 scripts/derive_target.py status                 # missing ids + lint flags (re-reads the work dir saved by extract)
python3 scripts/derive_target.py lexemes                # tokens that still need "gloss | pos"; write lexemes.tr.json
python3 scripts/derive_target.py inject                 # realizations, overlays, en-es manifest line, backfill block
python3 scripts/derive_target.py check                  # compiler validate + compile of the course, backfill --dry-run
```

`--first-unit` defaults to the next free unit number of the target course (es numbers A1-B1 continuously; derived units are A1 in
the A1 group). Coordinate it with other agents adding units to the same course: content keys must be unique.

## What is translated, derived, authored

| Piece | How |
|---|---|
| Teaching targets, examples, unit/lesson titles, prompt texts, media texts, pair target sides | **atoms**: translated once per distinct text; reused wherever the exact text occurs, including quoted inside English feedback |
| Media text that is a concatenation of cards (dialogues) or a card minus its speaker label | derived from the translated cards (cannot drift from the card text) |
| `introduced_tokens` | derived: tokens of the translated target + its examples |
| `tested_text` | derived when it is a sentence atom or the answer; otherwise **authored** (`#tested`: comprehension spans, matching word bags; must occur in the audio text) |
| `word_bank` tiles | derived from the translated answer and deterministically scrambled; source tiles with distractors become an authored `#bank` |
| Punctuation variants of accepted answers | derived (`X.` and `X`, like the source); real alternatives are authored (`#ans` with `||`, extra `#alt` on any exercise) |
| Distractors for target-language options, fill-in-blank frames and fillers, free-production answers | **authored** (`#dist`, `#frame`, `#ans`): wrong answers are plausible errors in the new language, never translations of the old errors |
| Notes and feedback that mention the source language (`*italic*` spans, unit cross references, leftover source words) | **authored** (`#note`, `#feedback`, `#instruction`): rewritten for the new language |
| `grammar_note` cards that explain source-language grammar | translated slot flagged `rewrite` + `GRAMMAR_REWRITE`: write the new language's own explanation |
| Content keys | slugs re-derived from the translation (lesson, teaching, media); unit number remapped |
| Cast names | `--names` maps them after translation (keep genders aligned: Lotte/Elena, Omar/Mateo) |
| Lexeme backfill | `lexemes` lists the new tokens; `inject` writes a marked, mergeable block into `backfill_lexemes_<x>_<t>.py` (`DERIVED_TARGET_GLOSSES`, `DERIVED_TARGET_POS`) |

Not derived: audio (media assets stay `pending_generation`) and native review. Practice packs are not derived from the source packs
either, but `derive_target.py packs` builds them from the injected units (below; the en-de depth run generated its packs from each
unit's lexemes and teaching sentences, see "German target" below).

## Practice packs: `packs`

```bash
python3 scripts/derive_target.py packs     # docs/content/practice/<pair>/a1_unitNN.yaml + scripts/manifest.d/practice/<pair>.txt
```

Unit-wide choose/listen/translate/match templates are built over the unit's `w_<token>` lexeme tags; sentence templates are anchored to
single-lexeme tags. A unit needs at least 3 usable lexemes (checkpoint needs >= 3 candidates for multiple choice and >= 6 for
matching pairs; the match template is skipped below that). Tokens that must not appear in packs (cast surnames, shop names, tokens a
learner has not met) go into `packs_exclude.json` in the work dir. Run `practice-validate` and the practice leakage and integrity
checks afterwards.

## Further work-dir inputs

* `en_override.json`: rewrites English text that is reused from the source overlay but names source-language grammar. Keys are exact
  strings, scoped (`<source content key>|title`, `|gloss`, `|example_gloss`, `|gloss:<key>`) or word level (`"~word": "rewrite"`).
* Scoped gloss keys: when two cards share a source word that becomes different target words, the atom key is
  `"<content key>#gk#<key>"` in `atoms.tr.json`.

## Lints (`status` / `inject`; errors block inject, acknowledge false positives in `ack.json` as `"<id>:<FLAG>": "reason"`)

* `GENDER` (es, it): a speaker-gendered predicate in a learner-produced answer (`Estoy cansado`) needs the other gender as an
  accepted alternate (`#alt`). It caught a missing feminine form in the pilot.
* `REGISTER`: the source marks formal (`u`/`uw`) or informal (`je`/`jij`) and the translation reads the opposite register.
  Atom context lists `register` so the translator keeps tu/usted aligned with the source roles.
* `CONTRACTION`: an obligatory contraction was not applied (es `de el`->`del`, fr `de le`->`du`, it `di il`->`del`). Never add the
  uncontracted form as a variant. English contractions (`don't`/`do not`) are folded by the shared grader and must not be listed
  as variants either (AUTHORING_GUIDE section 18).
* `TILES`: an accepted word-order variant uses other words than the tiles (the bank is built from the canonical answer).
* `GLOSS_KEY`: a reading card's gloss key must be one whole word of the translated card text (multi-word phrases fail the compiler).
* `VARIANTS` (warn): the source accepted more distinct forms than the translation gave.
* `SOURCE_GRAMMAR`: English text (feedback, notes, options) still explains source-language grammar (separable verbs, het-words, main
  clause order, local culture). Rewrite it via the `#note` / `#feedback` / `#options` slots or `en_override.json`.
* `OPTIONS_COUNT`: a reading exercise with an authored `#options` list does not give the same number of options as the source.
* `PAIR_RIGHT_TARGET`, `GRAMMAR_REWRITE`, `LEFTOVER` (warn/error): review hints; `LEFTOVER` means source-language words survived in
  an English field.

## German target (`de`, first non-es target)

`CFG["de"]` carries what German needs; the same switches are generic and reusable for other targets.

* `case_sensitive`: tested text, tiles and register detection keep case (nouns are capitalised; `Sie`/`Ihnen`/`Ihr` is formal
  and `sie` is not). `slug(translit=...)` writes `ae/oe/ue/ss` in file names and keys; typed answers also accept the
  transliteration variants (`schlaeft`, `Strasse`) because learners may not have umlaut keys.
* Gender: mode `agent` (`Ich bin Student/in`): a gendered agent noun in a learner answer needs the other form as `#alt`.
* Register: du/Sie pairs are checked against the source u/je roles (`REGISTER`); contractions `im am zum zur vom beim` are required
  where the grammar demands them (`CONTRACTION`).
* `CASE` lint: a capitalised word in mid-sentence that is not a known noun, or a lowercase noun, is flagged using the backfill
  lexicon. Acknowledge real exceptions in `ack.json` (nominalised verbs and adjectives: `Essen`, `Gute`, colour nouns; proper
  names such as `Theater Zum Stern`; the particle `mal`).
* `--suffixes nl=de` maps topic words in file names and unit keys (`bakker=baeckerei` gives `a1_unit90_baeckerei.yaml`); units
  continue the target's numbering (`--first-unit`).
* Extra author slots the strict residual check needs: `#opts` (English options that quote a source word), `#gv:<key>` (gloss values),
  `#desc` (course description), `#prompt<N>` (English prompt blocks), `#title`/`#gloss` (rewritten grammar cards). `strict_residual`
  fails when a source-language word survives in a learner-facing English field (cognates such as `Party`, `blond` are masked).
* Lexeme glosses: `lexemes.tr.json` takes `"gloss | pos"`, or `"=lowercase"` to alias a sentence-initial capital onto its
  lowercase citation form (written to `DERIVED_TARGET_CITATION`).
* Rewrite the grammar notes for German (cases, verb-second, separable verbs, `kein/nicht`) instead of translating the Dutch ones;
  keep each to a short why. Keep `Write exactly` copy tasks as they are at A1.
* Always pass `--new en-de` (or rely on the saved `plan.json`); an earlier default of `en-es` once wrote the wrong config.

## Limits and pitfalls

* The overlay English (glosses, English options, pair meanings) is reused unchanged, so a translation must keep the meaning of the
  source sentence. Where Spanish needs another construction (`Ik lees graag` -> `Me gusta leer`), choose the translation that matches the
  English gloss; an example whose words the card never introduces is fixed by example tokens being introduced on the card.
* Culture is not translated: Dutch-specific topics (bike rental, waste separation, gemeente) need a localisation decision, not a
  translation. Pick portable units first (health, money, hobbies, phone, appearance, animals, colours, seasons, restaurant).
* Native review of the derived target text is required; derived units are written `unreviewed` / `native_speaker_review`.
* Tested with en-nl as source only; other sources need their own `CFG` formal/informal markers in the script.
