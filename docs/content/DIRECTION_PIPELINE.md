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
* `inject` writes one file per course group / pack into `scripts/manifest.d/content/<group>.txt` and `scripts/manifest.d/practice/<pair>.txt`
  (overwriting only its own files), so parallel directions never conflict on a shared manifest. Readers glob the dirs in sorted order.
* Overlays/packs are written with `review.status: unreviewed`, `required_next_reviewer: native_speaker_review`.
  Native review of the translated text is still required (contrastive notes, register, distractor plausibility).
* The generated `scripts/backfill_lexemes_<x>_<t>.py` is a clone of the sibling's backfill (so the sibling must use
  `_target_lexeme_backfill_common.py`, like de-en and the generated ones) with the gloss tables replaced. Levels that were not
  derived get empty tables.

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
