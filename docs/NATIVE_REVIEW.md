# Native-review checklist (consolidated 2026-11-05)

One checklist per language, highest priority first. Every item names the place to look (file under `docs/content/` or a UI
locale key) and the question to put to the reviewer. Tick the box, write the verdict next to it, and fix or file the change.

Priority: P1 = learner sees wrong or unnatural language in the core path (wrong gender or person, register errors, wrong word);
P2 = plausible but unverified wording; P3 = polish or a design decision.

Sources: completion-rescore, hiar-fix, session20-group3, session19-cross-batch, qualfix, notes-fix and notes-fix2 (all 2026-11-04/05
logs in `.local/logs/`, not in git), PR #145 (Privacy/Terms notice) and PR #149 (password change) UI strings, plus the earlier open
questions. Held content packs not listed here are in `docs/RAMIN_REVIEW_BACKLOG.md`. Process notes for reviewers:
`docs/NATIVE_REVIEW_full_turn_instructions_2026-07-31.md`.

Reviewer shortcut: for the cross pairs (X-ar, X-fa, X-prs, X-hi) the target text is shared with the `en-<target>` course, so a
correction to a target sentence is made once in `docs/content/realizations/<target>/` and flows to every learner language.
Corrections to learner-language text are made in `docs/content/overlays/<pair>/` (per pair).

## UI strings (all 14 non-English locales; ask each language's reviewer)

Files: `packages/shared/src/i18n/locales/<code>.json` (ar es fa fr hi it ja ko nl pl prs ro ru zh). English source: `en.json`.

- [ ] P2 `legal.english_only_notice` ("These documents are currently available in English only.") and `legal.agree_notice`
  ("By continuing you agree to the Terms of Service and Privacy Policy.", `<terms>`/`<privacy>` tags wrap the link text). PR #145.
  Question: natural and legally neutral? Do the tags still wrap exactly the words "Terms of Service" / "Privacy Policy"?
- [ ] P2 `account.*` (PR #149), 14 strings of the Change-password form: `title`, `current_password`, `new_password` (includes
  "at least 8 characters"), `confirm_password`, `submit`, `saving`, `success` ("signed out of your other devices"), `mismatch`,
  `too_short`, `same_as_current`, `wrong_current`, `unavailable` ("This account has no password to change", i.e. social sign-in
  accounts), `rate_limited`, `error_default`.
  Question: are these the wording banks/apps use in your language? Is "signed out of your other devices" clear? Is the number 8 shown
  correctly in RTL (ar, fa, prs)?
- [ ] P3 fa vs prs: the two UI files must differ (Iranian vs Afghan wording). Question (fa and prs reviewers each): any word that
  sounds like the other variety?

## Arabic (ar)

- [ ] P1 Gloss gender, `hiar-fix`: b1 `أساعدك` / `اتصلت` / `بك` (docs/content/overlays/en-ar, b1 units; X-ar lexicon
  `docs/content/lexicon/<X>-ar.json`). The gloss says masculine addressee, but the dialogue partner may be a woman, and the
  Arabic is unvocalised. Question: which readings are right for each dialogue line? Should the gloss say "(masc. or fem.)"?
- [ ] P1 b1 `عندك` set to feminine because Yusuf is talking to Nour (scripts/backfill_lexemes_en_ar.py, b1 entry). Question: confirm
  the feminine reading in that dialogue, and that the gloss does not mislead in other contexts.
- [ ] P1 Applied-list audit: 7 re-translated glosses x 8 learner languages plus 47 direct fixes in `docs/content/lexicon/<X>-ar.json`
  and `docs/content/tm/<X>.json` (examples: de `ein (masc.)` for واحدا, de `sie beginnt (f.)` for تبدأ, es `verlo` for مشاهدته,
  es `las patas` for البطات, ro `fericită`). Full list: `.local/logs/hiar-ar-applied-2026-11-05.json` (tok, old gloss, new gloss,
  confidence). Question: confirm each "medium" confidence row; the reviewer needs Arabic plus the learner language, so route by
  language (de, es, fr, it, nl, pl, ro, ru).
- [ ] P2 ~50 low-confidence X-ar gloss suggestions and ~150 "missing (m.)/(f.) label" suggestions, not applied. Same JSON file,
  `suggestions` section. Question: accept or reject each; is a gender label needed for a learner at this level?
- [ ] P2 First-person verbs glossed masculine only (speaker Layla is female): es `تشرفت`/`تشرفنا`/`أهلا`, it `تشرفت`, pl
  `سعدت`/`اخترت`/`أود`, ru `شربت` (X-ar lexicons). Question: should these be gender-neutral or shown as feminine for Layla?
- [ ] P2 `docs/content/overlays/en-ar/b1_unit35.yaml` `yusuf_contrast`: gloss "Yusuf says he can't ..." for a first-person Arabic
  sentence. Question: is the person right?
- [ ] P2 Tashkeel: Arabic text is deliberately unvocalised (A1 packs, realizations), while TTS needs vowels. 2490 audio strings
  have no tashkeel (`session13-audio` log) and render as the engine guesses. Question: which items (names, verbs with ambiguous
  roots, words with shadda) need full or partial tashkeel to be read and spoken correctly, and should learners see it at A1?
- [ ] P3 RTL punctuation and mixed Latin/Arabic: `ru-ar`, `pl-ar` (session 20 batch 2 fixed "Nur" to "Nour" in pl). Question:
  any other name rendered differently from the course's spelling?

## Persian (fa, Iranian)

- [ ] P1 Register of the whole `en-fa` course and the eight X-fa cross pairs (de es fr it nl pl ro ru -> fa): colloquial
  vs formal consistency (`docs/content/overlays/<X>-fa/`, `docs/content/realizations/fa/`). Question: is the register consistently
  Iranian colloquial where dialogues are casual, and formal in service encounters? Any Afghan-only word?
- [ ] P1 `docs/content/realizations/fa/a1_unit36` card text renamed in #165 (`تنبل نیست (he/she is not lazy)`) and the gloss
  lexicons keyed on it. Question: natural phrase for "is not lazy"?
- [ ] P2 `hi-X` / `X-fa` romanisations are in `romanize_*` exercises (e.g. `fa.a1.unit01.lesson01.exercise08.romanize_salam`,
  `romanize_goodbye` "khoda hafez"): accepted Latin spellings. Question: which transliterations do learners expect?
- [ ] P3 fa/prs audio is blocked on keys; when voices exist, review pronunciation of names (Mateo, Nour, Fenna).

## Dari (prs, Afghan)

- [ ] P1 All 18 prs course directories (`docs/content/overlays|practice/` for de-prs en-prs es-prs fr-prs it-prs nl-prs pl-prs
  ro-prs ru-prs and prs-de prs-en prs-es prs-fr prs-it prs-nl prs-pl prs-ro prs-ru) plus `docs/content/realizations/prs/`. Several
  were produced by translating and then mechanically converting Iranian wording to Dari (`prs-es`: 432 findings, 1887 replacements;
  `prs-de`: `ببخشید` replaced by `معذرت`). Question: does anything still read as Iranian (Tehrani contractions such as
  می‌خوام / می‌تونم, Iranian-only words, copied Farsi sentences)? Is the Dari idiomatic rather than a calque?
  `scripts/check_dari_register.py` is 0 but only catches listed words.
- [ ] P1 Idioms and set phrases in Dari: greetings, farewells, politeness (`به امید دیدار` close_exchange in `prs.a1.unit01.lesson03.exercise08`,
  `بلی، خوب است!` responses, `چاشت` for afternoon/lunch). Question: natural for a speaker in Kabul/Herat? What is the usual
  alternative?
- [ ] P1 b1 prs notes (`docs/content/realizations/prs/b1_*`): 42 notes were recoded as English prose around Persian examples
  (notes-fix2). Question: are the Persian examples in them Dari, not Iranian?
- [ ] P2 `de-prs` "gefunden worden" reworded (session 20); `it-prs` Persian Yeh fix. Question: check the replacements read well.
- [ ] P2 Names and spellings of foreign words in Dari (`اپارتمان`, `بایسکل`, `اپریل`, `هژدهم`). Question: the Afghan spelling for
  each?

## Hindi (hi)

- [ ] P1 Lena/लेना ambiguity: `scripts/_hindi_names.tsv` standardises Lena as `लेना`, which is also the verb "to take" (and
  `लीना` is the only alternative). Appears in hi-X overlays and practice, e.g. `docs/content/overlays/hi-de/a1_unit76.yaml`,
  `hi-es/a1_unit54.yaml`. Question: keep `लेना`, switch to `लीना`, or use `लीना` in names only? Whatever is chosen, change the TSV
  and re-run `scripts/_hindi_name_check.py`.
- [ ] P1 Person-name spellings (3750 edits in #170; table `scripts/_hindi_names.tsv`): confirm the standard spelling for each name,
  especially `मातेओ` (Mateo), `मैथ्यू`, `थॉमस`, `फ़ेना`, `फ़ेलिक्स`, `कियारा`, `योनास`, `दिएगो`, `सैंडर`, `मैग्डा`, `पेत्रु`, `कासिया`, `इरा`.
  Question: which spelling would a Hindi speaker write?
- [ ] P2 About 4400 places where a Latin name stands inside a Hindi sentence in hi-X overlays (for example "Mihai कहता है").
  Question: convert to Devanagari everywhere, or leave Latin? (Converting risks answer matching: exercises that accept the
  name in one script only. Decision needed before any bulk change.)
- [ ] P2 Hindi transliterations of target-language words in hi-X cards (names, places, loanwords), session 20 hi pairs
  (`docs/content/overlays/hi-*/`). Question: spot-check 20 cards per pair.
- [ ] P2 `en-hi` realization cards that carry Hindi plus English gloss (9 cards, now localised via `target_text`). Question: is
  the Hindi gloss correct?
- [ ] P2 Hindi dinner/prompt fix in this PR: `docs/content/overlays/hi-nl/a1_unit23.yaml` `write_dinner_summary` now accepts Dutch
  variants only; plus the same fix in every X-nl, fa/ru/prs-nl and other pairs listed in the PR. Nothing for a Hindi reviewer
  unless the Hindi instruction reads wrongly.

## Spanish (es)

- [ ] P1 `quedarnos`: `docs/content/realizations/es/a2_unit91_vakantieplannen.yaml`, audio `es.a2.audio.vakantieplannen.vamos_a_quedarnos_una_semana.01`
  and `es.a2.unit91.lesson05.exercise04.listen_hotel` (distractor "Vamos a quedarnos una semana en el camping"). Question:
  "Vamos a quedarnos" natural for ir a + reflexive infinitive with a clitic attached? Prefer "nos vamos a quedar"? Is the
  distractor wrong for the right reason?
- [ ] P1 `mudo`/`mudarse`: `docs/content/realizations/es/a1_unit15_comparisons.yaml` (lines about `quiere mudarse`, "Por eso
  quiero mudarme") and `a1_unit14_housing.yaml`. Question: "mudarse" for "move house" is correct in all regions taught? Is "mudo"
  (first person present, or the adjective "mute") ever shown where it could be misread?
- [ ] P1 "a lo mejor": `docs/content/realizations/es/b2_unit02_especulacion.yaml` (card "Seguro o a lo mejor", register notes
  near line 27). The unit says it takes the indicative in everyday speech. Question: correct, and is the register label
  accurate for Spain and Latin America?
- [ ] P3 `es-prs` a1_unit22 (practice and overlay) contains "quedarnos"; check the Dari rendering.

## French (fr)

- [ ] P1 "Je compte" + infinitive, intention: `docs/content/realizations/fr/a2_unit93_vakantieplannen.yaml` (card title line 329,
  "Je compte suivre un cours", "Je compte déménager"); overlay `en-fr/a2_unit93.yaml` and the wrong-answer distractor "Je compte à
  déménager". Question: is "compter + infinitif" natural for plans at A2? Is "je compte" stronger than "je pense" here?

## German (de)

- [ ] P1 `werden` for plans: `docs/content/realizations/de/a2_unit96_vakantieplannen.yaml` ("Wir werden eine Woche in einem Hotel bleiben",
  "Im August werde ich nach Italien fahren", audio `de.a2.audio.vakantieplannen.wir_werden_eine_woche_in.01`, exercises
  `de.a2.unit96.lesson05.exercise03/04`) and overlay notes `en-de/a2_unit96.yaml`. Question: in everyday German "werden" for
  near plans is marked as formal; should the main examples use present tense with a time word, as the note itself says?
- [ ] P3 `de-ro`, `de-fr` etc. instructions using "Sie" vs "du": session 14 convention is Sie to clerks and doctors, du between
  friends. Question: any breach?

## Italian (it)

- [ ] P1 "Allora L'aspetto lunedì" (capital L, no comma): `docs/content/realizations/it/a2_unit83_afspraak_verzetten.yaml` line 618
  and `docs/content/overlays/en-it/a2_unit83.yaml` lines 432-457 (matching pair and accepted answers with and without full stop).
  Question: should it be "Allora, l'aspetto lunedì" or "Allora ti aspetto lunedì"? Is the intended meaning "I'll expect you / see
  you Monday"?
- [ ] P2 `it-prs`, `it-fa`, `it-ar`, `it-hi`: Italian learner-language text is fine, but check the Italian example sentences quoted
  in the target-language notes keep accents and apostrophes.

## Romanian (ro)

- [ ] P1 "a conveni" (to suit): `docs/content/overlays/en-ro/b2_unit05.yaml` line 236 (gloss "suits / is convenient") and line 534
  (feedback: "V-ar conveni săptămâna viitoare?" polite proposal) plus `docs/content/realizations/ro/a2_unit76_afspraak_verzetten.yaml`.
  Question: is "V-ar conveni" the right polite form for a booking request? Is the gloss right?
- [ ] P2 ro a2 grammar notes (unit21-24 `*_grammar`): English glosses were removed from the Romanian spans in notes-fix. Question:
  do the cards still read as complete Romanian?
- [ ] P2 `ro` b1 unit16 "prefer" false-positive handling: confirm "a prefera" forms are right.

## Polish (pl)

- [ ] P1 Grammar notes rewritten without English: u8 `gdzie_jest_note`, u9 `prosze_bezokolicznik`, `jak_dojsc_note`, `multi_step_note`,
  u13 `wolec`, u14 `dobry/ale` recap, u15 `jechac_note`, `dziesiatej_rano_note`, u16 `boli/czuc_sie`
  (`docs/content/realizations/pl/*.yaml`, A1 and A2/B1 files). Question: is the Polish correct and natural?
- [ ] P1 Titles translated into Polish-learner languages for `prosze_bezokolicznik` ("Please + infinitive") and `jechac_note`
  ("To go (by vehicle)") in 11 X-pl overlays (de es fr it nl ro ru hi ar fa prs). Each language's reviewer should check them.
- [ ] P2 Polish gender in glosses for names and verbs in `pl-ar`/`pl-hi`/`pl-prs` (e.g. `Jestem chory i potrzebuję lekarza` vs
  `chora`): does every first-person example have a gendered counterpart where needed?

## Dutch (nl)

- [ ] P2 Dutch variants added by this PR in every X-nl pair (`write_dinner_summary`, `write_self_intro`, `give_price`,
  `respond_wanneer_verjaardag` etc., all `docs/content/overlays/*-nl/`): check `Omar betaalt de rekening, en het is vijfendertig euro.`
  and the other variants are natural Dutch and accepted spellings.
- [ ] P3 en-nl homograph overrides: `docs/EN_NL_HOMOGRAPH_OVERRIDE_CANDIDATES.md`.

## Russian (ru)

- [ ] P2 ru-ar instructions reversed in 2 places (fixed in #160), and ru-X register of address (ты vs вы) in the new nl/pl/ro/ru
  batch. Question: consistent ты between friends and вы to clerks?

## Japanese, Korean, Chinese (UI only)

- [ ] P2 The `legal.*` and `account.*` strings above in `ja.json`, `ko.json`, `zh.json`. Question: politeness level for a
  password form (です/ます, 합쇼체 or 해요체, 您 or 你)?
