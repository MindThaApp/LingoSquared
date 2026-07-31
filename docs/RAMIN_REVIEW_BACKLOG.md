# Ramin's review backlog

Things the autonomous coordinator (Claude) decided or deferred that Ramin may
want to review when he has a moment. **Nothing here is blocking** — it is a
queue, not a set of questions. Newest at top. The coordinator appends; Ramin
prunes.

Standing mandate (2026-07-23): Claude runs the build autonomously as
coordinator/architect/engineer with a subagent team; only genuinely blocking
or owner-reserved decisions interrupt Ramin. Everything else lands here.

---

## 🔴 SYSTEMIC (2026-07-30) — ~327 `dialogue_comprehension` LISTENING exercises unanswerable pending audio (PRODUCT DECISION)

Corpus-wide scan found **362** lesson exercises of `type: dialogue_comprehension` with **empty
`prompt.target_blocks`**. The compiler wires playable audio (`audio_text`) ONLY for `listen_select`/
`listen_type`/`listen_order` — **never** `dialogue_comprehension` (verified in `compile_exercise`,
compile_content.py:3638). Their `media_asset_key` points at a pre-recorded asset that is
`status: pending_generation`. Net: with no audio AND no readable `target_blocks`, the learner sees only
the (source-language) instruction + answer options — nothing to comprehend.

- **✅ FIXED by me (35 permanent cases): all fa + prs** — those languages have zero TTS/recording network
  EVER, so text is the only possible stimulus. Populated `target_blocks` from each lesson's own taught
  dialogue. (This is already the established project convention — pl/hi realizations do it for 100% of
  their dialogue_comprehension, nl for ~91%.) fa/prs now 0 broken.
- **🔴 REMAINING ~327 — YOUR CALL, in TTS-capable langs:** en **58**, de **27**, fr **65**, ru **53**,
  ar **51**, ro **19**, es **22**, nl **32**. These are (intended) LISTENING exercises whose content_keys
  are literally `listen_*` — they're waiting on audio generation. **In-scope for the 6 review directions:
  en (58 — affects fa-en/prs-en/nl-en) and nl (32 — affects en-nl).** Two options: (A) generate the
  audio (English/Dutch/German/French/etc TTS all exist) — preserves the listening-skill assessment; or
  (B) populate `target_blocks` to convert them to reading-comprehension (mechanical, I have the script) —
  makes them answerable now but removes the listening practice. **I did NOT touch these** — converting a
  listening exercise to reading is a pedagogy/product decision, not a coordinator call. If you want (B)
  for en/nl (or all langs), say so and I'll run the same fix. Until then, every one of these renders
  unanswerable in the current no-audio build.

---

## 🔴 SYSTEMIC (2026-07-30) — fa/prs translate answers ending in `.`/`!` are UNTYPEABLE (grading vs keyboard) — YOUR CALL

Code-verified by the batch-23 en-prs 29-33 reviewer, two facts combine into a real bug:
- `backend/app/review/grading.py`: fa/prs resolve to `script="arabic"` → `tolerant=(script=="latin")` is **False**,
  and `_normalize()` never strips punctuation. So a single missing/extra `.` `!` `؟` `،` is graded flat WRONG.
- `packages/shared/src/lib/scripts.ts`: the in-app virtual keyboard's Perso-Arabic layer has only digits +
  `، ؛ ؟` — **no period `.` and no `!` on ANY layout**. A learner without a native device keyboard **physically
  cannot type** a period or exclamation mark.

⇒ Any translate/free-text exercise whose ONLY `accepted_answers` variant ends in `.` or `!` is **unanswerable**
via the app keyboard (HIGH); `؟`-only is typeable but needs a symbol-layer toggle (MEDIUM). The corpus already
has an established mitigation convention — en-fa and en-prs unit29 carry BOTH punctuated and unpunctuated
variants — but **en-prs a1_30+ dropped it** (8 HIGH period/! cases in u31/32/33 + several MEDIUM ؟ in u30-33).
Likely present in more unreviewed en-prs a2/b1 too.

**THREE fix options — pick one and I'll execute:** (A) **grading.py mechanism fix** — strip trailing terminal
punctuation on both sides before comparison (one change, fixes all langs at once; cleanest/altitude-correct, but
changes grading semantics — your call since it's product behavior). (B) **keyboard fix** — add a period key to
the Perso-Arabic layout in scripts.ts (fixes typeability, keeps grading strict). (C) **content dual-variant
pass** — add the unpunctuated companion to every fa/prs free-text `accepted_answers` (matches the existing
en-fa/u29 convention; additive/safe but touches many overlay files, a band-aid). I recommend (A). Until one
lands, I'm HOLDING en-prs a1_23/30/31/32/33 (their only/main blocker is this class) rather than flipping them.

---

## ⭐ Native review — BATCH 1 (2026-07-27): 20 wave-4 packs reviewed + fixed + flipped

Fresh-context native review (4 sonnet reviewers, AUTHORING_PREFLIGHT.md + realization/overlay +
live backfill-pool cross-check) of the 20 packs edited in wave 4: en-fa a1_31-36, a2_12/13/14/16,
b1_01/02/03/04/06/11 + en-prs a1_06/25/26/36. All 20 now `review.status: reviewed`. This is
batch 1 of the full 509-pack native-review ship-gate (489 remain — see the note at the end).

**CRITICAL found + FIXED (commit 9ce89823):** en-fa units 31-36 lesson01 choose.001 /
translate.003 / volume_translate drew the units' **junk label-phrase lexemes** (POS 'phrase'
authoring-label strings the backfill persists because `_label_guarded` is scoped to 25-30/37-57,
leaving 31-36 in the gap — 51 such rows corpus-wide, 35 in 31-36). choose.001 showed the English
answer inside the prompt; translate.003's only accepted answer was the unanswerable label string —
a real checkpoint mis-grade. Fixed pack-side (narrowed those 18 item slots to
[noun,verb,adjective,adverb], excluding all 'phrase' lexemes). NOTE: the same unrestricted-phrase
pools exist in en-fa units 53-57 + b1_08-16 (no in-unit junk, so only course-scope Endless-Practice
exposure — lower severity, NOT yet fixed); and the durable source fix (widen `_label_guarded` +
delete the 51 persisted rows) still needs a dev DB (BLOCKED).

**MAJOR found + FIXED (commit bca647be):**
- Mis-glossed lexeme shown as the answer (lesson-scoped backfill gloss overrides; take effect on
  re-backfill): en-fa `باشید` "be (polite)" → "(if) you (pl.) be" in b1_03's subjunctive paradigm;
  en-prs `خراب` "broken" → "bad; broken" in a1_25 (weather sense).
- False unit-attribution feedback over untagged course-scope pools (anchored the shared presets to
  the wave-4 generated unit tags): en-prs a1_25 adverb_word_pool, a1_26 unit_noun_pool +
  verb_adjective_pool; en-prs a1_06 people_choose.001 feedback genericized (role_word can draw
  مشتری from a1_08); en-fa b1_01 lesson04.choose.001 dropped `symbol` (was drawing و glossed
  "and (links tens+units)").

**RESIDUAL — MINOR / known-limitation (NOT blocking; documented, not fixed):**
- **Systemic course-scope synonym-collision (corpus/compiler-level):** at Endless-Practice course
  scope, broad no-semantic-tag MC pools can draw two synonyms with the identical gloss (اگه/اگر
  "if"; نتونستم/نمی‌تونستم "I couldn't") → two correct MC options. Reachable in en-fa b1_01/02/03/
  04/06/11 choose.001 (and the already-disclosed A2 بیایید/بیاید, خوب/خوبی). Low per-instance
  probability; NOT fixable per-pack — needs a runtime/compiler pool-distinctness check OR
  gloss disambiguation in backfill_lexemes.py. Queued as a corpus-level item.
- en-fa b1_04/06/11 stale review.notes claim a "dedicated bare-word proper_noun translate" that
  doesn't exist in those files (only b1_03 has it) → those units' person names are unreachable by
  any generated exercise. MINOR (coverage gap, not a mis-grade).
- en-prs a1_36 overlay lesson06 translate_wrap_summary accepts a و-joined variant for an اما
  ("but") source — MINOR meaning-drift in one accepted answer.
- en-fa a2_12 نیما self-gloss in match.002 (author-disclosed tradeoff, pool drops to 5 without it);
  a2_14 lesson04.choose.002 MC at exactly the 3-option floor (zero slack — fragility note);
  b1_01 وقت دارم (a clause) tagged noun in a 6-card matching pool (granularity nit). All ship-acceptable.

## ⭐ Native review — BATCH 7 (2026-07-30): fa-en/prs-en/nl-en/en-nl a1_31-35 (recombination units)

**DONE (clean LIVE pack-only fixes committed):**
- u34 listen_dialogue_favorite distractors (fa-en/prs-en/nl-en, commit 0965a73c): swimming/yoga/soccer
  are all said by Daniel → replaced with tennis/basketball (CLAUDE.md "full stop" rule; overrode the
  nl-en author's rationalizing note for cross-direction consistency).
- en-nl u35 fill.003 Sander→Fenna wrong-fact + u34 order.003 'mijn' determiner (c64c0513).

**QUEUED — NATIVE-JUDGMENT (Dari, prs-en — need Ramin/native confirm, do NOT auto-fix):**
- **prs-en u35 `battery`="بطری" (CRITICAL): بطری = "bottle" in Dari/Farsi, not battery** (should be
  باتری or the colloquial بتری the backfill already uses — spelling is also inconsistent بطری/بتری).
  The overlay note claims بطری is "distinct from Iranian باتری" — reviewer (native-ish) says that's wrong.
- prs-en u31 `curly`="چوقی" (backfill) vs "مجعد" (overlay) — likely mistranslation; u32 `bird`="مرغک"
  (chick) vs "پرنده"; spelling drifts (پشک/پیشک, مو/موی سر, چشمان/چشم‌ها).
- ~~**`می‌ته` vs `می‌ده` pattern**~~ **RESOLVED (batch 9): NOT a defect** — legit Afghan colloquial
  د→ت shift, corpus-pinned convention. Withdrawn. (See BATCH 9 note.)

**QUEUED — DEPLOY-EFFECT (backfill):**
- prs-en/fa-en leaked-annotation glosses reachable via bare unit_verb/unit_noun pools: fa-en u33/34/35
  (answer/lot/etc.), prs-en u32/33/35 (takes="طول می‌کشه (سوم‌شخص مفرد take)", make="گرفتن (در make an
  appointment)", "(سوم‌شخص مفرد)" grammar notes). Fix = strip the parentheticals in the gloss dicts
  (collision-check) OR re-anchor the bare-POS templates to fa_en_a1_unitNN_words / prs_en_a1_unitNN_words
  (DEAD-verify per POS). Same wave as the earlier leaked-gloss strips — a dedicated `" ("` sweep of both
  dicts is worthwhile. en-nl u34 `boodschap`/`bericht` synonym false-negative (drop boodschap from
  lesson02 compound_note introduced_tokens, or add an NL_A1_VOLUME_TAG_EXCLUSIONS tuple).

**QUEUED — JUDGMENT/DESIGN:**
- nl-en u33 order.002/translate.001 "take the car/bike" contradicts the unit's own teaching (car→drive,
  bike→ride) — pack author documented "take is standard English", reviewer disagrees. Fix = narrow to
  {bus,train} (new tag) OR reframe vehicle-neutral "by {item}" (like sibling order.001). Ramin's call.
- fa-en u31/32 + nl-en u31 + prs-en u31 production-prompt completeness (missing curly/long/short/glasses
  etc. accepted_answers) — add the taught variants; native-EN judgment.
- fa-en u34/u35 duplicate templates (order.005 vs volume_order — differentiate the frame, like u31 did).
- corpus-wide: prompt.target_blocks English text often exceeds taught vocab (~40 instances) — policy call.

**FLIPPED reviewed (unambiguously clean):** en-nl a1_31/32/33; nl-en a1_32/34 (after the distractor fix).
(prs-en u33/34 + fa-en have residual reachable leaked-gloss / duplicate / mistranslation findings → not flipped.)

## ⭐ Native review — BATCH 8 (2026-07-30): fa-en/prs-en/nl-en/en-nl a1_36-40 (recombination units)

**THE HEADLINE — a systemic triad, code-verified across all 4 dirs (supersedes/expands the
"bare-word translation over UNTAGGED pools" note at the bottom of this file):**
The 2026-07-24/25 DEAD-fix waves widened many recognition/translation slots to **bare
part_of_speech (no semantic tag)** to escape DEAD templates. Commit `05af7ace` (2026-07-25)
then generated per-unit tags (`<dir>_a1_unitNN_words`, `a1_unitNN_<topic>`) but **did not
re-point those bare-POS slots**. So the slots still resolve, at Endless-Practice (course-wide)
scope, against the whole course pool. Three consequences, by direction:
- **X-en (fa-en + prs-en) — LIVE, learner-facing:** the shared gloss table
  `scripts/_en_target_lexeme_common.py` (~L844-992) stores disambiguating **leaked-annotation
  glosses** — `went→"رفت (زمان گذشتهٔ go)"`, `community→"اجتماعی (در community college)"`,
  `answer→"جواب دادن (در answer emails)"` (~27 noun/verb/adj entries, ~7% of verbs, ~3% of adj).
  `derive_answer(slot_gloss)` returns the string **verbatim** as the MC/listen correct option;
  a `translation` template rendering `slot_rendering: english_gloss` shows it **as the whole
  Farsi/Dari prompt** → the English answer is leaked inside the prompt. Confirmed in
  `service.py` (no sanitization) + `_material`/`generate_batch` (course-wide scope).
- **X-en — LIVE grading bug (class 6, fa-en):** the same bare noun pools contain true-synonym
  pairs with **identical** Farsi glosses (`shop`/`store`→مغازه, `photo`/`picture`→عکس,
  `trip`/`journey`→سفر, `mail`/`post`→پست). Whichever the RNG draws is the ONLY accepted
  answer (`grade()` translation path = exact string); the learner who writes the other
  equally-correct synonym is marked **wrong**. (prs-en has this too.)
- **nl-en / en-nl — NOT live:** Dutch glosses carry no English leak, and the contamination's
  only symptom is the **runtime-INERT** `feedback_frame` ("X is een woord uit deze les" when X
  is an off-unit review word) + off-theme distractors. Grading stays self-consistent.

**⛔ WHY THIS NEEDS YOUR DECISION (not auto-fixable):** fa-en's reviewer verified that
**pack-side re-anchoring the X-en bare-POS slots back to a semantic tag RE-CREATES the DEAD
templates** the widening was meant to solve (the unit-scoped POS pool drops below floor). And
delatinizing the Persian glosses is native-Dari judgment (e.g. `خرید (زمان گذشتهٔ buy)` → the
"buy" must go but the past-tense signal must stay, else buy/bought collide). So the real fix is
**data-layer**, and it's a design call:
  (a) **sanitize `english_gloss` at point-of-use** in `service.py` (strip the ` (…)` parenthetical
      before it's used as an MC option / translate prompt) — one place, fixes all X-en units, but
      re-introduces the buy/bought ambiguity the parenthetical was disambiguating;
  (b) **maintain a shared bare-POS eligibility exclusion set** (skip leaky-gloss lexemes for
      untagged slots) — keeps disambiguation for tagged uses, needs list upkeep;
  (c) **add `interchangeable`-style multi-answer support** to `translation`'s `slot_text`
      derivation so synonym pairs (class 6) both grade correct — orthogonal, also needed;
  (d) delatinize the glosses in `_en_target_lexeme_common.py` with native-Dari review (deploy-effect).
Recommend (b)+(c) together, or (a) if you accept the ambiguity tradeoff. **BLOCKED on your call +
a dev DB to re-backfill.** This is the dominant remaining defect class in the X-en corpus; further
review batches will keep re-finding it, so this decision unblocks the most value.
  **Full inventory generated: `docs/LEAKED_GLOSS_INVENTORY.md`** (376 leaked total: fa-en 158, prs-en 218).
  Classified conservatively (cross-POS collision): **class A disambiguating** (fa 68 / prs 111 — tense/
  3rd-person/contraction/negation, must delatinize keeping the Persian marker); **class B collision**
  (fa 52 / prs 90 — bare strip re-exposes a shared gloss like well→خوب=good/fine/okay); **class C
  collision-free standalone** (fa 38 / prs 17 — candidate strips, but native spot-check the base is a
  complete answer). NOT auto-stripped: even class C is Persian text under the "no auto-fix Dari" rule;
  the prior wave's 111 safe strips already took the easy ones, so this residue is the genuinely-hard set.

**DONE (clean LIVE pack-only fixes committed — nl-en, English target, no leak, authors' own pattern):**
- nl-en u39 choose.001/listen.002/translate.004/choose.002 re-anchored POS-only `neighborhood_adj`
  (651-token course-wide pull) → `unit39_match_word` (a1_unit39_neighborhood, 15 unit-scoped); +
  `unit39_noun` preset given the same tag (10 nouns). Authors had already done this for match.003 and
  explicitly left the 4 siblings "not dispatched".
- nl-en u38 `unit38_noun` (506 course-wide) → +semantic a1_unit38_household (9 nouns);
  nl-en u37 lesson02.translate.001 bare verb (315 course-wide) → +semantic a1_unit37_celebrations (19).

**QUEUED — en-nl (deploy-effect / hygiene):**
- **`schrijf` mis-gloss (LIVE):** `NL_GLOSSES["schrijf"]="prescribe; write (with ik)"` (inherited from
  A2 doctor unit) surfaces as the MC correct-option in u39 lesson02.choose.001/listen.004 (slot_gloss).
  "write (with ik)" is right for A1 post-office AND for the A2 "schrijf een recept" sense → a single-sense
  global fix is defensible; or a context override (precedent: Nodig/Regel/Duur folds). Native-Dutch call.
- **5 new `_pure` tags** (verjaardag/huishouden/buurt/post/koken) for en-nl u36-40 — the `_vocab`/`_cat`
  tags are contaminated by course-wide review tokens → **inert** false feedback only; LOW priority
  (allow-list new tokens, repoint choose/translate/listen/match). No `_pure` exists for these 5 topics yet.

**QUEUED — nl-en (hygiene, inert):**
- u36/u37 choose.001/choose.002/listen.002 on cross-unit `education_noun`/`celebration_noun` → inert
  false-provenance feedback + off-theme distractors. Blunt re-anchor risks injecting plurals
  (classes/nights) into the "My {item} is difficult" generative frames → needs a split preset
  (recognition→unit tag, generative→curated). Deferred (inert).
- u36 order.001/order.002/translate.001 generative frames apply the full noun pool to
  "My {item} is difficult"/"We like our {item}" → grammatical-but-odd ("My test is difficult"); LOW.
- u39 overlay reading-passage renders gender-neutral "neighbor across the street" as female "buurvrouw"
  (invented detail, no graded impact).

**QUEUED — prs-en (native-Dari, do NOT auto-fix — extends the batch-7 queue):**
- ~~`می‌ته` recurs in u36/u39 overlays~~ **RESOLVED (batch 9): NOT a defect** — the native-Dari reviewer
  confirmed it's the legit Afghan colloquial د→ت shift (the prior reviewers who cited it as positive
  Afghan-register evidence were right). Withdrawn.
- `community`="اجتماعی" (=social, adj) for a noun is a probable mistranslation independent of the leak;
  and stripping its parenthetical collides with `outgoing`→"اجتماعی". Native call.
- prs-en u40 match.003.volume_match.008 ships a stray authoring note in `frame.text_blocks`
  ("Second review matching set for this unit.") — runtime-inert (build_prompt ignores text_blocks); cosmetic.

**Low-sev forward-refs (all dirs, class 4 — reword or accept):** fa-en u36 write_subject_word uses "study"
(taught lesson02), u36 choose uses "classes" (lesson04), u37 gift exercises use "someone" (lesson02),
u39 write_neighbor_word uses "lives" (lesson04). Compiler doesn't check MC/writing_prompt prompts.

**FLOOR (pre-disclosed, informational):** match.003 below 6-pair floor — fa-en u37(4)/u38(3)/u40(4),
nl-en u37(4)/u38(3)/u40(5), prs-en u37/u38/u40(4), en-nl various. All authored-around, not new.

**FLIPPED reviewed (clean this batch):** fa-en a1_40 (no bare-POS slot anywhere — structurally immune);
nl-en a1_38/39/40 (39 after the re-anchor; 38/40 clean modulo disclosed floor). NOT flipped: fa-en
u36-39 + prs-en u36-40 (live leaked-gloss/synonym exposure, blocked on the data-layer decision);
en-nl u36-40 (schrijf + _pure hygiene); nl-en u36/u37 (inert feedback, deferred).

## ⭐ Native review — BATCH 9 (2026-07-30): fa-en/prs-en/nl-en/en-nl a1_41-45 (cooking/personality/colors/seasons/emergencies)

**DONE (clean LIVE pack-only fixes committed — nl-en re-anchors, same safe pattern as batch 8):**
- nl-en u42-45: re-anchored POS-only / fully-unrestricted-POS slots (no semantic tag → course-wide
  pull at Endless-Practice scope) to the generated unit tags. All DEAD-verified + 0 dup-glosses:
  u42 u42_adj adjective→[noun,adjective]+a1_unit42_personality (21; verb excluded — relax/relaxed
  →ontspannen collision); u43 inline-10-POS→a1_unit43_colors (25), u43_adj→+a1_unit43_colors (8);
  u44 10-POS→a1_unit44_seasons (15), 4-POS lesson03/04→a1_unit44_seasons (15); u45 10-POS→
  a1_unit45_emergencies (32), 4-POS lesson03→a1_unit45_emergencies_lesson03 (11, tag added). u41 clean.
- FLIPPED reviewed: nl-en a1_41-45; en-nl a1_43/45 (both clean per reviewer).

**DONE (LIVE cross-direction fix — speak_response completeness, class 6):**
- u42 lesson03.exercise04 (respond_own_personality) + u43 lesson03.exercise04 (respond_own_favorite_color)
  speak_response accepted_answers OMITTED taught answers (u42: standalone "I'm friendly/funny/talkative";
  u43: black/white) → learner saying a taught answer graded WRONG (grading.py: speak_response multi-answer
  `accepted` is a closed set, confirmed L643). Added the missing variants to the SHARED
  `realizations/en/a1_unit42_personality.yaml`/`a1_unit43_colors.yaml` + all 3 dirs' overlays (fa-en/prs-en/
  nl-en) — 8 files, matching the sibling writing_prompt's already-complete lists. validate 0/0 all 6
  realization×overlay pairs. This also retroactively validates the nl-en u42/u43 flips.

**QUEUED — en-nl (inert / cosmetic, LOW):**
- u41/u42 blanket-tag contamination (persoonlijkheid_vocab/kleuren_vocab pull course-wide review tokens
  → runtime-INERT false feedback + off-theme distractors; up to 86% false-feedback rate on u41
  lesson03.choose.001). Fix = new `_pure` tags (unit-scoped allow-list: u41 personality =7, u42 colors =8,
  both clear floors; but u41 lesson03.choose.001 at [noun,adj,pronoun,verb] has only 2 unit-scoped →
  narrow POS to [noun,adjective] instead of _pure, per the Vrijdag-DEAD-trap). Deploy-effect. No live bug.
- u44 lesson03.order.002 "Ik bel de {item}" can draw capitalized `Politie` → "Ik bel de Politie." stray
  mid-sentence capital (cosmetic; render_frame self-consistent). Exclude the cap form or fold to lowercase.

**QUEUED — fa-en hygiene (LOW):**
- bare-POS leaked-gloss exposure in u41/u43/u44/u45 lesson01/02/03 recognition+translate slots (already
  in docs/LEAKED_GLOSS_INVENTORY.md; same data-layer decision as batch 8 — NOT re-fixed per-pack).
- u41 stale review.status: `reviewed` but wave-2 (2026-07-25) added 3 templates after that review with no
  re-review — either re-review those 3 or flip to unreviewed. (This batch's reviewer did read them: only
  the bare-POS hygiene item, no live bug.)
- minor near-duplicate templates (same `{item}` frame + overlapping bare-POS pool) u43/u44/u45; calm/relaxed
  →آرام borderline near-synonym in u42 id_wide adjective pool (self-flagged, not identical strings).

**prs-en batch-9 (DONE + one big resolution):**
- ✅ **`می‌ته` is NOT a defect — RESOLVED.** The native-Dari batch-9 reviewer confirms `می‌ته`/`می‌گه`/
  `می‌شه` is the legit, corpus-pinned Afghan colloquial د→ت shift (بده→بته etc.), documented in
  overlays/prs-en/a2_unit36.yaml's own note — not Pashto contamination. This settles the batch-7/8 queued
  question; the `می‌ته→می‌ده` global-replace item is WITHDRAWN. (prs-en native mistranslation items like
  battery=بطری from batch 7 still stand — separate from می‌ته.)
- ✅ **DONE: prs-en u42 match.003 + volume_match.007 widened 4→5 slots** (NOT 6 — the reviewer's "widen to
  6" hit the DEAD-trap: personality_adj's unit42-scoped pool is only **5**, not 6 — one of friendly/funny/
  hardworking/shy/calm/talkative isn't reachable at unit42 checkpoint scope. 6 slots DEADed both templates;
  backed off to 5, the true pool ceiling. Still below the 6-pair floor but +1 pair and non-DEAD). unit-scope
  0 DEAD, TOTAL back to baseline. Lesson: always verify unit-scoped pool via the tool, not the tag's total.
- QUEUED LOW: prs-en u41 lesson01 exercises use "cut/cutting" (taught unit41 lesson04) — within-unit
  forward ref; reword or accept (native-EN). u43/44/45 clean, no bare-POS leaked-gloss exposure in prs-en
  u41-45 (unlike fa-en). Process/hygiene: fictional `pool_check.py` cited in u43/44/45 notes (script doesn't
  exist; claims independently re-verified true); 5 redundant tag-append blocks in `_en_target_lexeme_common.py`
  (harmless — service.py sets() them; cleanup-only).

**FLIP (batch 9, after fixes):** prs-en u43/44/45 clean → flip; prs-en u41 (LOW forward-ref residual) +
u42 (after floor fix) → flip. All 6 English-target speak_response fixes clear u42/u43 for those dirs too.

## ⭐ Native review — BATCH 10 (2026-07-30): a1_46-50 (lost_items/appointments/library/waste/accommodation)

**DONE (clean LIVE pack-only fixes committed — nl-en re-anchors):**
- nl-en u46/u47: 6 templates each, POS-only/unrestricted slots → +semantic a1_unit46_lost_items /
  a1_unit47_appointments (keep POS; pools 31/26 and 20/16, 0 dup-glosses, DEAD-verified).
- nl-en u48: 4 MC templates → a1_unit48_library (keep POS; MC protected by distractor casefold-dedup even
  though borrow/borrowing→"lenen" dup exists); **the 2 TRANSLATION templates POS-NARROWED** to keep the
  synonym pair out of a free-text pool: translate.003 → [noun,adjective,adverb] (11, excl. borrow),
  volume_translate.001 → [verb] (16, excl. borrowing); lesson04.translate.006 → a1_unit48_library_lesson04
  (20, collision-free by construction). This mirrors the pack's own already-fixed match.002 discipline.

**QUEUED — en-nl u49 LIVE (MC synonym-collision — deploy-effect _pure):**
- u49 lesson05.choose.001 (`confirmation_reading` pool) has bevestigd="confirmed"/Bevestiging="Confirmation"
  /bevestiging="the confirmation" — a capitalized-variant reworded-gloss trio that `_distractor_values`
  casefold-dedup does NOT catch (service.py:386-405) → two defensible "confirmation" MC options, correct
  learner picking the confusable one marked wrong. Same in lesson06.choose.001/lesson02/lesson03
  (`accommodatie_vocab`/`accommodation_wrapup_dialogue`: leuk/mooi/mooie trio). u46 predates the
  NL_CITATION_FORMS folding (scoped 34-42/49-72) so its capitalized "Bevestiging" never folded onto u49's.
  Fix = _pure unit-scoped tag (u49 nouns kamer/bevestiging/uitchecken ≥3) or POS-narrow. Deploy-effect
  (backfill). NOT auto-fixed. → u49 held from flip.

**QUEUED — prs-en (native-Dari + gated):**
- **prs-en u49 `jar`="بوتل شیشه‌ای" (بوتل = bottle, narrow-necked)** — a wide-mouth jar is شیشه in Dari;
  same lexeme-substitution family as batch-7 battery/بطری but milder (both glass containers; `jar` is a
  taught token but never the tested fact, so no mis-grade — just wrong vocab). Native-confirm → شیشه.
  In BOTH the u49 dialogue gloss + reading-passage gloss (shared realization? — check: it's the English
  realization's introduced-token gloss, prs-en overlay side). Otherwise prs-en u46-50 clean EXCEPT they
  carry bare-POS leaked-gloss slots (other→"دیگه (در on the other hand)", back→"باز (در come back)") →
  gated on the data-layer decision like fa-en. → prs-en u46-50 held from flip.

**QUEUED — hygiene (LOW, all dirs):**
- en-nl u48 `GFT` classified proper_noun in backfill but no template slot allows proper_noun → the unit's
  central word is unreachable as a candidate. Reclassify GFT→noun in backfill_lexemes_en_nl.py (deploy-effect).
- nl-en overlays u47/48/49/50 carry `review.status: reviewed` while their notes say "needs fresh-context
  review" (u46 was corrected 07-23; siblings weren't) — overlay-side metadata self-contradiction; this batch
  IS that review, so safe to correct the overlay status when convenient (separate from the practice-pack flip).
- Both prs-en + en-nl reviewers independently confirm the review-notes cite a FICTIONAL `pool_check.py`
  (doesn't exist); claims were re-verified true via iter_specs. Cosmetic note-accuracy only.

**DONE (fa-en — a key reframe of the "fa-en is blocked" story):**
- fa-en u46/u47 re-anchored their bare-POS translate/choose slots to fa_en_a1_unit46_words / _unit47_words.
  This FIXES the fa-en synonym false-negatives (told/said [said=u37], appointment/meeting [meeting=u14],
  seems/looks [looks=u43] — all CROSS-unit, so unit-scoping excludes the collider) AND, because both unit
  pools are **leaked-gloss-free + dup-free** (verified), it ELIMINATES the leaked-gloss block for those two
  packs. **Insight: the fa-en leaked-gloss block is PER-UNIT, not monolithic — any fa-en pack whose own unit
  pool has no leaked gloss can be re-anchored to full clean.** u46 → flipped. u47 → HELD (see `changes`).
- fa-en u50 checkout distractor: "ten o'clock" violated the CLAUDE.md full-stop rule (Receptionist says
  "seven to ten") → swapped to "eight o'clock" (never spoken) in both checkout exercises. fa-en-only —
  prs-en already used "eight o'clock", nl-en used just nine/noon.

**QUEUED — fa-en gloss/sense (deploy-effect, native-Farsi):**
- u47 `changes` classified noun→"تغییرات" but the unit teaches the VERB ("if something changes") → wrong
  sense; needs a unit-scoped verb override ("تغییر می‌کند"). Holds u47's flip.
- u48 `used`→"استفاده کرد" but taught only in "used to" (habitual past) → add UNIT_SENSE_OVERRIDE
  ("عادت داشت"), mirroring the existing b1_unit13 pattern. u48 also has `other`→"دیگر (در on the other
  hand)" leaked gloss + borrow/borrowing→"قرض گرفتن" dup IN-pool → u48 can't be cleanly re-anchored like
  u46/47 (the [noun,adj,adv] translate-narrow that dodges borrow re-exposes `other`); needs the gloss fixes
  first. u48 HELD. (The pack's own note wrongly claims borrow/borrowing is "accepted per recipe §6.3" — true
  for matching_pairs, FALSE for its bare translation templates.)

**QUEUED — class-3 completeness (CONTESTED → your judgment):** nl-en flagged verbatim-taught sentences
missing from accepted_answers (u47 "Are you available on Friday?", u49 green-bin/next-time, u50 "Your/Our
room has two beds" vs accepted "The room..."), but the fa-en + prs-en reviewers independently checked the
same exercises and found them complete. These are open-ended speak_response/writing_prompt items where
"which taught phrasings should count" is a policy call (e.g. is the Receptionist's "Your room..." a valid
learner check-in response?). Deferred rather than adjudicated. All would be shared-realization + 3-overlay
fixes if you decide to widen them.

**FLIP (batch 10):** en-nl u46/47/48/50 + nl-en u46/48 + fa-en u46 → flipped (7). HELD: nl-en u47 (Friday
class-3 contested), u49/u50 (class-3); fa-en u47 (`changes`), u48 (`used`/`other`/borrow), u49/u50 (leaked
`collection`/`under` + gated); en-nl u49 (_pure MC-collision); prs-en u46-50 (bare-POS gated + u49 jar).

## ⭐ Native review — BATCH 11 (2026-07-30): a1_51-55 (pharmacy/personal_care/bike_rental/laundry/swim/etc.)

Directions DIVERGE on the same units (different lane authoring): nl-en + fa-en u51-55 were authored
already-unit-anchored (recipe §8.1), prs-en still has bare-POS slots.

**DONE (LIVE fixes committed):**
- nl-en u51-55: all CLEAN by construction → flipped (5).
- prs-en u51/u52/u55: re-anchored their bare 10-POS choose/listen/translate slots to prs_en_a1_unitNN_words
  (pools 14/10/23, all leaked-gloss-free + dup-free) → flipped.
- **prs-en u51 numeral fix (HIGH):** "nine dollars" was glossed «این نو دالر استه» (نو = NEW, not نه = nine)
  in 7 sites incl. a graded translate PROMPT + the reading passage. Fixed نو→نه to match the corpus's own
  a1_unit07 («نه دالر»); نو means "new" 50+ places, so this was an unambiguous authoring typo, corpus-backed,
  not a word-choice judgment. Flagged for your awareness but corrected.
- en-nl u51/u52/u53/u55: CLEAN → flipped.

**QUEUED — fa-en u51-55 (deploy-effect / native-Farsi — ALL 5 gated, already-anchored so NO re-anchor helps):**
- Real MISTRANSLATIONS (not just leaks): u51 `hours`→"ساعت‌های کاری" (business-hours) but every use is dosage
  "every four hours" → plain time-unit; u52 `visit` tagged noun/"مراجعه" (formal) but used as casual verb
  "coming to visit" → verb "سر زدن به" (a2_unit33 already does this right); u53 `deposit`→"واریز" (bank
  transfer, shared w/ a2_unit27) but it's a refundable security deposit — the overlay's OWN teaching card
  uses "ودیعه" (corpus self-contradicts) → FA_EN_EXTRA_LEXEMES override "ودیعه"; u53 `costs`→"قیمتش چقدر است"
  (a QUESTION!) for a declarative "it costs $10" → declarative gloss. All backfill_lexemes_fa_en.py overrides.
- Leaked glosses in-pool (Class C strips, already in LEAKED_GLOSS_INVENTORY): u51 runny, u54 pick/broke,
  u55 diving/board. Deploy-effect.

**QUEUED — prs-en (native-Dari / gated):**
- u53/u54 own-pool LEAKED glosses (we'd→"...(مخفف we would)", enjoying→"...(شکل ing فعل enjoy)", pick→
  "...(در pick up)") → native delatinize (deploy-effect). u53/u54 held from flip.
- u52 + u54 `coffee`→"چای" (tea): could be intentional Afghan localization (tea = the social norm) OR a
  mistranslation (قهوة is the corpus's coffee term). JUDGMENT/localization confirm. (u52 flipped anyway — the
  re-anchor makes it otherwise clean and چای-for-coffee is defensible; u54 held for the pick leak regardless.)

**QUEUED — en-nl u54 (backend-data, deploy-effect):**
- `regel` (A1 "de regel"=the rule) shares NL_GLOSSES with A2-unit77 "arrange (with ik, part of regelen)" →
  wrong gloss. Backfill already excludes `regel` from zwembad_vocab/_noun (airtight for MC/listen/translate),
  BUT `_material()`/`_speaking_targets()` (service.py ~:775) select speak_response targets by
  provenance_lesson_id with NO agreement_tags filter → a learner past u54 lesson05 can get a speak_response
  cue "arrange (with ik...)" for answer "regel". Fix: correct the A1 `regel` gloss in backfill OR make
  _material/_speaking_targets respect the tag-exclusion. u54 held.

**FLIP (batch 11):** nl-en u51-55 (5) + prs-en u51/52/55 (3) + en-nl u51/52/53/55 (4) = 12. HELD: prs-en
u53/u54 (own-pool leaks), fa-en u51-55 (in-pool gloss defects, deploy-effect), en-nl u54 (regel backend).

## ⭐ Native review — BATCH 12 (2026-07-30): a1_56-60 (restaurant/cinema/museum/banking/invitations/etc.)

**DONE (LIVE fixes committed):**
- fa-en u57/u58/u59/u60 CLEAN (freshly-authored glosses, no shared-dict reuse) → flipped.
- prs-en u58/u59: re-anchored bare choose/listen/translate 10-POS slots to prs_en_a1_unit58/59_words
  (clean pools) → flipped. prs-en u56 re-anchored (clean pool) but HELD (see نزده).

**QUEUED — en-nl u56-60 (ONE root cause, deploy-effect backfill — LIVE bug, but no live flip until re-backfill):**
- **`was` homograph, LIVE class-1 wrong answer.** `NL_GLOSSES["was"]="do the dishes (with ik)"` (unit10
  "Ik was de vaat") is the ONLY gloss for `was`, but every outing unit's wrap-up uses the copula "Was het X
  goed?". The backfill's own docstring CLAIMS `was` is excluded from these `_vocab` tags but
  `NL_A1_VOLUME_TAG_EXCLUSIONS` (only has koken/bak, post/schrijven, zwembad/regel) — the `was` entries were
  never added. So a generated MC/translate on `was` shows "do the dishes" as the correct meaning of a copula.
  FIX (mechanical, matches documented intent): add `("bioscoop","was"),("museum","was"),("concert","was"),
  ("park","was"),("sportschool","was")` to NL_A1_VOLUME_TAG_EXCLUSIONS — AND sweep units 61-72 (strand/
  dierentuin/rondvaart/voetbalwedstrijd/pretpark/theater/markt/bakker/ijssalon/bloemist/boekwinkel/
  dierenwinkel all carry `was` in their `_vocab` tag too, same "Was het X" pattern — verify each then exclude).
  Also restaurant_vocab/accommodatie_vocab/wasserette_vocab carry it. Do NOT exclude from unit10's
  daily_activity (there `was`=dishes is correct).
  **★ BATCH-15 confirmed the FULL scope: the single `was` Lexeme carries ~45 outing-unit `_vocab` tags
  course-wide (verified via iter_specs).** The clean fix is to exclude `was` from EVERY en-nl a1 `_vocab`
  tag except `daily_activity` (unit10). Per-unit LIVE vs inert depends only on whether that pack's
  choose/listen/translate slots include verb POS: LIVE (verb POS present) = en-nl u56/57/58/59, u61/62/63,
  u68, u70/71/72; inert (POS-filtered) = u60, u64/65, u66/67, u69 (those flipped). Same broad tags also
  admit `is`/`hebt` etc. but those are correct-sense (class-2 LOW, not wrong-answer). One backfill edit +
  re-backfill unblocks all ~11 held en-nl outing packs at once.

**QUEUED — prs-en (native-Dari / gloss / re-anchor):**
- u57 `journey`="سفر (بخشی از نام فلم Star Journey)" leaked-gloss IN-pool (unit57's own tag) — the Latin film
  title renders in the translate PROMPT (slot_rendering english_gloss) leaking the answer. Rewrite gloss to
  plain سفر or exclude the token (it's only half a fixed film title). Native/gloss fix → u57 held.
- u56 `نزده دالر` for "nineteen dollars" (4 sites) — everywhere else the corpus spells 19 as `نوزده`; could
  be a dropped-letter typo OR a legit colloquial elision (cf. چارده/14 precedent). NATIVE-CONFIRM → u56 held.
- u60 CLEAN but needs a FULL re-anchor (choose/listen/translate 10-POS + matching_pairs multi-slot +
  word_order, and prs_en_a1_unit60_words is not yet declared in its tag_schema) — mechanical follow-up,
  deferred (the matching_pairs inner slots don't match the uniform re-anchor pattern).

**QUEUED — fa-en u56 (deploy-effect UNIT_SENSE_OVERRIDES):**
- `bill`→"قبض" (utility-bill, shared-dict reuse) but unit teaches restaurant-check "صورت‌حساب" [HIGH];
  `could`→past-ability "می‌تونستم" but taught as polite-request chunk [MED]. Add
  UNIT_SENSE_OVERRIDES[("a1_unit56_restaurant","bill")]="صورت‌حساب" / [...,"could"]="می‌شه". u56 held.

**DONE (nl-en):**
- nl-en u56/u57/u59 CLEAN → flipped. u60: **LIVE checkpoint bug fixed** — translate.002's render_frame answer
  "She {item} an invitation" lacked the period its feedback + Dutch prompt carry; router sets
  orthography_strict=True for checkpoints (zero typo tolerance, grade_answer returns incorrect before the
  Damerau-Levenshtein branch), so a learner typing the natural period-ending form was graded WRONG on
  checkpoints. Added the period to match. → flipped. (Endless Practice forgave it as "almost"; checkpoint-only blast radius.)

**QUEUED — nl-en u58 (deploy-effect backfill):**
- city→"de stad" / town→"de stad; het stadje" in a1_unit58_museum translate pool — "de stad" is the whole of
  city's gloss and a prefix of town's; bare-word translate can't disambiguate (Dutch conflates city/town→stad)
  → synonym false-negative. Not a re-anchor (already anchored); exclude `city` from the union for translate/
  choose/listen, or disambiguate the gloss in backfill_lexemes_nl_en.py. u58 held.

**VERIFIED (not a bug):** nl-en u34 matching_pairs `left` is the ENGLISH definition ("a sport played with a
round ball…"), `right`=English term — correct pattern, NOT Dutch-translated (u58's notes' second-hand claim
was wrong for u34; my batch-7 flip stands). TODO: separately verify nl-en a2_unit29's matching_pairs left.

**FLIP (batch 12):** fa-en u57/58/59/60 + prs-en u58/59 + nl-en u56/57/59/60 = 10. HELD: fa-en u56 (bill/
could), prs-en u56 (نزده)/u57 (journey)/u60 (full re-anchor), nl-en u58 (city/town), en-nl u56-60 (was).

## ⭐ Native review — BATCH 13 (2026-07-30): a1_61-65 (apologies/phone/help/compliments/returns; en-nl outings)

**DONE (LIVE fixes committed):**
- **u61 writing_prompt completeness (cross-direction):** `write_own_apology_message` ("give the reason")
  accepted only the "The bus is late." reason; the unit equally teaches "I made a mistake." (lesson01/02) —
  a learner giving that taught reason was marked wrong. Added 4 "I made a mistake" variants to the SHARED
  realizations/en/a1_unit61 + fa-en/prs-en/nl-en overlays. validate 0/0 ×3. → fa-en u61 + nl-en u61 flipped.
- Clean flips: nl-en u62/63/65, en-nl u64/65 (was POS-filtered inert there), fa-en u62/63.

**QUEUED — fa-en (native/content, not re-anchorable — both shape-B already-anchored):**
- u65 **HIGH**: word_order frame `"Leila {item} it"` over {offered, exchanged} — **Leila isn't a character in
  unit65** (it's Daniel + the Clerk), and the two verbs have different real subjects (clerk offered / Daniel
  exchanged). Fix = split into two correct-subject frames or unnamed rewrite. u65 held.
- u64 `being`→"بودن (در Thanks for being kind)" — the whole English target sentence embedded in the gloss,
  rendered into the word_order HINT (render_frame default english_gloss) → answer spelled out. Rewrite gloss
  to plain "بودن". u64 held. (Info: EN_PHRASE_LEXEME_UNIT_STEMS skips a1_unit61_apologies_excuses →
  unit61 lesson02 got no phrase lexemes; non-blocking coverage gap. lesson03 dialogue lexemes exist in
  u62-65 but no pack template references them — non-blocking authoring-completeness note.)

**QUEUED — en-nl u61/62/63 (live `was`, blocked on the queued backfill exclusion):**
- The `was`→"do the dishes" homograph is a LIVE candidate in u61/62/63 (their slots include verb POS); u64/65
  POS-filter it out (inert, flipped). Same root fix as BATCH-12 (add the outing-unit `was` exclusions to
  NL_A1_VOLUME_TAG_EXCLUSIONS). en-nl u61/62/63 held until that + re-backfill.

**QUEUED — prs-en (native / gloss / re-anchor):**
- u65 **register**: learner-facing teach.note strings (lesson03 dialogue_line1/line7) use formal/Iranian
  بدهد/می‌کند + a bare English "refund" mid-Dari — inconsistent with the item's own colloquial gloss;
  self-disclosed unfixed. Native-Dari. u65 held.
- u61 `waiting`→"...(شکل ing فعل wait)" + u64 `being`→"...(شکل ing فعل be)" leaked morphological glosses
  in-pool (Class-A disambiguating, corpus-wide 218-instance convention) → native delatinize. u61/u64 held.
- u62/u63 CLEAN pools but need a re-anchor of their narrow-POS ([adj,noun]/[adj,noun,verb]) + phrase +
  word_order slots (tag not yet declared in tag_schema; the [adj,noun] pool is exactly at the 3-floor) —
  mechanical follow-up, deferred with u60 (fiddlier than the uniform 10-POS pattern).

**QUEUED — nl-en u64 (backfill, deploy-effect):** `being`→"het zijn (in being kind)" leaked gloss renders in
the translate prompt + word_order hint → strip to "het zijn" in backfill_lexemes_nl_en.py:1832. u64 held.
Also nl-en u58 city/town→"de stad" synonym false-neg still queued (BATCH-10).

**FLIP (batch 13):** fa-en u61/62/63 + nl-en u61/62/63/65 + en-nl u64/65 = 9. HELD: fa-en u64/65, prs-en
u61/62/63/64/65, nl-en u64, en-nl u61/62/63.

## ⭐ Native review — BATCH 14 (2026-07-30): a1_66-68 — LAST a1 X-en band (pharmacy_symptoms/family_news/borrowing_lending; en-nl theater/markt/bakker)

**DONE (flipped):** nl-en u66/67/68 (all clean), fa-en u66/67/68 (u68 lesson02.fill.003 frame fixed
"Thank you for the {item}." → "Thank you for {item} it." = natural gerund), prs-en u66, en-nl u66/67.
This COMPLETES the a1 review sweep for nl-en + fa-en (all 68 units flipped-or-held).

**QUEUED — prs-en (deploy-effect backfill gloss, native-Dari):**
- u67 `must`→"باید (در must be: حتماً)" (backfill_lexemes_prs_en.py:1265) + u68 `lending`→"امانت دادن (شکل
  ing فعل lend)" (:1268) — Latin embedded in the Dari gloss, LIVE in u67 bare-verb slots + u68's three
  matching_pairs (confirmed shipped). Native delatinize + re-backfill. u67/u68 held.
- u67 register: 2 un-repaired formal دارد ("یک طفل نوزاد دارد.") in teach.baby example_gloss + teach.sister_baby
  gloss (NOT dialogue cards, so not covered by the disclosed dialogue-exclusion) → داره. Compile-time overlay
  edit but Dari → queued with the must fix (u67 held on must regardless).

**QUEUED — en-nl u68 (live was):** bakker_vocab slots include verb POS (widened to admit the unit's own
`gebakken`), so the `was`→"do the dishes" homograph is a LIVE candidate → held on the queued was-exclusion.
(en-nl u66/u67 POS-filter verb out → inert → flipped.)

**QUEUED — fa-en u68 (backfill coverage, non-blocking, self-flagged):** lesson03 has zero lexemes →
checkpoint <12 generatable items despite the pack clearing the template-count bar. Backfill-lane
(EN_PHRASE_LEXEME_UNIT_STEMS / lesson03 lexeme registration). Did NOT block u68's flip.

**FLIP (batch 14):** nl-en u66/67/68 + fa-en u66/67/68 + prs-en u66 + en-nl u66/67 = 8. HELD: prs-en
u67/u68 (must/lending gloss + دارد), en-nl u68 (live was).

**★ a1 STATUS after batch 14:** nl-en a1 fully swept; fa-en a1 fully swept (both dirs' held packs are all
on deploy-effect backfill/native gloss fixes — a single re-backfill wave + native-Dari/Farsi pass clears
most). prs-en a1 nearly done (held: leaked-gloss units). en-nl a1 through u68 (u69-72 remain). NEXT:
en-nl a1_69-72 + open the a2 band (fa-en/prs-en/nl-en a2_01-05).

## ⭐ Native review — BATCH 15 (2026-07-30): a2_25-29 opens (bureaucracy/opinions/banking/doctor/maintenance) + en-nl a1_69-72

**DONE (LIVE fixes committed):**
- **u25 shared-realization speaker bug (HIGH, cross-direction):** the DMV dialogue transcript
  (realizations/en/a2_unit25_bureaucracy.yaml) had two consecutive `Clerk:` turns — "Clerk: I see.
  Could you tell me what I need to bring? Clerk: You'll need..." — the question is Daniel's (the
  exercises' own tested_text at lesson04 already treat it as Daniel's line). Re-attributed to Daniel.
  Audio is pending_generation, so the corrected text will TTS correctly. validate 0/0 ×3 dirs.
- **nl-en a2 u25 checkpoint punctuation** (u60-class): weekday_translate.007 render_frame "come this
  {item}" lacked the "?" its feedback+Dutch prompt carry → checkpoint marked "...Friday?" wrong. Added "?".
- **nl-en a2 u26 re-anchor:** opinion_adj preset + content_translate_bare.004 inline slot were POS-only
  (course-wide pull at Endless-Practice) → +semantic a2_unit26_opinions (5) / a2_unit26_opinions_lesson04
  (7), declared in tag_schema. 0 DEAD.
- FLIPPED: fa-en a2 u25/26/28/29; nl-en a2 u25/26/27/28/29; prs-en a2 u25/26/28.

**QUEUED — fa-en + prs-en a2_27 banking (deploy-effect backfill + native-Dari, BOTH dirs):**
- **`fee`="معاش" is WRONG — معاش means SALARY/wage** (confirmed by a2_unit39 salary=معاش + fa-en's own
  note "حقوق not معاش"). A bank fee is a charge FROM the customer → should be **کارمزد** (standard Persian/
  Dari, already used correctly in backfill_lexemes_fa_en.py:893). HIGH — reaches ~12 overlay teach/exercise
  strings + the backfill gloss dict in both fa-en (:865?) and prs-en. Native-confirm کارمزد, fix overlay
  text + gloss dict. u27 held (both dirs).
- **`direct`="مستقیم (در direct deposit)"** leaked English in the gloss, LIVE in banking_adjective/banking_word
  (fa-en backfill + prs-en backfill:866). Strip the parenthetical. (fa-en also: business=کاری/checking=جاری
  context-bound gloss defensibility, MEDIUM-LOW.)

**QUEUED — prs-en a2_29 (completeness, prs-en-overlay-only):** lesson04 reply_as_daniel/speak_maintenance_
dialogue accepted_answers list only the period-split join; lesson02.exercise06 (same clauses) + sibling
unit28 + nl-en/fa-en overlays all carry the comma+and / and-only variants → a taught-correct join is graded
wrong. Add the 2 variants to both u29 lesson04 exercises (mirror lesson02.exercise06). prs-en u29 held.

**QUEUED — LOW/cosmetic:** fa-en a2_25 two duplicate word_order templates (`.volume_order` over 1-candidate
weekday pool → identical exercises; drop one of each pair — pack-only, verify tier floor) + English
feedback_frame on those (inert); fa-en a2_25/26 matching instruction "وصل کنید" (formal outlier among
colloquial کنین — one-word fix each); fa-en a2_29 teach.confirmation_text gloss "درخواست تعمیر" vs the
unit's "گزارش"(report) — non-graded nit; nl-en a2_25 overlay schema 1.0-vs-1.1 example_gloss gap (7 WARN,
becomes error once retrofitted). All flipped-with-residual or held per severity.

**FLIP (batch 15):** en-nl u69 + fa-en a2 u25/26/28/29 + nl-en a2 u25-29 + prs-en a2 u25/26/28 = 13.
HELD: fa-en+prs-en a2_27 (fee/direct), prs-en a2_29 (join variants). NEXT: batch 16 = en-nl a2_24-28 +
fa/prs/nl-en a2_30-34.

## ⭐ Native review — BATCH 16 (2026-07-30): a2_30-34 (job_interview/travel/online/schedule/complaint) + en-nl a2_24-28

**FLIP (batch 16):** fa-en a2 u33/34 + prs-en a2 u31/32/34 + nl-en a2 u31/33/34 + en-nl a2 u24/28 = 11.
HELD (all on queued gloss/backfill/native items below): fa-en u30/31/32, prs-en u30/33, nl-en u30/32,
en-nl u25/26/27.

**QUEUED — wrong-sense backfill glosses (deploy-effect, native — the dominant a2 class, mirrors batch-15
fee=معاش):** these are shared-dict tokens reused for another unit's sense, reaching MC/translate/matching
answers. ALL need UNIT/LEVEL_SENSE_OVERRIDES + strip leaked parentheticals; NONE are pack-YAML/re-anchor.
- fa-en: u30 `next`=کنار(spatial)→بعدی, `meet`=ملاقات→رعایت("meet deadlines"); u31 `way`=طرف→راه(route);
  u32 `post`=noun پست→verb پست‌کردن (POS wrong too; prs-en already glosses it verb). + leaked parentheticals
  social/media/being (u30), leaves (u31), staying/touch/lot/many (u32).
- prs-en: u30 `well`="خوب (در hear well)" wrong-unit note; u33 `look`="معلوم شدن (در look well)" wrong-context.
- nl-en: u30 `social`/`being`/`next`/`looking` embed the English answer in the Dutch gloss; u32 `touch`/`waste`
  embed English + `lot`/`many` both→"veel" (synonym false-neg, add NL_UNIT_GLOSS_OVERRIDES veel disambiguation).

**QUEUED — prs-en u33 stale wave-3 migration (PACK-YAML fix, compile-time — straightforward):** its 3
`match.001` templates still use the pre-wave-3 cross-topic union `[weekday, sport_noun, hobby_noun,
education_noun, food_item, family_collective, dialogue_word]`; the proper `prs_en_a2_unit33_lesson02_words`
(7) / `_lesson03_words` (11) / `_lesson04_words` (12) tags already EXIST unused (all ≥6-pair floor) — commit
09e324d7 re-anchored siblings 30/31/32/34 but skipped 33. Re-point the 3 match.001 to their lesson tags +
update tag_schema (mirrors siblings exactly). [Doesn't fully flip u33 alone — the `look` gloss also holds it.]

**QUEUED — en-nl a2_25/26/27 near-dup-gloss MC collisions (deploy-effect backfill, LIVE MEDIUM):**
opinion_verb vind/vindt (ik vs hij/zij conj), bank_verb openen/geopend (inf/pp), visit_noun huisarts/dokter
(register-variant) — same verb/near-synonym both eligible as MC target+distractor; casefold-dedup misses them.
Fix = isolate the collider into a single-member tag or exclude from the MC/listen pool (backfill).

**QUEUED — content/native (LOW/judgment):**
- u34 (shared realization a2_unit34_shopping_complaint) reply_as_leila/speak_complaint prompt says "The clerk
  says: Can I help you?" but the Clerk never says it — Leila speaks first ("I'd like to return this blender…").
  Copy-paste from unit31's pattern. Non-grading (prompt text only) → flipped-with-note; reword the prompt
  (drop the fabricated line / scene-set instead). Affects fa-en/prs-en/nl-en (shared realization).
- **SYSTEMIC (all a2 units, LOW):** the long `reply_as_*`/`speak_*` dialogue_response exercises accept only
  ONE join-phrasing (period-split) while shorter writing_prompts in the same units offer comma/and variants →
  a taught-correct join style is graded wrong. Same class as batch-15 prs-en u29. Add ≥1 alternate join per.
- prs-en/fa-en u31 listen_bus_departure_time distractor "6:00"/"6.00" — the Agent says it for a DIFFERENT
  referent (train vs bus); reviewers judged it acceptable (disambiguated by the question). POLICY question:
  does the "full stop" distractor rule admit a different-referent exception? Your call.

## ⭐ Native review — BATCH 17 (2026-07-30): b1_01-05 opens (necessity/abilities/hypotheticals/debate/workplace) + en-nl a2_73-77

**FLIP (batch 17):** nl-en b1 u01-05 (ALL clean — first fully-anchored, defense-in-depth batch) + en-nl a2 u74 = 6.
HELD: prs-en b1 u01-05, fa-en b1 u01-05, en-nl a2 u73/75/76/77.

**KEY: nl-en b1 is CLEAN; X-en b1 is uniformly BACKFILL-GLOSS-GATED (like early a1 X-en).** The X-en b1
recognition-tier templates draw the unit-wide pool which surfaces leaked/grammar-note/wrong-sense glosses.
All fixes are `scripts/backfill_lexemes_{fa,prs}_en.py` (UNIT_SENSE_OVERRIDES + strip parentheticals), NOT
pack-YAML. One re-backfill wave clears them.

**QUEUED — prs-en b1 (deploy-effect backfill glosses):** untagged recognition pools surface must/make/don't/
set/did/done (u01), was/were/had/wasn't/like (u02), doesn't/didn't/**take** (u03, take=گرفتن(در take the
street) stale A1-directions context), **miss (u04, HIGH — گم کردن=lose-an-OBJECT, should be از دست دادن/دلتنگ
شدن; overlay gets it right, auto-gloss wrong; 13 live templates)**, little (u05). don't/did/doesn't/didn't
have ZERO real gloss (only an English grammar footnote) → worst.

**QUEUED — fa-en b1 (deploy-effect backfill glosses + overlay completeness):**
- **u05 (worst): report/update both wrong-POS** (taught as NOUNs گزارش/گزارش‌پیشرفت but shared-dict has them as
  VERBS گزارش‌دادن/به‌روزکردن), **course**="دوره"(class) for the idiom "of course"(البته), **sure**="البته" for
  "make sure"(مطمئن) — course/sure are literally each other's sense. 4 wrong-sense glosses, 5 live templates each.
  UNIT_SENSE_OVERRIDES for all 4. The shared `_en_target_lexeme_common.py:~297` code comment already flags the
  report homograph risk.
- u04 `sense`="حس"(feeling) for "makes sense"(منطقی/معنی); u01 `more`="بیشتر (در more expensive)" leaked (LOW);
  u03 `much`="چقدر"(interrogative-lean, LOW).
- **overlay completeness (compile-time, fa-en overlays — exact fixes):** u02 speak_ability_dialogue add
  "Next time, I'd be able to save time if I did it online too." (I'd contraction); u03 reply_as_leila add an
  "I'll…I'll…" contracted variant; u03 speak_hypotheticals_dialogue add the "would've signed up" variant
  (the same unit's write_if_had_known already accepts would've). These 3 are the ONLY blockers for u02/u03 —
  fixable without a re-backfill; do in a focused fa-en-b1 pass.

**QUEUED — en-nl a2_73-77 near-dup-gloss MC collisions (deploy-effect backfill tag isolation, LIVE):**
extends the batch-16 en-nl collision class. u73 vaardigheid/vaardigheden (MODERATE) + blanket-tag LOW; u75
**Probeer/probeer** (HIGH — case-variant, the pack's own note wrongly says bare MC is safe); u76 rooster/agenda
(MODERATE-HIGH); u77 artikel/exemplaar (LOW) + `regel` (LIVE, confirmed — shopping_complaint_verb, already
queued was/regel item). Fix = isolate the collider into an exact-case/single-member tag or exclude from the
MC/listen pool.

## ⭐ Native review — BATCH 18 (2026-07-30): b1_06-10 (narrative/conditions/sequencing/reported-speech/purpose) + en-nl b1_01-05

**DONE (compile-time fixes committed):**
- shared `realizations/en/b1_unit06` reply_what_happened: "happened" untaught forward-ref in the English prompt
  → target_blocks [] (source-language overlay instruction carries the task; both fa-en+nl-en flagged it).
- fa-en b1_08 + nl-en b1_08 speak/reply accepted_answers: added missing no-period / bare-without-"Sure."
  variants (taught-correct answer was checkpoint-graded wrong).
- FLIP: fa-en b1 u07/u08/u10 + nl-en b1 u06/07/08/09/10 + en-nl b1 u04 = 9.

**QUEUED — X-en b1 backfill wrong-sense glosses (THE dominant b1 class; UNIT_SENSE_OVERRIDES + re-backfill; one
wave clears all of prs-en/fa-en b1):**
- fa-en: u06 over(ختم‌شدن→pull-over)/when(interrogative→sequencing)/work(verb→noun)/got(took→arrived);
  u09 asked(درخواست‌کرد→پرسید for "asked whether")/read(infinitive→past)/long(بلند-physical→طولانی-duration).
- prs-en: u06 over/stopped(transitive→intransitive)/when/got/word(گپ→قول "kept his word")/offered; u07
  meet(آشنا‌شدن→جلسه‌کردن); u08 **dinner="شب چاشت" (non-standard; overlay uses نان شب)**/gets/start; u10
  study/studying ZWNJ near-dup collision in the single-item pool (matching_pairs was fixed, single-item wasn't).
- **ROOT (systemic, X-en):** the single-item recognition templates (choose/listen/translate) have NO
  semantic-tag filter, only POS — so both wrong-sense glosses AND grammar-jargon METALANGUAGE_TOKENS
  (tense/clause/verb/speech) reach them. The METALANGUAGE exclusion only covers tag-scoped matching_pairs.
  A proper fix: give the single-item templates a semantic tag too (or exclude metalanguage/wrong-sense at the
  pool level). This underlies the entire X-en a1+b1 leaked/wrong-gloss class.

**QUEUED — en-nl b1_01-05 (backfill NL_GLOSSES + near-dup-gloss, deploy-effect):**
- **HIGH wrong-answer:** u02 `waar` reaches MC as "where" but the unit teaches "waar"="true" (its slot POS list
  wrongly includes adverb — lessons 02-05 correctly exclude it; drop adverb OR homograph entry); u05 `was`
  LIVE = "do the dishes" but unit teaches copula "was" (slot includes verb; exclude verb OR was homograph).
- u01 `werk` verb→should be noun "job"; near-dup-gloss pairs werk/werkt, eet/eten (u02), beginnen/begint (u03),
  helpen/helpt (u02, cross-unit) — same NL_GLOSSES case-sensitive-only dedup gap. u04 cleanest (flipped).

**QUEUED — systemic completeness (all dirs, LOW):** reply_as_*/speak_* accepted_answers often omit taught
contraction/no-period/join variants → checkpoint-grades a taught answer wrong. Fixed opportunistically per pack
(u08 both dirs this batch); a corpus-wide sweep would close the class.

## ⭐ Native review — BATCH 19 (2026-07-30): b1_11-15 (hypotheticals/concession/relative-clauses/professional/complaints) + en-nl b1_06-10

**FLIP (batch 19):** nl-en b1 u11/12/14/15 (completeness variants added to u12/14/15) + fa-en b1 u11 = 5.
HELD: nl-en b1 u13, fa-en b1 u12/13/14/15, prs-en b1 u11-15, en-nl b1 u06-10 — all on backfill glosses.

**QUEUED — X-en b1 backfill wrong-sense glosses (re-backfill wave; each token: UNIT_SENSE_OVERRIDE or
FA_EN_EXTRA/EN_TARGET_TO_PRS gloss edit). CONFIRMED course-wide-reachable (untagged pools span the whole
b1 course → any unit's wrong gloss contaminates all), so one wave fixes all X-en b1 at once:**
- fa-en: u12 mind(اهمیت‌دادن→نظر "change your mind"); u13 meets(ملاقات→رعایت "meets deadlines")/works(خوب‌بودن→
  کار‌می‌کند)/desk(میز‌پذیرش→میز‌کار); u14 follow(پیگیری-noun→پیگیری‌کردن "follow up"); u15 name(اسم-noun→
  نام‌بردن "name the problem")/chair(صندلی‌میزکار compound-bleed→صندلی).
- prs-en: u12 mind(چیزی‌نگفتن→ذهن/فکر); u13 meets/works/used(استفاده‌کرد→"used to")/desk(میزپذیرش→میز)/just(فقط→تازه
  "just joined"); u15 sorry(ببخشین→متأسفم "sorry to hear")/ordered(فرمایش‌داد→سفارش‌داد)/name(noun→verb).
- **ROOT reconfirmed:** single-item recognition templates have NO semantic-tag filter → wrong-sense +
  metalanguage glosses reach them course-wide. The real systemic fix is to tag those templates (or exclude
  wrong-sense/metalanguage at pool level); until then every X-en b1 pack is gated on the gloss data.

**QUEUED — en-nl b1_06-10 (backfill NL_GLOSSES + near-dup, deploy-effect):** u06 werk(verb→noun)/eten(verb→
noun) wrong-sense + moet/moeten & hoef/hoeft near-dup conjugation pairs; u09 waar(where→true) + LIVE was;
regel LIVE in u06-10; u08 pending your native pass. No clean POS-drop (POS needed for correct tokens).

**QUEUED — nl-en b1 u13 (backfill judgment):** coworker/colleague both glossed collega/de collega (same Dutch
word) → near-dup MC collision + translation false-negative. Needs a fold-or-distinguish decision (not a YAML
one-liner). Only nl-en pack held this batch.

**QUEUED — systemic completeness (compile-time, all dirs):** reply_as_*/speak_*/writing_prompt accepted_answers
routinely omit natural contraction/expansion/no-period variants (I'd/I'll/that's/cannot…) → a taught-correct
answer graded wrong on checkpoint (grading forgives edit-distance-1 typos, NOT a whole-word contraction). Fixed
opportunistically where it's the SOLE blocker (nl-en u12/14/15, fa-en u08 this program); a scripted corpus-wide
sweep would close the whole class. fa-en b1 u12/13/14/15 completeness patches are exact-specified in the batch
reviews, to apply alongside their backfill fixes.

## ⭐ Native review — BATCH 20 (2026-07-30): b1_16-19 (advice/regret/future/summarizing) + en-nl b1_11 — COMPLETES the 4 English-primary dirs' a1/a2/b1 sweep

**★★ MILESTONE:** with batch 20, **fa-en / prs-en / nl-en / en-nl are fully swept across a1 + a2 + b1.**
nl-en is 100% flipped. The other three's remaining held packs ALL cluster on one lever (below).

**FLIP (batch 20):** nl-en b1 u16/17/18/19 (u19 completeness variant added) + fa-en b1 u16 = 5.
HELD: fa-en b1 u17/18/19, prs-en b1 u16-19, en-nl b1 u11 — all backfill glosses.

**QUEUED — X-en b1_16-19 backfill wrong-sense glosses (re-backfill wave; UNIT_SENSE_OVERRIDES):**
- fa-en: u17 looking(دنبال‌گشتن→نگاه‌به‌گذشته "looking back")/back(برگشتن-verb→به‌عقب-adverb); u18 made(درست‌کرد→
  گرفته "make a decision")/feels(احساس‌می‌شود-passive→احساس‌می‌کند-active)/experience(soft); u19 moved(نقل‌مکان‌کردم-
  1st-person→منتقل‌شد "meeting was moved")/many(چند‌تا-interrogative→زیاد-quantity).
- prs-en: u18/u19 since(از-temporal→چون-causal "since=because"); u17 long(دراز-physical→طولانی-duration); u16
  form(فورم-document→شکل-grammatical); u16/u19 direct/other stale (در ...) parentheticals; u19 right(راست→درست) LOW.

**QUEUED — en-nl b1_11:** grappig/grappigs near-dup MC collision (checkpoint-live HIGH) + was/regel (queued).

**═══ RE-BACKFILL WAVE (the #1 lever — unblocks ~all held X-en + en-nl + reverse-dir packs at once) ═══**
The dominant held-pack class across a1+b1 is deploy-effect gloss data in `scripts/backfill_lexemes_{fa,prs,nl}_en.py`
+ `_en_target_lexeme_common.py` — **AND (found batch 24) the reverse dirs too**: `backfill_lexemes.py` (en-fa) +
`backfill_lexemes_en_prs.py` carry the same embedded-metalanguage-gloss class (لازمه "(colloquial contraction…)",
آقای "(ezafe-linked form…)", قهوه‌یی "(spelling variant…)", اینجا, پُسته, "(spoken)" etc.) that renders verbatim
as MC answers/translate prompts — pervasive (52/56 templates in en-fa a1_39-43 alone), retroactively affecting
already-flipped reverse-dir packs. Same fix (split display-gloss from doc-note), same wave. Root cause (confirmed program-wide): the single-item recognition templates
(choose/listen/translate) carry only a POS filter, NO semantic tag, so wrong-sense + metalanguage glosses reach
them course-wide. Two remediation paths, YOUR call:
  (A) **Systemic:** give the single-item recognition templates a semantic-tag filter (as matching_pairs already
      has) — one structural change closes the whole class without per-token overrides. Best long-term.
  (B) **Per-token:** the ~60 UNIT_SENSE_OVERRIDES / gloss-strip entries catalogued across BATCH 8-20 +
      docs/LEAKED_GLOSS_INVENTORY.md. Faster to start, but a growing list.
Either way needs a dev DB to re-run the backfills (BLOCKED on you). Plus the discrete native-Dari/Farsi
confirmations (battery=بطری, jar=بوتل, fee=معاش→کارمزد, dinner=شب‌چاشت→نان‌شب, میته-resolved) and the en-nl
`was`-exclusion + near-dup-tag-isolation set. NEXT: batch 21 opens the en-fa / en-prs reverse directions
(English→Dutch/Farsi/Dari; batch 1 already did ~20 wave-4 packs of those).

## ⭐ Native review — BATCH 26 (2026-07-31): reverse-dir a1 tail + a2 open — en-prs a1_57-61 + en-fa/en-prs a2

**FLIP (batch 26): 6 packs** — en-prs a2_09 + a1_59/60/61 + en-fa a2_09/10. (a1 reverse-dir is now DONE bar
deploy-holds; a2 mostly needs a fix-pass — see below.)

**✅ FIXED by me:** en-fa a2 NEW-1 merged-unattributed-speaker dialogue_comprehension (a2_10/11/15/17
lesson04 comprehend_* merged two speakers into one em-dash block, no speaker field) → split into speaker-tagged
blocks. (a2_10 flipped; 11/15/17 still held on other issues below.)

**⚠️ NEW SYSTEMIC #4 — اما→و over-leniency (corpus-wide, ~23 en-prs a1 units + a2):** every `lesson06`/`lesson04`
wrap-up "write a sentence with اما (but)" exercise's overlay `accepted_answers` includes a variant that swaps the
contrastive **اما** for additive **و** ("and"), silently accepting a meaning-flipped sentence as a correct
contrast. Found in en-prs a1_36/39-56/57-61 + a2_10 (write_debate_summary) and the اگر-conditional analog in
a2_11/12/13. **Over-leniency only — never FAILS a correct learner**, so I've treated it as non-blocking and kept
the affected a1 packs flipped. Fix = drop the و-variant from the write_*_contrast accepted_answers corpus-wide
(mechanical; I can run it) — but NATIVE-CONFIRM first whether و ever reads as an acceptable loose paraphrase.
Distinct from the 3 earlier systemic classes.

**✅ a2 FIX-PASS PROGRESS (2026-07-31) — MECHANICAL fixes COMPLETE:** DONE — (a) NEW-1 attribution splits en-fa
a2_10/11/15/17; (b) metalanguage stripped from grammar-note target.text on 8 en-fa a2 cards → pure Farsi; (c)
en-prs a1_57 untaught-conjugation frames → attested forms + FLIPPED; (d) en-fa a2_15 + en-prs a2_15 lesson02
forward-ref prompts fixed (dropped leading متاسفانه/متأسفم); (e) en-fa a2_15 cancel_word example aligned to لغو شدن;
(f) en-prs a2_16 lesson02 attribution de-named. **FLIPPED this pass: en-fa a2_09/10/15/17/18 + en-prs a2_09/16 +
a1_57 (10 total incl. batch-26).** **REMAINING = native-judgment only (queued, NOT mine — Ramin's native lane):**
the STRUCTURAL forward-ref rephrases/pre-teach cards (en-fa a2_11 بکنم; en-prs a2_12 مشکل, a2_13 مشکلی, a2_17
می‌کنی, a2_18 مشکلی) — these foundational words are oddly first-taught in lesson04 of their own units; correct fix
= pre-teach in lesson01 (needs a native example sentence) OR native rephrase; I did NOT author fa/prs sentences.
Plus a2_14 self-answering matching wart (deploy), a2_18 بخاری teaching-order (LOW), NEW-2 off-theme re-anchors
(hygiene, Endless-only — non-blocking), NEW-3 typo-conflation (deploy).

**🔴 a2 FIX-PASS workstream (compile-time, mine — the reverse-dir a2 units need this before flipping):**
- **NEW-4 forward-ref in graded dialogue_response PROMPTS** (learner must read an untaught token to answer):
  en-fa a2_11 (بکنم, taught lesson04), a2_15 (متأسفانه, lesson04); en-prs a2_12 (مشکل, lesson04 — compiler-WARNed),
  a2_13 (مشکلی — NEVER taught anywhere; compiler-BLIND because validate_untaught_vocabulary only reports tokens
  taught in a *later* lesson, silently dropping never-taught ones — compile_content.py:2968); en-prs a2_15/17/18
  (متأسفم/می‌کنی/مشکلی in lesson02 prompts). Fix = rephrase the lesson02 prompt to an already-taught form, or move
  the token's intro earlier.
- **Hard metalanguage baked into grammar-note `target.text`** (English jargon tagged language_code: fa, shown as
  target): en-fa a2_11 (باز کردن "(to open, light verb)", رو "(object marker)"), a2_17 (-ها "(habitual plural…)"),
  a2_18 (پس دادن "(to return, light verb)"). Fix = move the jargon to the card's `note:`, keep target.text pure
  Farsi.
- **Teaching-card ordering / forward-ref in EXAMPLES (LOW, compiler-blind, examples aren't graded):** en-prs a2_18
  بخاری used in 4 lesson01 examples before its own card (8th of 9) — reorder heater_word to front; en-prs a2_14
  (مصاحبه‌کننده/وظیفه/سی‌هزار), a2_15/16/17 minor same-lesson-early example tokens; en-fa a2_15 cancel_word
  note-vs-example light-verb mismatch (لغو شدن vs لغو کردن).
- **NEW-2 off-theme course-wide pools + false unit-origin feedback_frame (Endless-Practice-only; checkpoint is
  unit-scoped so checkpoint-SAFE):** en-fa a2_11/15/17/18 POS-only/`reviewed_phrase`-union `choose`/`match`
  templates draw any course-wide same-POS token in Endless Practice while feedback_frame claims "from this unit."
  feedback_frame is runtime-INERT so the false claim isn't rendered, but the off-theme fill is real → re-anchor to
  a unit semantic tag (DEAD-trap-verify) OR neutralize. Same class as en-fa a1_53's 8 unscoped templates.
- **NEW-3 grading over-leniency (deploy/backfill):** typo-tolerance (distance-1, ≥4 chars, arabic strict) conflates
  taught near-pairs بیایید(u12)/بیاید(u13), خوبی(u17)/خوب(u16) — a wrong-but-taught word marked correct in
  course-wide Endless pools. Disambiguate glosses in backfill_lexemes.py.
- **en-prs a2_16 cross-lesson attribution:** lesson02 dialogue_response_own_habit instruction attributes a line to
  زرمینه that lesson04's canonical dialogue gives to همایون. Re-attribute or de-name.
- **en-prs a2_10 write_debate_summary + a1_57 untaught conjugation** (دیدیم/آوردم in practice frames — never taught;
  rephrase to attested همایون…دید / او…می‌آورد) **+ a1_58 zoo_word HARD metalanguage** (باغ/وحش glossed
  "(in باغ وحش: zoo)" — decompose باغ وحش as one atomic item, don't split into [باغ,وحش]) + animal_word pet-in-zoo
  soft frame (سگ/پشک در باغ وحش).
- **Meta:** en-prs a2_11/12/13 carry byte-identical templated "2026-07-11 fresh-context review" notes asserting an
  اگر-issue even in a2_13 which has no اگر — `status: reviewed` on those realizations was not independently earned.

## ⭐ Native review — BATCH 25 (2026-07-30): reverse dirs — en-fa a1_49-57 + en-prs a1_47-56

**FLIP (batch 25): 16 packs** — en-prs 47/48/49/50/51/52/53/54/55/56 + en-fa 51/52/54/55/56/57.

**✅ FIXED by me (compile-time):** en-fa 54-57 grammar-note citation errors (learner-facing prose) — داره/بزرگه
mis-cited "already taught from unit26" (verified real = unit04, corroborated by unit45's own correct note); u56
خوبه mis-cited "unit01/05/06/07/10/12" (real = unit06/10/12, matching u54's already-fixed note). Fixed 8
learner-facing strings; left unflagged و citations + internal review-notes prose untouched. Flipped 54-57.

**🔴 HELD — hard leaked-metalanguage glosses (RE-BACKFILL WAVE):** en-fa a1_49 (بازه "is open (spoken)", جعفری
"(surname)"), a1_50 (سفارش "(in سفارش دادن…)", دوغ), a1_53 (surnames حسینی/شاهین). Same deploy class.
**a1_53 ALSO needs a re-anchor:** 8 MC/translate templates (lesson01/02/04/06 choose.001/translate.002) have NO
`agreement_tags.semantic` → in Endless Practice `{item}` draws ANY course-wide token (off-theme) and the
feedback_frame falsely claims "introduced in this unit." Compile-time fix (add `semantic: [concert_word,
person_name, reviewed_phrase]`, DEAD-trap-verify) — do it when the gloss deploy unblocks u53.

**QUEUED — native-confirm / hygiene (non-blocking, flipped packs):**
- **en-prs 52-56 اما→و over-leniency (all 5):** each unit's wrap-up contrast writing_prompt
  (write_*_contrast / write_like_walking_no_time) accepts a variant swapping اما ("but") for و ("and") —
  over-lenient (no learner failed), violates AUTHORING_GUIDE §12. Native-confirm whether و reads as an
  acceptable loose paraphrase; if not, remove the و variant across all 5.
- **en-prs 52-56 soft multi-sense glosses** (برنامه "schedule; program", کارمند "clerk; employee", کورس
  "class; course", الماری "locker; cupboard", شروع "start; beginning") — milder than the hard-metalanguage
  class (both senses valid), but verbose as MC answers/translate prompts; trim to one primary sense in a gloss-
  hygiene pass. Not confirmed to visibly leak.
- **en-prs u55 میله** ("picnic/outing" — standard Persian sense is "rod/bar"; Afghan-regional festival sense) +
  **u51 رستوران vs رستورانت** spelling — LOW native-Dari confirms.
- **en-prs feedback_frame lang-mistag** (translate.006 pure-Dari text tagged `language_code: en, direction:
  ltr`) — recurs u49/50/52/54/55/57/58; feedback_frame is runtime-INERT so cosmetic, but could misrender if
  ever shown; fix at the template generator.
- **en-fa 49/50/51/52/53 ؟-punctuation** (write_*_message accepts only the ؟-form) — rides the keyboard/grading
  systemic. **en-fa u53 also** has the soft below-count self-report typo; u52 "7 tokens" off-by-one — cosmetic.

## ⭐ Native review — BATCH 24 (2026-07-30): reverse dirs — en-fa a1_39-48 + en-prs a1_34/35/37/38/41-46

**FLIP (batch 24): 11 packs** — en-fa 44/45/46/47/48 + en-prs 34/37/43/44/45/46.

**✅ FIXED by me (compile-time content-consistency):**
- **en-prs u44 (waste_disposal) plastic-bin contradiction (HIGH):** lesson01/03 taught & graded plastic→GREEN
  bin, contradicting lesson02/05 + the unit's own stated design (green=general waste, blue=recyclables incl.
  plastic) + the lesson05 reading ("plastic is ALSO in blue"). Canonicalized plastic→blue (سطل آبی) across
  teaching examples / matching_pairs / translation / overlay title+mirrors. Validates 0-err; flipped.
- **en-prs u46 (pharmacy) residual mistranslation (MED-HIGH):** the 2026-07-10 pass fixed 7/8 occurrences of
  "این نسخه از همایون است" glossed "This prescription is **from** Homayoun" (implies he wrote it; he's the
  patient) → "This is Homayoun's prescription." The 8th (matching-pair right-value, realization + overlay) was
  missed. Fixed both; flipped.

**🔴 HELD on the RE-BACKFILL WAVE — reverse-dir leaked-metalanguage glosses (NEW, deploy-effect, needs dev DB):**
The X-en `LEAKED_GLOSS_INVENTORY` class ALSO exists in the reverse dirs — `backfill_lexemes.py` (fa) and
`backfill_lexemes_en_prs.py` (prs) carry glosses with embedded authoring metalanguage that `service.py`'s
`derive_answer()`/`render_frame()` (slot_gloss/slot_text) render VERBATIM as the MC correct answer, a distractor,
the translate prompt, or a matching_pairs value. Confirmed instances:
- **en-fa (pervasive — 52/56 templates across a1_39-43 alone):** لازمه "necessary/needed (colloquial contraction
  of لازم است)", اورژانسه "is an emergency (spoken)", بزنید "call/hit (polite imperative, in زنگ بزنید…)", آقای
  "Mr. (ezafe-linked form of آقا)", امانت "loan (in امانت گرفتن…)", پس "back (in پس دادن…)", پلاستیکه/بازیافته/
  شنبه‌ست "(spoken)", دیدید "did you see? (polite)". Likely present corpus-wide (any fa lexeme with a
  parenthetical gloss). **Retroactively implicates earlier reverse-dir flips too** — the re-backfill wave must
  clean fa/prs glosses, not just X-en.
- **en-prs:** قهوه‌یی "brown (spelling variant of قهوه‌ای…)" (backfill_lexemes_en_prs.py:1212, u38); اینجا "here
  (spelling variant of این‌جا, no ZWNJ)" (:1238, u41 — GUARANTEED exposure, sole candidate); پُسته/پُستی "post
  (as in پُسته خانه…)"/"postal (as in تکت پُستی…)" (:1184-1185, u35).
Fix = split display-gloss from documentation note (trim the learner-facing gloss to just the word; move the
parenthetical to a doc-comment), re-run the backfills against the DB. Folds into the **RE-BACKFILL WAVE** (see
that section). **HELD on this: en-fa a1_39/40/41/42/43, en-prs a1_35/38/41.**

**HELD on other deploy/thin:** en-prs a1_42 (thin lexeme pool → 1 tier-short, checkpoint_unavailable; needs
backfill lexeme extension — native-clean); en-fa a1_40 چتر ("umbrella", core unit40 vocab) tag-scoped to unit07's
weather lesson so unit40 can't host it (backfill fix); en-fa u41/u42 genuinely thin (zero-lexeme lessons).

**QUEUED — compile-time (do in a focused pass; these units are HELD on the deploy gloss anyway):**
- **en-fa u41 lesson02.order.003** frame `پنجشنبه {item}` over availability_word draws آزادید (a QUESTION form,
  taught only as آزادید؟) → generates the statement "پنجشنبه آزادید" (no ؟) which asserts something odd. Split
  into two single-member word_order templates (آزادم ending `.`, آزادید ending `؟`) or drop آزادید.
- **en-fa u43 realization** 4 undeclared fused-copula example tokens (زباله‌ست/کاغذه/شیشه‌ست + forward-ref
  شنبه‌ست) in teaching cards — compiler-invisible (examples aren't graded), LOW; add to their cards'
  introduced_tokens.
- **en-prs u38 color contradiction:** Zarmina says "رنگ آبی را دوست دارم" (blue) in lesson04 dialogue but the
  lesson05 reading narrates "او رنگ سبز را دوست دارد" (green). Reconcile to blue (dialogue = character's own
  words = canon). Compile-time, but u38 is deploy-held on قهوه‌یی anyway.

**QUEUED — native/minor (non-blocking, flipped packs):** en-fa 44-48 lesson05 `write_*_note` prompts grade only
the exact example under strict fa grading (underdetermined production — reword "Copy this note" or widen accepted
variants); en-prs systemic و/اما (contrast instructions accept و for اما — native-confirm, all reverse units);
en-prs u43 قرض predicative gloss + u46 دانه bare-classifier slot (LOW native-confirm); en-fa u39 order.003
feedback_frame double-copula (feedback_frame is runtime-INERT → hygiene only).

## ⭐ Native review — BATCH 23 (2026-07-30): reverse dirs — en-fa a1_23-30/37-38 + en-prs a1_22-33

**FLIP (batch 23): 12 packs** — en-fa 23/24/25/26/27/28/29 + en-prs 22/24/27/28/29.

**✅ FIXED by me (compile-time):**
- **reading_comprehension merged-unnamed-speaker** (same class as u14) — en-fa u18/u23/u24 lesson06.exercise03
  merged two first-person speakers into one speakerless block (unanswerable: both correct answer & distractor
  verbatim-true). Split into سارا/نیما `speaker:`-tagged blocks per each lesson's dialogue attribution. (u18 was
  already flipped in batch 22; fix improves it retroactively.)
- **en-prs u23 empty-target_blocks MC** — `lesson04.exercise02.recognize_amount` (instr "Select the correct
  translation" with NO referent) got `target_blocks: [صد دالر]`; `lesson05.exercise02.reading_comprehension_where`
  got the exercise01 passage. Both were unanswerable.

**HELD:**
- **en-prs a1_23/30/31/32/33** — blocked (mainly) on the punctuation/keyboard SYSTEMIC item above (untypeable
  `.`/`!` answers; u30-33). u23's other 2 defects are fixed; its remaining 2 are `؟`-variant (that class). Plus
  teaching-card untaught vocab: **دشوار** (u31 lesson02 examples, only introduced 2 lessons later), **خوشمزه** +
  **می‌گویم** (u32 lesson01 examples; خوشمزه never taught corpus-wide, می‌گویم is A2) — content-quality, fix by
  retiming the intro or rewording the example.
- **en-fa a1_30** — `backfill_lexemes.py` tags **رشته‌ی** (bound ezafe fragment, never taught standalone) into
  `subject_word` with english_gloss `"major of (ezafe-linked form of رشته)"`; render_frame uses english_gloss
  unscrubbed → this metalanguage string can surface as the MC answer / translate prompt. DEPLOY-EFFECT (backfill
  fix + re-run, needs dev DB) — same leaked-metalanguage class as the X-en inventory. (Also: u30 vs u18 char
  canon — نیما/سارا at university vs their jobs — low, native/judgment.)
- **en-fa a1_37/a1_38** — (a) `dialogue_comprehension` prompt uses untaught reporting verbs می‌پرسه/می‌گه (+ 3rd-
  person دوست داره in u38) instead of the actual taught dialogue — fix by reverting the prompt to the real
  transcript (my audio-fix pattern); (b) factually-false word_order frame: u37 `موز {item}.` lets the banana be
  any of 7 colors (contradicts taught "موز زرده"), u38 `{item} سرده و برفیه.` lets تابستان be "cold and snowy"
  (contradicts taught "تابستان گرمه") — narrow the pool/frame (DEAD-trap: verify unit-scoped count).

**QUEUED — reverse-dir minor/native (batch 23, non-blocking, flipped packs):**
- **en-fa a1_26 thinness** — `pet_description_word` tag omits کوچیکه/بزرگه (first-occurrence-wins provenance keeps
  unit04's `family_description` anchor for the identical token) → lesson04 drills only color, never size. Add a
  unit26-scoped discriminator key (mirrors the چند تا precedent) + widen. Compile-time/deploy.
- **en-prs a1_22 گرم gloss** — taught in-unit as "hot" (title/gloss) but its reused lexeme's PRS_GLOSSES entry is
  "warm" → Endless-Practice could show either. Native-Dari: pick one canonical gloss. LOW.
- **`(spoken)`/`(informal)` english_gloss annotations** (corpus-wide, backfill_lexemes FA_GLOSSES/PRS) surface
  verbatim to learners in MC/translate copy (e.g. "how much is it? (spoken)"). Same class as the leaked-gloss
  inventory — systemic gloss-hygiene, deploy-effect. LOW.
- **matching_pairs below-floor** — en-prs u23 match_money_words (4), u24 match_transport_words (5), various
  u30/32/33 (pre-existing, self-reported in pack notes) — §16 "aim" not a hard rule. Cosmetic.

## ⭐ Native review — BATCH 22 (2026-07-30): reverse dirs — en-fa a1_13-22 + en-prs a1_12-21

**FLIP (batch 22): 22 packs** — en-prs 12/13/14/15/16/17/18/19/20 + en-fa 13/14/15/16/17/18/19/20/21/22
(plus en-prs 07/08/09 unblocked by the audio-accessibility fix above). All 4 fresh-context reviewers ran the
full mechanical gate (scope-check, practice-validate, register-check, compiled-JSON audio-accessibility check) —
reverse dirs stay much cleaner than X-en. **HELD: en-prs a1_21 only** (see below).

**✅ FIXED by me (compile-time, no native confirm) — en-fa a1_14 reading_comprehension:**
`fa.a1.unit14.lesson06.exercise03.reading_comprehension_who_likes_what` merged two unnamed "من" speakers with
no attribution → both the correct answer (نیما=tea/warm) and the distractor (سارا=coffee/delicious) were
verbatim-true in the shown text (unanswerable). Split into two `speaker:`-tagged text_blocks (سارا / نیما) per
the lesson's own dialogue attribution + unit15/17 precedent. Validates 0-err; pack flipped.

**HELD — en-prs a1_21 (2 issues):**
- **NATIVE-CONFIRM (HIGH, do NOT auto-change): پنجصد vs پانصد for "500".** Unit21 uses regularized **پنجصد**
  pervasively (realization media/teaching/dialogue + ~15 overlay accepted_answers). Iranian-standard is the
  fused **پانصد**. BUT this may be a DELIBERATE Afghan-Dari regularized numeral — the same pattern, **دوصد** for
  "200", recurs **15× across the corpus** (Iranian دویست appears nowhere). Afghan Dari genuinely favors analytic
  numeral compounds, so this is plausibly correct register, NOT an error. Needs a native-Dari ruling before any
  find/replace. If confirmed wrong: mechanical `پنجصد`→`پانصد` (+ audit `دوصد`→`دویست` corpus-wide) then
  re-validate.
- **COMPILE-TIME (queued): 3 translate exercises drop the taught "؟".** `lesson03.exercise06.translate_size_question`,
  `lesson04.exercise06.translate_try_on_request`, `lesson05.exercise05.translate_asking_color` — accepted_answers
  omit the "؟" that the same phrase's teaching card / recognition tested_text / dialogue line all carry, and
  Dari gets zero punctuation tolerance in grading (`orthography_strict` unset → `tolerant=script=="latin"`=False)
  → a learner reproducing the exact taught form is marked wrong. Fix: add the "؟"-bearing form as an accepted
  variant on all 3. (Deferred with the pack since it's held on the numeral question anyway.)

**QUEUED — reverse-dir minor/native (batch 22, non-blocking, packs already flipped):**
- **en-fa a1_21 untaught token مجموع** ("total") in `lesson06.exercise03.match_dialogue_facts` pairs — never in
  any `introduced_tokens`; compiler misses it (doesn't check `pairs`). Fix: add a مجموع teaching card to lesson06
  OR drop the pair + widen with an already-taught fact. (Content edit, not native-blocking.)
- **en-fa a1_20 `lesson01.teach.want_word`** gloss/note swapped (gloss holds a full sentence, note holds the
  explanation) — cosmetic; می‌خوام is a grammar_note, never reaches the pack. Swap to match sibling cards.
- **en-prs a1_12/13 introduced_tokens punctuation-bundling** (`چطور؟`, `است؟` bundle the "؟" into the token) —
  cosmetic bookkeeping, no untaught-vocab gap.
- **en-prs a1_20 `volume_order.002` feedback_frame** is a raw Dari echo with no English gloss — but feedback_frame
  is runtime-INERT and this is a corpus-wide template-generator artifact (~64 files). Cosmetic; fix at the
  generator level if ever revisited, not per-file.

## ⭐ Native review — BATCH 21 (2026-07-30): REVERSE dirs open — en-fa a1_03-12 + en-prs a1_01-11

**KEY: the reverse dirs (English→Farsi/Dari) are much CLEANER than the X-en dirs** — their target text is
hand-authored in realizations/fa + realizations/prs (not shared-dict-generated), so the wrong-sense-gloss-reuse
class that gates X-en doesn't apply. 16/20 packs flipped this batch.

**FLIP (batch 21):** en-prs a1_01/02/03/04/05/10/11 + en-fa a1_03/05/06/07/08/09/10/11/12 = 16. (en-fa u09
kept flipped with است — see note.) HELD: en-prs a1_07/08/09, en-fa a1_04.

**✅ RESOLVED (2026-07-30) — audio-accessibility sweep, en-prs a1_07/08/09 + 12 more units.** Root cause pinned:
the §14 audio-accessibility retrofit (2026-07-06) converted `listen_type`/`listen_select` but MISSED the
`dialogue_comprehension`/`listen_context` type; a later 2026-07-07 fix then blanked those exercises'
`prompt.target_blocks` to `[]`. Net: every `dialogue_comprehension` with empty `target_blocks` renders with no
audio (fa/prs have zero TTS AND the compiler wires `audio_text` only for listen_* types, never
dialogue_comprehension — confirmed) and no readable text → unanswerable. Fixed all 17 broken exercises across 15
units by populating `target_blocks` with the lesson's own taught dialogue (explicit `speaker:` from the `kind:
dialogue` teaching cards; media-asset transcript fallback for phrase-only lessons) + rewording overlay
instruction "Listen…"→"Read the conversation." (kept `type: dialogue_comprehension` — renders via the same
MultipleChoice/TextBlock component, so the `speaker` field shows as "Name:" labels). Units fixed: **en-prs
01/02/04/05/06/07/08/09** (u01 also lesson05.listen_extended_greeting + lesson06.dialogue_facts) + **en-fa
06/07/08/09/11/21/22**. All 15 realization/overlay pairs validate 0-err. en-prs 07/08/09 (sole batch-21 blocker
was this) now FLIPPED.

**QUEUED — en-fa a1_04 possession-verb agreement (deploy-effect backfill, HIGH):** lesson02.have_order.003
frame "من یک {kinship_term} {possession_verb}" hardcodes 1st-person من but possession_verb is a flat tag
mixing persons (دارم/داری/داره/دارد/…) → ~5/7 draws are ungrammatical AS THE CORRECT ANSWER ("من یک برادر
داری"). Fix: add a `possession_verb_1sg` sub-tag (دارم/ندارم) in fa_agreement_tags() [backfill_lexemes.py,
re-backfill] + repoint the slot. Secondary: lesson04.kin_order.003 negative-interrogative draws.

**QUEUED — reverse-dir minor/native (LOW):** en-prs پوسته‌خانه (post office, low-conf native-confirm);
en-fa u09 write_meeting_time_summary uses formal است in a colloquial unit (register nit — proper fix needs
عصره TAUGHT first, else it's an untaught-token compile error, verified; deferred, u09 flipped as-is since
است is grammatical + graded-correct); en-fa u12 آرش/سارا character-pairing breaks the settled سارا/نیما duo
(advisory); en-fa u04/u06 tested_text-vs-audio register cosmetic (non-graded).

**DOC-HYGIENE (found by 3 reverse-dir reviewers):** CLAUDE.md "Per-lane register pins" only defines fa-en/
prs-en (the X-en dirs); it has NO explicit en-fa/en-prs pin. The operative pin for the reverse dirs lives in
each realization's own `course.register_policy`/`dialect` (en-fa = Iranian fa_IR standard-colloquial; en-prs =
Afghan prs_AF kabuli استم/استین/می‌تانین). Add explicit en-fa/en-prs entries to CLAUDE.md so future dispatchers
don't mis-cite the X-en pin.

## ✅ en-nl _pure WAVE + prs-en u14 re-anchor — 2026-07-29 (deploy-effect)
LATER (2026-07-29/30, loop cont.): also done — prs-en u14 5 bare-POS pools re-anchored (7deec01b);
fa-en u15 digit fix (4171fccb); prs-en painting→نقاشی (2c9e76fc); en-nl u13 preference_item_pure
(453ffb50); en-nl u14 equal_adj exact-case excl. 'Mooi' (20aa8bca); nl-en u30 malformed dup template
(2bb61b1d); en-nl u9 route_word→route_map_pure {route,START,DOEL} (8cc4a302); en-nl u8 voor→
position_no_voor (0bf6a8e7). **en-nl _pure tail now CLEARED except u19 weekday.**
**REMAINING — all HIGH-RISK or NATIVE-JUDGMENT (NOT auto-fixable; do NOT churn/risk):**
- **u19 weekday casing-fold (HIGH-RISK, queued for a careful native/integration-tested pass):** the
  weekday tag is contaminated with metalabels + CAPITALIZED sentence-initial day tokens, and
  weekday_pure has 0 unit19-scoped members (unit19's own weekday was introduced capitalized) — the
  DEAD-trap. The real fix is an NL_CITATION_FORMS-style lowercase-fold of weekday tokens in
  backfill_lexemes_en_nl.py — a broad classifier-mechanism change affecting weekday across ALL units,
  which needs the integration suite (Postgres, blocked here) + native verification before it's safe.
- **NATIVE-JUDGMENT (queued):** prs-en 28 + fa-en 22 collision-token gloss disambiguation
  (well=خوب etc. → non-English Dari/Persian disambiguator); prs-en Dari orthography confirms
  (سکو/صبح‌چاشت/تُند/قیمتی‌تر/زیاتر/خیر استه/شرت/انجینیر); fa-en 33 phrase-derived leaked-gloss
  stragglers; the deferred lesson01 matching_pairs forward-reference (shared realization, high revert).
- **DEPLOY-BLOCKED:** ALL of the above content fixes are deploy-effect — none is live until a
  re-backfill/re-seed (needs the live server / dev DB). Plus the readiness-audit must-fixes
  (ADMIN_EMAILS, live deploy, TLS, backend CI run). **Deploy is the lever.**

## ✅ en-nl _pure WAVE — COMPLETE 2026-07-29 (deploy-effect)
All LIVE en-nl blanket-tag contamination / reworded-capital MC-ambiguity from batches 5+6 is
source-fixed: 4 safe existing-tag swaps u16-19 (symptom_hebben/work_vocab/room_word/weather_vocab →
_pure, commit 7870b4ab) + 5 new exact-case classifier tags — symptom_zijn_pure (d2ee6288),
payment_noun_pure/clothing_fit_pure/room_count_question_pure (039a0a93), phone_identity_pure/
phone_clarification_pure + u22 match_union rebuilt (174d3854). Each DEAD-verified (unit-scoped count ≥
floor) + validate 0/0 + unit-scope unchanged. text_message_pure determined UNNEEDED (translate.001's
[verb,noun] POS filter already yields {bel,stuur,sms}). **STILL OPEN (en-nl, deploy-effect, NOT in
this wave):** u19 weekday DEAD-trap (needs NL_CITATION_FORMS casing fold, not a _pure swap); u12 voor
position-sense gloss; u13 preference_item / u14 equal_adj reworded-capital (need their own _pure or
narrow); u8 route_word contamination. u30 volume_order.006 malformed dup template.

## ⭐ Native review — BATCH 6 (2026-07-29, ALL 4 REPORTED): fa-en/prs-en/nl-en a1_21-24+30, en-nl a1_21-23/29/30

**prs-en batch 6 (a1_21-24/30):** all 5 OPEN, same recurring classes — ambiguous listen_select
(u21 listen_ticket_request, distractors literally spoken in the full-dialogue clip), underdetermined
production prompts (u21/u22 reply_as_daniel: a required clause has no cue; u23/u24 do it right),
within-unit forward-ref (u23 "job" first taught lesson04), undisclosed thin below-floor (u22/u24 →
could add prs_en_a1_unitNN_words tags), **Dari mistranslation `painting`="رنگ‌مالی" (wall-painting) vs
artistic "نقاشی"** (deploy-effect gloss fix; overlay already uses نقاشی), example_gloss schema-gap
(u22/u24 pre-1.1), + orthography native-confirms (سکو/سردردی/انجنیر-vs-انجینیر/هیچ‌وقت). NOTE: prs-en
confirmed NO leaked-gloss reachable in u21-30's slotted tags (that class lives in earlier units).
No prs-en batch-6 pack flipped.


**FLIPPED reviewed (CLEAN):** en-nl a1_21/29/30, fa-en a1_24 (commit 5c07b220). → 76/553 reviewed.

**OPEN — all recurring known classes (queued into the existing waves):**
- **en-nl u22/u23 — needs NEW exact-case `_pure` tags** (blanket-tag contamination, LIVE MC/matching
  ambiguity): u22 `phone_identity_pure`{Met,wie,U,spreekt} + `phone_clarification_pure`{Spreek,hoor}
  (match.005 — the "met"/"Met"=with/This-is pair genuinely differs → real ambiguous matching_pairs) +
  `text_message_pure`{bel,stuur,sms} (translate.001); u23 `payment_noun_pure`{rekening,wisselgeld,
  totaal} (5 templates — "rekening"/"Rekening"=the bill/Bill live MC distractor). Reviewer verified
  unit-scoped counts safe (no DEAD). backfill_lexemes_en_nl.py + repoint. Deploy-effect. → en-nl _pure wave.
- **fa-en u23/u30 — leaked-annotation gloss (HIGH, LIVE):** u23 `answer`="جواب دادن (در answer emails)"
  reachable in match.003 (fa_en_a1_unit23_words); u30 `video`="ویدیویی (در video games)" reachable in
  lesson03.translate.001 via the UNTAGGED bare-POS `content_word` pool — which at course scope is a
  wide leak vector for the WHOLE corpus (fa-en gloss dict has ~231 "(در <english>)" tokens, like
  prs-en's 186). Fix: strip the two glosses (collision-check) + narrow content_word to
  fa_en_a1_unit30_words. → the leaked-gloss wave (now confirmed BOTH prs-en AND fa-en).
- **Ambiguous listen_select — distractors literally spoken in the multi-turn audio** (NEW recurring
  class; realization-level, shared): nl-en+fa-en u21 listen_ticket_request ("One way or round trip?"/
  "That's forty dollars." are said by the Clerk in the same clip), fa-en u30 listen_dialogue_leila_
  hobby ("reading" is Leila's own line). Fix: scope the instruction to a speaker/moment ("what X says
  first") or trim the audio clip. Shared EN realization → affects all X-en. Queue (careful).
- **Deferred (already-tracked):** lesson01 matching_pairs forward-reference (nl-en u21 match_travel_
  words 3/8, u24 match_rooms balcony; fa-en implied) — shared-realization, high revert risk, Ramin's call.
- **fa-en u21/u22 reply-prompt completeness gaps** (a required clause has no cue in target_blocks;
  units 23/24 do it right → avoidable). Add the missing cue or narrow accepted answer. Native-EN judgment.
- **nl-en u30 `volume_order.006` malformed dup template** (English feedback, paste-error content_key,
  TIER-LOAD-BEARING — do NOT blind-delete; give it a proper key + Dutch feedback OR replace with a
  distinct structured-tier exercise). nl-en u23 lesson01.match.003 lesson-anchoring quirk (silently
  under-available early, never wrong) → re-point lesson_content_key to lesson04.
- **Realization fact-drift:** fa-en/shared u30 — Daniel "often" (l3) vs "always" (l4) goes running.
  Pick one, shared EN realization. LOW (not currently graded).
- **INERT (feedback_frame):** false-provenance across many u21-24/30 packs → the consolidated sweep.

## ⭐ Native review — BATCH 5 (2026-07-29, ALL 4 REPORTED): fa-en a1_15-20, prs-en a1_16-20, nl-en a1_15-20, en-nl a1_16-20

**nl-en (a1_15/17/18/19/20) reported first — all findings are already-tracked or runtime-inert; nothing
new-and-live:**
- **Within-unit forward reference in lesson01 matching_pairs (class 5)** — 4/5 units (15/18/19/20):
  the realization's fixed lesson01 `match_*` exercise pads past lesson01's own vocab with 1-3 pairs
  first taught in later lessons of the same unit (e.g. u18 match_past_verbs includes watch/do/be from
  L2-L4). `canonical_pairs()` grades all-or-nothing. This is the ALREADY-TRACKED, DEFERRED
  shared-realization class ("~9 files across dirs", high revert risk, Ramin's call) — fix = trim
  lesson01 pairs to lesson01-native + mirror to every X-en overlay. NOT done (queued, careful paired pass).
- **feedback_frame false-provenance / stale counts / one echo bug — RUNTIME-INERT** (not read by
  generate_batch/build_prompt; same finding as a1_10-14). u17 (3× 'uit deze les' over a 1027-word
  untagged pool), u18 verb_pair.003 ('twee'→should be 'vijf'), u19 (2× false-provenance over 315-verb
  pool), u20 volume_order.009 (feedback echoes the English prompt instead of Dutch). Fix pattern =
  the a1_10-14 genericization. QUEUED as part of a CONSOLIDATED corpus-wide feedback_frame sweep (do
  once, not per-batch, since inert) OR fold into the unit-tag re-anchor.
- Tier-short (u18 verb_pair past_verb=5, u20 match.003 comparative_adj=5) = hard pool ceilings (the
  known 2 tier-short); naturalness nits (u15 'pay with credit', u20 'bag is faster') = LOW/optional.
- **No nl-en batch-5 pack flipped** (every unit has ≥1 open finding, all queued classes).

**ALL 4 BATCH-5 REVIEWERS REPORTED (2026-07-29).** Findings by systemic class:

**★★ LEAKED-ANNOTATION GLOSS WAVE — SAFE SETS DONE 2026-07-29 (deploy-effect).** Stripped the
collision-free-safe leakers: prs-en 63 (commit 2275464d) + fa-en 48 (commit 5343057e) = 111 tokens.
Verified each: module imports, content suite 34/34, no new collisions possible by construction (safe
set required each stripped gloss to have exactly one owner). **RESIDUAL (still queued):** prs-en 28
collision tokens + 'Path' straggler + 'works' {day} bug; fa-en 22 collision tokens + 33 phrase-derived
safe tokens (not dict keys — need a different fix path). Collision tokens must be disambiguated in
Persian/Dari (not stripped — stripping re-exposes a shared gloss e.g. well=good/fine/okay) OR the
consuming template narrowed (fa-en a1_03 precedent). Original analysis below.

**★★ LEAKED-ANNOTATION GLOSS WAVE (prs-en + fa-en) — LIVE, systemic, HIGH.** The gloss dicts use a
`"<persian> (در <english phrase>)"` convention; where the English TOKEN is a substring of its own
gloss, any template that renders the gloss as a bare translate-prompt (prompt=gloss, answer=token,
100% leak) or MC/listen option hands the learner the answer. Traced end-to-end (gloss →
_distractor_values/derive_answer verbatim → raw render). **prs-en: ~186 Latin-parenthetical glosses;
92 are true leakers (token ∈ gloss).** Ran a collision analysis (scratch `gloss_leak.py`, logic:
strip trailing `\s*\([^()]*\)\s*$`, check if the stripped gloss still contains the token, and whether
it collides with another token's final gloss):
  - **64 SAFE to strip** (stripped gloss is token-free AND unique) — bulk-strippable. e.g. across/
    advance/bed/dressed/end/front/gone/hand/lock/love/manage/... (regenerate the full list via the
    script). credit/debit already DONE (35003d4e).
  - **28 COLLISION** (stripping re-exposes a shared gloss → do NOT strip; disambiguate in Dari without
    English, or narrow the consuming template): answer(=reply), away(=far), back(=open), by(=with),
    community(=outgoing/social), did(=s), direct(=straight), each(=every/per), excuse(=sorry),
    get(=arrival), journey(=trip), little(=slightly), look(=seem), lot(=very), make(=pick/take),
    many(=few), miss(=lose), must(=should), other(=another/else), pick, s, set(=put), take, up(=wake),
    very, wake, well(=fine/good/okay), within(=until).
  - **`works` gloss = `"مناسب/خوب بودن (در {day} works for me)"` has a literal unrendered `{day}`** —
    malformed, MUST rewrite (drop the brace + the English leak).
  - **fa-en equivalent** (own backfill, own collision analysis needed): u16 wake/dressed/bed
    ("بیدار شدن (در wake up)" etc. → reviewer says safe to pure-Persian: بیدار شدن/پوشیده/رختخواب);
    u10 get/can't (batch-4); "much" already fixed via the a1_03 template-narrow.
  - **APPROACH:** bulk-strip the collision-free set per direction (scripted, then iter_specs-verify no
    "(در" remains + no new collision + no DEAD); for the collision set, prefer a non-English Dari
    disambiguator or narrow the consuming translate template (fa-en a1_03 precedent). Deploy-effect.

**★ en-nl BLANKET-TAG `_pure` SWAPS (LIVE — MC ambiguity + wrong-capital display).** batch-5 en-nl:
  - **SAFE now (existing _pure tag, reviewer-verified unit-scoped counts ≥ floor — but RE-VERIFY per
    the weekday DEAD-trap law before each):** u16 lesson01/02/04/05/06 `symptom_hebben`→`_pure` (4);
    u17 the 9 recognition/production templates `work_vocab`→`work_vocab_pure` (8); u18 lesson01.order
    `room_word`→`room_word_pure` (5); u19 the 7 recognition templates `weather_vocab`→`weather_vocab_
    pure` (8). Pack-side swaps.
  - **NEEDS A NEW backfill tag** (deploy-effect): `symptom_zijn_pure` (u16, ziek/verkouden),
    `room_count_question_pure` (u18, appartement/kamers/slaapkamers — excludes cross-unit function
    words), `clothing_fit_pure` (u20, excludes capitalized `Past`).
  - **⚠ DEAD-TRAP (do NOT naive-swap):** u19 `weekday` — at unit19 checkpoint scope the only reachable
    members are capitalized `Zaterdag`/`Zondag` (from unit19's own sentence-initial teaching), and
    `weekday_pure` has 0 unit19-scoped members → swap would DEAD it. Real fix = an
    `NL_CITATION_FORMS`-style capital→lowercase fold in backfill_lexemes_en_nl.py (extend the
    2026-07-22 volume-batch fold to pre-volume A1 units), OR bake a literal weekday into frame text.

**fa-en batch-5 (a1_15/16/18/19/20):**
  - **u15 content_translate.006 / content_choose.005 (HIGH, LIVE false-NEGATIVE):** `content_word`
    includes `symbol` POS → digit lexemes "1"/"10" (gloss یک/ده). Translation renders the gloss and
    grades the bare digit — a learner typing "one" is marked wrong (no typo tolerance <4 chars). Fix:
    drop `symbol` from content_word POS (→ [noun,verb], like u16/u19). Pack-side; verify pool ≥ floor.
  - u16 wake/dressed/bed leaked glosses (see leaked-gloss wave).
  - u19 verb_meaning.001/.004 false "this lesson's preference VERB" feedback over a pool with adj/adv
    members (INERT — feedback_frame) + `choose_prefer_answer` ambiguous MC (hand-authored: distractor
    "I like tea because it's calmer" is also correct) → narrow the instruction to name the "prefer" form.
  - u18 verb_pair.003 / u20 match.003 below-floor (5<6): the generated `fa_en_a1_unit18_words`(12) /
    `_unit20_words`(10) tags EXIST → widen+re-anchor is available (units 15/16/19 got it; 18/20 were
    skipped). LOW value (below-floor is the accepted honest-thin ledger) — consistency polish, optional.

**DEFERRED / already-tracked (all dirs):** within-unit forward-reference in lesson01 matching_pairs
(realization-level, shared across X-en overlays, high revert risk — Ramin's call). Present in nl-en
u15/18/19/20, prs-en u16/18/19/20, fa-en (implied), en-nl (via realization).

**NATIVE-CONFIRM (prs-en Dari — escalate):** صبح‌چاشت (breakfast? vs صبحانه/ناشتا), تُند (strong coffee?
vs غلیظ/قوی), قیمتی‌تر (more expensive? vs گران‌تر), زیاتر (typo for زیادتر?), خیر استه (okay? خیر often
reads "no"); + a gloss embedding literal "Unit 19" metalanguage (u19 `like`). شرت (shirt vs شورت) from
batch 4.

**INERT (feedback_frame — not read at runtime):** false-provenance / stale-count / echo across many
packs (nl-en u17/18/19/20, fa-en u19/u20, prs-en). QUEUED as ONE consolidated corpus-wide feedback_
frame sweep (do once, low priority) OR fold into the unit-tag re-anchors.

**en-nl u20 listen_notice CRITICAL — DONE 2026-07-29 (commit 3bb81f73).** Also: u20 practice pack was
marked review.status:reviewed despite open findings — should be set back to unreviewed.

**No batch-5 pack flipped reviewed** (every pack has ≥1 open finding).

**DONE from the batch-3/4 ★ backfill wave this session (deploy-effect, source-correct):**
- **prs-en credit/debit leaked-gloss** (commit 35003d4e): stripped '(در credit/debit card)' → clean
  اعتباری / بانکی؛ مستقیم; collision-verified. Fixes unit15 card_type_translate (100% leak) + payment.
- STILL QUEUED in the ★ wave: prs-en `well`='خوب (در hear well)' — do NOT strip ('خوب' already =
  good/fine/okay → 4-way collision); fix via the unit14 bare-POS re-anchor (prs_en_a1_unit14_words,
  DEAD-verify per POS). fa-en get/can't (unit10 verb_gloss). The broader prs-en/fa-en '(در <english>)'
  gloss-annotation pattern (much/get/next/across/front/excuse/miss/take/little/over/by/wake/...) — these
  leak ONLY where a template renders the gloss as a bare prompt / MC-answer; per-template audit needed
  (strip only if collision-free, else narrow the template — fa-en a1_03 precedent).

## ⭐ Native review — BATCH 4 (2026-07-28, ALL 4 REPORTED): fa-en a1_09-13, prs-en a1_11-15, nl-en a1_10-14, en-nl a1_11-15

**KEY RUNTIME FACT (en-nl reviewer, grep-confirmed):** `feedback_frame` is NOT read by
`generate_batch`/`generate_checkpoint`/`build_prompt` and is absent from `PracticeItemOut`/
`PracticeAnswerOut` — so ALL feedback_frame defects are content-correctness/source hygiene, NOT live
learner-facing bugs today (may surface on other/future surfaces). By contrast `frame.language_code`
(the PROMPT) IS live. Prioritize accordingly.

**DONE this session (all committed, gated):**
- **nl-en a1_10-14 feedback_frame** (64edd7b4): false-provenance ('uit deze les/dit gesprek/dit
  bericht' on wide untagged pools → 'Het juiste antwoord is {item}.'), stale match counts
  (twee→zes/vijf), false specific-facts (Daniel/forecast/label → self-ref/hedged/category). INERT
  per above but source now truthful.
- **en-nl a1_15** (434f6669): 6 MC/listen swapped *travel_noun→*travel_noun_pure (kills the
  Kaartje/kaartje + Perron/perron reworded-capital ambiguity the backend casefold can't reach);
  travel_noun_pure verified 6 unit15-scoped (no DEAD). **LIVE.**
- **en-nl a1_12** (434f6669): translate.001 + reverse_translate.002 had frame.language_code:nl while
  rendering english_gloss → aligned to language_code:en + 'Translate into Dutch.' text_block. **LIVE.**
- **prs-en a1_12** (منجم→متوسط, earlier commit): 'astronomer' wrongly used for size 'medium' 23×
  incl. 4 graded fields; aligned to the already-fixed lexeme. **LIVE (overlay).**
- **fa-en a1_09** (4b42e8de): write_restaurant instruction register-mix (formal خودتان/نپخته‌اید in
  a colloquial-pinned overlay) → colloquialized. **LIVE (overlay).**

**★ CONSOLIDATED en-nl/prs-en/fa-en BACKFILL WAVE — QUEUED (deploy-effect; touch each backfill_*.py
once; VERIFY unit-scope per token — see the weekday DEAD trap below):**
1. **Leaked-annotation glosses (strip the English parenthetical that leaks the answer in bare
   translate / MC-answer usage):**
   - fa-en (backfill_lexemes_fa_en.py EN_TARGET_TO_FA_GLOSS): `get`="رسیدن (در get to)"→"رسیدن",
     `can't`="نمی‌توانی/نمی‌تواند (منفیِ can)"→drop parenthetical (unit10 verb_gloss.004 MC-answer leak,
     MAJOR). NOTE the annotation is HELPFUL as a translation-PROMPT hint (turn_translate.003) — so
     the clean fix is to narrow verb_gloss.004's pool, not globally strip, OR accept the prompt-hint
     tradeoff.
   - prs-en (backfill_lexemes_prs_en.py): `well`="خوب (در hear well)"→"خوب" (unit14 desc_translate.004
     100%/sole-prompt leak HIGH + 2 MC leaks); `credit`="اعتباری (در credit card)"→"اعتباری",
     `debit`="بانکی؛ مستقیم (در debit card)"→"بانکی؛ مستقیم" (unit15 card_type_translate 100% leak HIGH
     + payment_translate 50% + total_translate 29%).
   - **CAUTION (learned fa-en a1_03):** stripping a parenthetical can REINTRODUCE a gloss-collision
     ("well"→"خوب" may collide with "good"→"خوب" if both are in desc_pool). Verify each token's pool
     for a same-gloss sibling; if collision, narrow the template pool instead (the fa-en a1_03 noun-
     narrow pattern). card_type (credit/debit only, 2 members) is collision-free → safe to strip.
2. **_pure / narrow tags for reworded-capital + metalabel contamination (en-nl):**
   - unit13 `preference_item` (9: Fietsen/Koffie/Thee capitalized from unit33/06 + lowercase) →
     `preference_item_pure` (unit13-only). 5 MC/listen ambiguous + false-feedback.
   - unit14 `equal_adj` (3: Mooi interjection from unit08 + mooi/praktisch) → hold Mooi out
     (METALABELS-style). translate.001 underdetermined (Mooi/goed both satisfy "nice; good").
   - unit11 `accept_decline_noun` leaks `tijd` (unit04) → false feedback (inert). Classifier holdout.
   - **⚠ unit11 `weekday` (21 members incl. metalabels geen/het/is/krijgen + capitalized days):
     do NOT just swap to weekday_pure — VERIFIED weekday_pure has 0 unit11-scoped members (unit11's
     only OWN weekday is capitalized 'Vrijdag' from a sentence-initial teaching card), so the swap
     DEADs the 4 render_frame + 1 MC checkpoint templates.** This is the documented _pure trap. Real
     fix = NORMALIZE weekday token casing at the backfill (unit11's own weekday should be lowercase
     'vrijdag', not 'Vrijdag' — the token is extracted sentence-initial), then the pure swap is safe.
     Same weekday contamination affects the 4 render_frame templates (wrong mid-sentence capital in
     the graded answer, e.g. "Zullen we Vrijdag koffie drinken?") — LIVE, but the fix is deploy-effect.
3. **Re-anchor bare-POS pools to the unit generated tags (the 'off-theme in Endless Practice' class):**
   - prs-en unit14: noun_pool/verb_pool/desc_pool/mixed_pool/action_pool/misc_pool (untagged POS-only)
     → `prs_en_a1_unit14_words`+POS (13-member tag EXISTS; content_match.003 already did it as precedent).
     10/11 templates. VERIFY per-POS unit-scoped count ≥ floor before swapping (desc≈5, verb≈4, noun≈4).
   - fa-en unit10 (unit_verb/unit_noun untagged) + nl-en unit10/unit14 (direction_word/noun_word/
     all_word untagged): SAME class. For nl-en I already genericized the FALSE FEEDBACK (removes the
     graded-severity defect); the thematic re-anchor (fa_en_/nl_en_a1_unitNN_words) is the deploy-effect
     polish. Same per-POS DEAD-verification required.

**NATIVE-CONFIRM / JUDGMENT (escalate — Ramin or a native pass):**
- prs-en unit13: `sad`="خفه؛ غمگین" / `worried`="خفه؛ پریشان" share leading "خفه" → MC harder to
  distinguish (not a hard dup). Confirm خفه is safe shared, or drop from one.
- prs-en unit12: `shirt`="شرت" (vs شورت shorts/underwear) — confirm the loanword register.
- prs-en unit15: "pay by cash" vs "pay in cash" idiom (LOW).
- fa-en completeness gaps (false-NEGATIVE mis-grades — a correct 'and'-joined answer marked wrong):
  unit09 reply_location (accepts only "It's next to the park."; add "The bank is next to the park.");
  unit11/12/13 reply_as_X/speak_X accept only ONE join of a multi-part dialogue reproduction (units
  09/10 already got the 'and'-joined variant; 11/12/13 didn't). Best as a focused native-EN sweep
  adding accepted_answers variants (W5-style).

**POLICY (reinforced — 2nd reviewer flagged it):** fa-en pack feedback_frame formal register across
ALL 5 batch-4 packs too. STILL a policy call (pin is overlay-only; 116 formal/0 colloquial is uniform;
AND feedback_frame is inert at runtime per above) — do NOT autonomously sweep. See BATCH-3 entry.

**HOUSEKEEPING:** prs-en unit14 `content_pool` + unit15 `number_no_hundred` dead anchors (unused) —
remove for cleanliness when next editing those packs.

**CLEAN in batch 4 (flippable):** prs-en a1_11 only. All other 19 packs have ≥1 open finding above
(mostly the queued deploy-effect classes) → NOT flipped.

## ⭐ Native review — BATCH 3 (2026-07-27, ALL 4 REPORTED): next pre-recipe a1 band

fa-en a1_02/03/04/06/08, prs-en a1_06-10, nl-en a1_04/06/07/08/09, en-nl a1_06-10 (4 sonnet
reviewers, all completed & coordinator-reviewed). **FIXED + committed this batch:**
- **nl-en a1_07 menu_meaning.001** hard-coded "{item} - $3" for every item → bare "{item}" (wrong
  price for tea/soup/sandwich). Commit 76d519de.
- **prs-en a1_08 پونډ→پوند** (HIGH): the shopping overlay used Pashto/Urdu retroflex پونډ throughout
  (28×) instead of Dari پوند, incl. inside a graded distractor value the learner sees. Repo-wide
  replace in that overlay only; graded correct answers unaffected. Commit 359d85be.

**QUEUED fix-waves from batch 3 (none blocking; ranked by value):**

**★ en-nl `_distractor_values` casefold-dedup — DONE 2026-07-28 (PARTIAL fix, commit e4144c8e).**
Implemented casefold-dedup + answer-variant fold-out + lowercase-representative preference in
`backend/app/practice/service.py`, with `backend/tests/test_distractor_casefold.py` (DB-free unit
test) and an algorithm proof harness. **SCOPE CORRECTION (my earlier "kills the whole class corpus-
wide" was overstated):** casefold on the GLOSS only merges pairs whose glosses differ *only* by case
(apples/Apples, library/Library, straight ahead/Straight ahead — the produce pool fully, direction_
word's rechtdoor pair, place's library pair). It does NOT merge a pair whose capitalized variant also
has a *reworded* gloss (`ziekenhuis`→"the hospital" vs `Ziekenhuis`→"Hospital"; `route`→"the route"
vs `Route`→"Route"; `buurtkaart`→"the neighbourhood map" vs `BUURTKAART`→"NEIGHBOURHOOD MAP") — those
contaminated capitalized rows remain and are the content-side `_pure`/route_word wave's job (below).
**STILL OPEN from this item:** (a) run the backend INTEGRATION suite before merge — needs Postgres
(docker not installed here) — to confirm no seeded MC/listen template starves below the 3-option
floor after dedup; (b) a MORE COMPLETE backend fix would dedupe distractors by underlying *token*
identity (appels/Appels, ziekenhuis/Ziekenhuis, route/Route all share a token) rather than by gloss
string — that catches the reworded-gloss variants too, but needs the answer's lexeme (not just its
gloss string) threaded in, and MUST be verified against the integration suite; deferred until infra.

--- original write-up (kept for the root-cause detail) ---
Root cause found by the en-nl reviewer:
`_distractor_values()` in `backend/app/practice/service.py` (~lines 351–388; the dedup is the
`list(dict.fromkeys(options))` + `str(value) != answer` at ~:386) dedupes multiple_choice /
listen_select option lists by EXACT string equality only. Many semantic-tag pools contain the same
word twice as separate Lexeme rows — a lowercase form and a capitalized sentence-initial/label form
with different-cased glosses (`apples`/`Apples`, `library`/`Library`, `the route`/`Route`,
`buurtkaart`/`BUURTKAART`, `rechtdoor`/`Rechtdoor`). When the other case-variant survives into the
random 3-of-N distractor draw, the learner sees TWO options meaning the identical thing, only one
graded correct — a real "more than one defensible answer" violation reachable in live sessions.
Confirmed exposed: en-nl a1_07 (`produce`, 3 templates), a1_08 (`place`/`place_non_station`, 7
templates), a1_09 (`direction_word` + `route_map`, 9 templates). This is CROSS-DIRECTION — any dir
whose MC/listen templates read a tag with a lowercase/Capitalized lexeme pair is exposed the same
way. **Fix: dedupe candidate options by casefold (or drop same-token-different-case rows) before
sampling distractors.** CAUTIONS for whoever implements: (a) don't shrink a pool below the option
floor — if casefold-dedup drops the pool under the needed distractor count, fall back gracefully;
(b) dedupe on the DISPLAY value/gloss the learner sees, keeping the graded answer; (c) run the
backend test suite (look under `backend/` + `scripts/tests/`) — this is generation-time logic that
grading/checkpoint paths lean on. word_order/translation templates are UNAFFECTED (they don't call
`_distractor_values`). This is the elegant fix; the content-side alternative (add `_pure` exact-case
sibling tags for produce/place/direction_word/route + repoint every MC/listen template) is
deploy-effect and touches ~19 templates — only worth it if the backend fix is rejected.

**en-nl a1_09 `route_word`/`route_map` blanket-tag contamination (same class as batch-2 item 5).**
The blanket per-lesson tagger (`lesson_categories["route_op_de_kaart"]="route_map"`,
backfill_lexemes_en_nl.py ~:2074) stamps `route_map` onto EVERY token in the route lesson, so the
real pool is 10 members incl. unit01/unit08 place nouns (station/bibliotheek/buurtkaart), not the 4
the 2026-07-24 "fix" claimed. Consequence: false "this unit's route/map word" feedback over place
nouns, plus more case-dups feeding the bug above. Fix: give `route_word` its own narrow literal-set
tag `{route, START, DOEL}` (like `place`/`direction_word` already do) instead of the blanket
category. Deploy-effect. NOTE the 2026-07-24 route_word re-anchor is itself defective — its
"verified 4 candidates" was wrong (real 10).

**en-nl a1_08 `voor` stale/wrong-sense gloss (MEDIUM).** lesson03.translate.004 draws `voor` from
the `position` preset; `NL_GLOSSES["voor"]` = "for; about" (canonical unit01 purpose-sense), but
this lesson drills the POSITIONAL sense "in front of" (its own overlay note flags the homograph).
Learner sees "Translate: for; about" inside an achter/voor location lesson — defensible but
wrong-sense. Fix: hardcode this template's slot to `{naast, tegenover, achter}` OR give `voor` a
position-specific gloss override. NOTE (2026-07-28): a pure pack-side slot-narrow is NOT available —
`lexeme_matches` filters only by language/POS/agreement-tags, not by token, so you cannot hardcode
`{naast, tegenover, achter}` in the slot. The fix needs a new `position_unambiguous` semantic tag on
naast/tegenover/achter (drop voor) in backfill_lexemes_en_nl.py + repoint translate.004, OR a
voor position-sense gloss override. Either way DEPLOY-EFFECT — fold into the consolidated en-nl
backfill wave below (route_word narrow-tag + `_pure` reworded-variant tags + food_item_orderable),
ideally after batch-4's en-nl findings land so the backfill file is touched once.

**en-nl a1_09 lesson06.translate.003 "Ga links."/"Ga rechts." (LOW-MEDIUM, native confirm).** The
`direction_word` slot includes bare links/rechts, but every attested Dutch direction-command in the
course pairs Ga/Sla only with -af forms or rechtdoor ("Ga rechtdoor.", "Sla linksaf."). "Ga links."
is unattested (grep = 0 hits) and reads awkward. Confirm with a native speaker or narrow slot to
`{linksaf, rechtsaf, rechtdoor}`. (en-nl a1_06 + a1_10 CLEAN.)

**fa-en a1_03 "much" leaked-annotation-gloss (CRITICAL) — DONE 2026-07-28 (commit 1910f052).**
Narrowed lesson3_word (used only by vocab_translate.006) to part_of_speech: noun, dropping the adverb
'much' (gloss «چقدر (در how much)» leaked the answer) and the adjective 'old' (verbose author-note
gloss); 5 clean noun members remain. Original write-up below.
lesson03.vocab_translate.006 is a bare
`{item}` frame rendering `english_gloss` over the `lesson3_word` union; the course gloss for "much"
is «چقدر (در how much)» — so the Farsi PROMPT literally embeds the English answer "how much", while
grading accepts ONLY the exact string "much" (a learner typing "how much" is marked wrong). Same
annotation-bleed for "old"→«سال قدمت‌داشتن (در بیان سن یا قدمت)» and "dollars"→«دلار (جمع)». Fix:
exclude much/old/dollars from this template's pool (or accept "how much"/"how" alternates) AND give
any sole-frame-rendered slot a CLEAN display gloss, not the parenthetical authoring-note gloss.
Deploy-effect if fixed via backfill gloss; pack-side if the slot pool is narrowed. Pool analysis
needed — mixed POS (adv/adj/noun), so no clean POS-narrow.

**fa-en PACK feedback_frame register — RAMIN POLICY DECISION (2026-07-28: downgraded from the
reviewer's "MAJOR violation"; do NOT autonomously sweep).** The batch-3 reviewer flagged fa-en pack
feedback_frames as formal (کنید/می‌کند/می‌شود) vs the colloquial overlays, citing the CLAUDE.md
register pin. BUT I verified: (a) the pin is explicitly the **fa-en OVERLAY lane** ("fa-en overlay
lane: colloquial spoken Persian", CLAUDE.md §"Per-lane register pins") — it does NOT mention practice
packs; a sibling pin even keeps **fa.json UI chrome FORMAL**, showing formal learner-facing text is a
deliberate surface elsewhere. (b) fa-en pack feedback is **uniformly formal across ALL 31 fa-en a1
packs: 116 formal-marker feedback lines, 0 colloquial** — a consistent authored convention, not
drift. So converting 116 lines would impose an *undocumented* policy on a uniform surface, and could
be wrong if formal instructional feedback is intended (mirroring the fa.json chrome). **DECISION
NEEDED:** should fa-en practice-pack feedback_frames converge to the colloquial overlay lane (for
learner-experience consistency) or stay formal (distinct instructional surface)? If "converge":
then a focused native sweep (W5-style, feedback_frame text only, graded values byte-identical) + a
NEW register pin in CLAUDE.md. If "stay formal": add a pin saying so, to stop future reviewers
re-flagging it. NOTE prs-en packs are already colloquial (matching their colloquial-Dari overlay
pin) — so this split is fa-en-specific.

**prs-en a1_10 place_listen.004 within-unit forward-reference (MEDIUM-HIGH) — DONE 2026-07-28
(commit d5ffa1d1).** Moved the listen_select from lesson02 to lesson04 (giving_directions_dialogue)
as place_listen.005, where the full direction_review pool (left/right/first/second/street) is in
scope. (Narrowing to turn_direction alone would starve the listen_select below the 3-option floor →
DEAD, which is why the pack originally re-pointed it.) unit-scope unchanged (0 DEAD).

**food_item_orderable wave (nl-en a1_07 + prs-en a1_07).** "I'd like a {item}, please" / cafe_order
include "bread" (uncountable → "I'd like a bread, please"). Fix = a narrower `food_item_orderable`
tag excluding bread (mirrors food_item_non_sandwich), in the respective backfill_lexemes_*.py.
Deploy-effect. CHECK all X-en directions' a1_07 (shared realization).

**prs-en small backfill-gloss fixes (LOW, inert until re-backfill).** a1_06 "who" glossed «کیا»
(Urdu) should be Dari «کی»; a1_07 "cafe" glossed «کیفی» should be «کافه». Both are backfill gloss
overrides, deploy-effect, no runtime effect today. (prs-en a1_09 CLEAN.)

**Honest-thin / benign / soft (NO action needed — documented for completeness):**
- fa-en a1_04 month_pair.003 (5 pairs, genuine 5-month ceiling) + a1_06 family_pair.003 (4 pairs,
  genuine 4-member family pool): disclosed FLOOR items, part of the assessed 116 below-floor. Leave.
- fa-en a1_08 audit-note inaccuracy: the pack's note claims "apples excluded" but apples (unit03,
  food_plural noun) IS a valid 8th candidate; benign (cumulative reuse is fine, bare {item} frames).
  Optionally correct the note.
- fa-en soft character-canon: unit02 casts Leila as a student/new-library-member; unit03/08 market
  dialogues implicitly cast her as the vendor. Not a hard contradiction; Ramin's call.
- shared realization a1_unit02 audio/text mismatch ("What's your name?" vs tested_text "What is your
  name") — pre-audio-recording, cross-direction (already noted in batch 2).

**CLEAN in batch 3 (flippable to reviewed):** nl-en a1_04/06/08/09; en-nl a1_06/a1_10; prs-en a1_09.
(Packs with an open finding above are NOT flipped yet.)

## ⭐ Native review — BATCH 2 (2026-07-27): 4 dirs' pre-recipe a1 reviewed; 1 CRITICAL fixed, rest = waves

Batch 2 = 4 fresh-context sonnet reviewers over the pre-recipe a1 band of the 4 launch directions not
in batch 1: fa-en a1_01/05/07/14/17, prs-en a1_01-05, nl-en a1_01/02/03/05/16, en-nl a1_01-05 (20
packs). Reviewers cross-checked against the English/Dutch realizations + L1 overlays + live backfill
pools + the real grading code. **FIXED this session (commit for nl-en/prs-en a1_03):**
- **CRITICAL plural-number agreement** (nl-en a1_03 "one", prs-en a1_03 "hundred"): plural-noun
  render frames drew a number that breaks agreement ("I have one dollars", "I'm hundred years old")
  as the GRADED answer. Repointed both to `count_plural_no_hundred`; nl-en's two singleton-pinned
  volume_fills singularized. DONE.

**REMAINING batch-2 findings — QUEUED as fix-waves (none fixed yet; several systemic/deploy-effect):**
1. **"I'm bad" / "Good day" untaught-in-bare-frame (CRITICAL/MAJOR, 4 directions).** `variety_wellbeing_
   order` + its volume_fill (hard-pinned to "bad") render "I'm bad." (never taught; the unit teaches
   "Not bad, thanks."); `variety_time_order` renders "Good day" (dated/untaught). Reachable in
   fa-en/nl-en/prs-en a1_01 (+ en-nl analog). Fix: exclude bad/day from these bare-frame pools and
   re-pin/retire the deterministic volume_fill singletons.
2. **fa-en OVERLAY register violation (MAJOR, systemic).** fa-en a1_01/05/07/14 overlays use FORMAL
   written Persian (کنید, می‌شود) in instruction/feedback/note strings; the pin is colloquial spoken
   Persian (کنین, می‌شه). a1_17 is the compliant control. 13–24 formal hits/pack. Fix: colloquial
   conversion sweep over the early fa-en overlays (likely all a1, not just these 4).
3. **fa-en a1_07 stale price overlay (CRITICAL, realization/overlay desync).** The realization fixed
   a coffee+sandwich total $6→$9 but the fa-en overlay still says «شش دلار / six dollars» in
   teach.thats_x_dollars, teach.closing_price, and exercise02.listen_price (graded answer + feedback
   both wrong). Fix: update those 3 overlay entries to «نه دلار / nine dollars». Classic
   realization+overlay-pairing footgun — CHECK the other directions' unit07 overlays for the same.
4. **fa-en a1_01 gloss-collision translations (CRITICAL).** good/fine/okay all gloss «خوب»;
   wellbeing_translate.004, politeness_translate.003 (post-union), practice_translate.905 (POS-only)
   show only «خوب» and grade one specific English word → underdetermined. Fix: exclude collision
   members from translation-type consumers (recipe defect 1.29 class).
5. **en-nl blanket-tag contamination (CRITICAL, corpus-wide) — METALABEL PART FIXED 2026-07-27.**
   backfill_lexemes_en_nl.py now holds the grammar-note metalabels (eenheid/tiental/behalve/hoeveel/
   hoofdletter/dag/dagen/maanden/jaar) out of the number/weekday/month/ordinal_number blanket
   category (verified: those pools are metalabel-free; real numbers/weekdays/months intact; ledger
   unchanged, 0 DEAD). This removes the CHECKPOINT-scope "hoofdletter is the month you heard" class.
   STILL OPEN (needs the `_pure`-tag + repoint wave, NOT an exclusion):
   (a) the weekday/month/number blanket also tags grammar-note SENTENCE words beyond the curated
   metalabel set (e.g. "Dagen krijgen normaal geen hoofdletter" → geen/het/krijgen/normaal still
   carry "weekday"); (b) the CAPITALIZED sentence-initial variants (Maandag/Twaalf/Jij…) still
   casefold-leak. **LEARNING 2026-07-27: do NOT fix these by excluding caps / blanket-skipping —
   tried it, it caused 7 DEAD (a1_11/a1_19/b1_09), because some units introduce their OWN
   weekday/number tokens in capitalized/sentence form, so those ARE the unit's only candidates;
   excluding them empties the unit-scope checkpoint pool.** The correct fix is the reviewer's:
   add exact-case `_pure` tags (weekday_pure exists; add number_pure/month_pure/hour_number_pure/
   informal_address_pure = real lowercase members only) and repoint ONLY the mid-sentence-frame
   templates to them, leaving "weekday"/"number"/… (both cases, all lesson tokens) for unit-scope
   satisfiability. Then narrow the affected translate/order/listen templates. Deploy-effect.
6. **prs-en overlay Dari spelling (MAJOR, needs native confirm).** a1_04 overlay glosses "month" as
   «مهی» 26× (standard «ماه» appears 393× elsewhere — almost certainly a dropped-vowel typo);
   a1_03 glosses "number" as «شمیر» in titles/instructions (standard «شماره»/«عدد» dominate — LESS
   certain, could be a variant). Fix: مهی→ماه is safe; شمیر needs a Dari reference / Ramin's call
   before touching. (These are overlay TEACHING glosses, not practice-grading data.)
7. **MINORs:** prs-en a1_05 "afternoon" glossed «بعد از ظهر» vs the course convention «بعد از چاشت»
   (unit01); nl-en a1_16 + en-nl a1_04 "this unit's own word" feedback over untagged course pools
   (same false-attribution class fixed in batch 1 — anchor to unit tags); shared realization
   a1_unit02 audio/text mismatch ("What's your name?" contracted vs "What is your name" tested_text —
   cross-direction, pre-audio-recording fix).

**CLEAN in batch 2 (no open findings):** fa-en a1_17, nl-en a1_02, nl-en a1_05 (post-rebuild),
en-nl a1_05, prs-en a1_02 — flippable to reviewed. Everything else in batch 2 has an open finding above.

### en-nl blanket-tag contamination (detail)

**en-nl blanket-tag contamination (CRITICAL, corpus-wide).** `backfill_lexemes_en_nl.py` tags every
introduced_token in a lesson with that lesson's category tag, so grammar-note METALABELS and
CAPITALIZED sentence-initial variants leak into the `number`/`weekday`/`month`/`hour_number`/
`informal_address` pools:
- Metalabels (in-unit → **checkpoint** mis-grade): `eenheid` "unit", `tiental` "multiple of ten",
  `behalve` "except", `Hoeveel` "how many" in `number` (unit02); `hoofdletter` "capital letter",
  `dag`/`Dagen` in `weekday` and `hoofdletter`/`Maanden`/`jaar` in `month` (unit03). A drilled
  "eenheid is the number you heard" / "hoofdletter is this month" is nonsense shown as ground truth.
- Capitalized variants (later-unit → **course-scope** Endless-Practice only): `Nul`/`Twaalf`/`Twee`/
  `Jij`/`Je`/`Donderdag` render a wrong mid-sentence capital baked into the render_frame answer key
  (`Het is Twaalf uur.`, `Ben Jij nieuw hier?`).
The backfill already has the fix PATTERN (`weekday_pure` exact-case tag, used by matching_pairs; a
non-casefold guard on `possessive_flexible`) but it was never extended to number/month/hour_number/
informal_address or to the translate/order/listen templates that still read the contaminated tags.
**Fix wave (queued):** (a) exclude the metalabels from the category tags in backfill_lexemes_en_nl.py
(METALABEL set, like the Persian METALANGUAGE_TOKENS); (b) add `_pure` exact-case tags for
number/month/hour_number/informal_address; (c) repoint the affected en-nl templates (all units, not
just a1_01-05) off the contaminated tags. Deploy-effect (runtime pools come from the DB re-backfill).
fa-en/prs-en/nl-en batch-2 reviewers still running; findings will fold in here.

## ⭐ Overnight deep-review + fix waves (2026-07-23 night) — READ THIS FIRST

**Headline / ship-readiness verdict:** the checkpoint publish-gate only ever
tested checkpoint *availability* (are there ≥12 items?), never grading
*correctness*. A fresh-context adversarial re-review of **every launch
realization + overlay** (14 reviewers, q_01..q_14) found the launch content had
**multiple systemic, compiler-invisible defect classes** — real mis-grading a
learner would hit. **Conclusion: the launch content was NOT ship-ready as it
stood.** Most of it is now fixed + committed; a few classes are deferred (need
your call or a careful paired pass). I recommend a **content-correctness gate**
(not just the availability gate) before any beta invite.

**Committed tonight on `fix/launch-gate-content-review-wave1` (unpushed, yours to review/merge):**
- **`ae9e0253` — launch fix wave (147 files).** All 21 launch manifest groups
  validate AND compile clean (0 errors).
- **`10465892` — non-launch fix wave (239 files, de/fr/ru/ar/es/ro/pl/hi).** All
  25 non-launch groups clean. (`it` lane commits separately once its worker ends.)

**Defect classes found + FIXED (verified real, each checked against the paired
overlay/grading before editing):**
1. **Prompt-shows-answer** — recognize_*/choose_* items displayed the target word
   in the prompt AND as the only correct option. en-fa a1 (18), en-prs a1 (23);
   detector-swept the rest of a1 → 0 remaining.
2. **Missing overlay teaching glosses** (compiler-invisible — learner saw target
   script with no translation): a systematic authoring gap. Scan found 20 launch
   files / 209 entries; all filled (fa-en a1_50-57+a2_26, nl-en/prs-en a2_26,
   en-fa b1, en-prs a1_20/23/37/38). Non-launch pl(14)+hi(29) too.
3. **§12 two-clause grading gap** — a correct period-separated / and-joined answer
   graded WRONG (only comma-join accepted). Additive variants added: en-prs
   a1_36-61, prs-en b1_01-06 + b2_01-08.
4. **prs-en Dari formal-register leak** (Iranian/formal endings in colloquial-Dari
   learner text) a1_62-68 + a2_35-38.
5. **ze/zij** interchangeable-pronoun mis-grade (en-nl a2_73-77).
6. **dinner→چاشت** mistranslation (prs-en a1_16) — 3rd recurrence of this class.
7. Fact contradictions, trait-reassignment (Leila eyes green→blue, graded),
   phantom introduced_tokens, register (خونه), prices, fabricated distractors,
   and **false review metadata** (status:reviewed while the file's own notes say
   the review never ran) across many files.

**A reviewer false-positive I caught + did NOT act on:** q_05 flagged en-prs a1_36
هستم as an "Iranian" register bug. It is NOT — DARI_REGISTER_REPAIR.md scopes the
هستم→استم fix to the *prs-en colloquial* lane; **en-prs is formal written Dari
where است/هستم is correct** (doc's own carve-out + CONTENT_DEFECT_REGISTRY §1.28).
Left unchanged. Flagging so the repair-doc scope stays clear.

**DEFERRED — need your call or a dedicated careful pass (NOT done tonight):**
- **matching_pairs lesson01 forward-reference** in the *shared* `realizations/en`
  (units ~02-24) → fans to fa-en/nl-en/prs-en/de-en overlays. Low severity (both
  sides shown in a match), but the fix is the realization + all-3-overlay mirror
  cascade that bit us before (the fwdfix revert). Wants one careful paired pass.
- a2_25-35 matching_pairs padding + "sequencing" jargon (same shared-corpus cascade).
- **Residual register** in prs-en a1_62-68/a2_35-38 `example_gloss`/`grammar_note`/
  dialogue-card fields (P1 fixed the reading/instruction/feedback fields; these
  lower-severity same-pattern fields need a field-extension sweep). + en-prs
  b1_01/06-11 overlay metadata still stale (minor).
- **PRODUCT decisions (yours):** (a) char-name romanization vs native-script in
  en-prs A2 English-facing fields (deliberate A2 convention? — corpus-wide);
  (b) b1_01-06 "reply in role" instructions give zero content guidance → currently
  rote-recall only; (c) the ~8% structurally-thin checkpoint units (unchanged from
  the prior gate ceiling item below).

---

## ⭐⭐ Practice-pack RE-AUTHORING done (2026-07-24) — dead-template family fixed (692 → 1)

Followed up the diagnosis below by actually **fixing the pre-recipe dead-template defect**.
A fan-out re-authored every pack that had a checkpoint-scope-dead template, each agent
self-verifying with a new unit-scope validator, and I gate+committed per direction.

**Result (measured by `scripts/_practice_unit_scope_check.py`): 692 dead template-slots → 1.**
~130 packs across all 6 launch directions re-authored. Fix pattern: re-anchor each dead
slot to the unit's OWN vocabulary (a unit-native semantic tag or POS-only pool), drop only
the genuinely-unfillable (keeping the checkpoint viable), widen below-floor matching_pairs.
All committed on `fix/launch-gate-content-review-wave1` (unpushed). Every re-authored pack
was flipped to `review.status: unreviewed` — they need a fresh-context native pass before ship.

**New tooling committed (all zero-false-positive, gate-able):**
- `scripts/_practice_unit_scope_check.py` — the missing DO-NOT #2 check: dead templates
  (per distinct-relation group), MC/matching floors, AND ≥3-live-templates-per-tier (§8).
- `scripts/_phantom_introduced_tokens_check.py` — untaught-in-production tokens.
- `scripts/_practice_self_reference_check.py` — "ten past {ten}" / invariant-answer frames.
- `scripts/backfill_lexemes*.py` — Codex fixed the cross-unit homograph GLOSS collisions
  (Family-2): unambiguous ones corrected in-place, polysemous ones given per-(unit,token)
  overrides; verified functionally (small→klein, manager→leidinggevende, must→باید, …).

**Residual follow-ups (NOT blocking; the dead-template family is fixed):**
- ~~**1 dead template left:** en-nl a1_29 lesson05.match.001 — freq_adverb group 4 slots / 2
  members; needs a 4→2 slot trim.~~ **DONE (already trimmed in a prior wave; verified 2026-07-27:
  the freq_adverb distinct group is [seventh, eighth] = 2 slots against its 2 unit-native members
  nooit/soms; corpus ledger 0 DEAD confirms).**
- ~~**Tier-thinness (335 tier-short lines, mostly PRE-EXISTING):** many packs — especially the
  pre-recipe en-prs/prs-en a1_26–37 range — have <3 live templates in a tier. Predates the
  re-auth (accepted at each pack's original review); the re-auth made a few acute (en-prs a1_34
  recycles the same 3 words across all tiers). Now gate-able via the validator's tier check.~~
  **FIXED 2026-07-25 (polish wave 2):** ~48 per-pack agents across all 6 directions (commits
  0a15fd0e en-nl, 38f99397 en-prs, a4cb5f81 prs-en, dd172bb2 en-fa, b7c40bf4 fa-en, cf8ed1cf
  nl-en; 240 pack files, ~13.6k insertions). Tier-short 335 → **4** — the residue is documented
  honest-thin (en-prs a1_34 production + a1_42 recognition, prs-en a1_43 structured, nl-en a1_43
  structured: unit vocab genuinely exhausted). The same wave converted POS-only matching_pairs
  to semantic unions wherever the unit's lexemes carry tags. Every direction gated: 0 errors,
  0 self-reference hits, 0 DEAD, 0 Dari-register findings.
- **NEW SYSTEMIC (from the wave, needs a backfill-lane pass): X-en semantic-tag deserts.** The
  backfill scripts carry ~zero `agreement_tags.semantic` for prs-en a1_43–68 + all B1/B2,
  fa-en/nl-en a1_43+, en-fa a1_31–36 + b1_06/b1_11, en-prs a1_06/25/26/36. In those units the
  POS-only matching_pairs CANNOT be unioned pack-side (agents measured max reachable pools,
  documented per pack in review.notes) — they stay POS-only (§3.1c-legal; cost = off-theme pairs
  in Endless Practice only). Durable fix = semantic-tag backfill pass over those bands, then a
  small union re-pass; would also unlock the 4 honest-thin tiers and many of the 144 remaining
  below-floor matchers. **DONE 2026-07-26 for the X-en directions:** generated tags (05af7ace)
  + wave-3 union re-pass (09e324d7 prs-en 64 packs, 7d0f8a46 fa-en 18, be6a1955 nl-en 19) —
  every X-en POS-only matcher now unit-scoped, ledger at 0 DEAD / 2 tier-short (both Dari-side
  honest-thins: en-prs a1_34 production, a1_42 recognition) / 116 below-floor. ~~STILL OPEN:
  the Persian-side deserts (en-fa a1_31-36 + b1_06/11, en-prs a1_06/25/26/36) — auto-tagging
  there needs a Persian-aware metalanguage guard in backfill_lexemes{,_en_prs}.py.~~
  **DONE 2026-07-26 (wave 4, Persian-TARGET side):** ported the generated-tag mechanism to
  `backfill_lexemes.py` (en_fa_) + `backfill_lexemes_en_prs.py` (en_prs_) with the Persian-aware
  metalanguage guard (en-fa empty — an FA_GLOSSES audit found ZERO Farsi grammar-term lexemes;
  en-prs excludes only فعل/فاعل; ZWNJ/combining-diacritic-aware alpha-guard) — commit 77c50674,
  proven additive (spec counts + unit-scope ledger byte-identical). Union re-pass committed
  54d108f8 (en-fa, 20 matchers across 16 packs: a1_31-36, a2_12/13/14/16, b1_01/02/03/04/06/11 —
  a full-direction sweep, not just the named subset) + 9587f5ec (en-prs, a1_06/25/26/36). a1_32
  used a lesson tag (لباس/لباس‌ها collision guard); a1_06 direction_pair.004 trimmed 10→8 to fit
  the tagged pool + its shared review_choose.001 also scoped; a1_26 de-aliased off the shared
  unit_noun_pool. Gates all green per direction (0 errors / 0 self-ref / 0 Dari / 0 DEAD, ledger
  unchanged — the win is Endless-Practice coherence, not a unit-scope metric). The 2 tier-shorts
  (a1_34/a1_42) assessed and LEFT as honest-thins: each recombination unit has only ~3 own content
  tokens, so a 3rd tier template would be padding, not vocabulary a tag can supply. Packs stay
  review.status: unreviewed pending the native pass. ~~Small concrete backfill bugs found en route: en-prs a2_12/13/14
  gloss-baked-into-token phrases; fa-en `walks` gloss comma; fa-en a1_31 His/Her frame.~~
  **FIXED 2026-07-25** (commit cb9e4ef9). STILL OPEN from the same class: **en-fa's 42
  label-phrase junk lexemes** (units 06/13/16/18/19/23/31-36 + a2 11/15/16/18 — tokens like
  «امروز (today) / سال (year) / …» with English glosses/slashes baked in, all tagged only
  `reviewed_phrase`; they can surface as junk tiles in the new course-scope phrase word_orders).
  The emission guard already exists but is deliberately scoped (see the `_label_guarded` comment
  in `backfill_lexemes.py` ~line 3259): suppressing them BEFORE deleting the persisted rows
  verifiably breaks the practice import (102 errors on a dev-DB copy). Paired deploy-side task:
  (1) delete those 42 Lexeme rows in the DB, (2) widen `_label_guarded` to all units, (3) rerun
  backfill + practice import. Needs a live dev DB to verify — same procedure the guard's author
  used.
- ~~**Duplicate `volume_match`/`volume_translate` templates (units 31–40, all directions):** the
  2026-07-11 authoring pass emitted literal-duplicate matching/translation templates (and a
  degraded bare-`{word}` feedback_frame on the translation ones).~~ **DONE (resolved by the
  polish-wave re-authoring; verified 2026-07-27 across all 6 directions' units 31–40: 0
  literal-duplicate template pairs and 0 bare-placeholder feedback_frames remain. The surviving
  `volume_*` templates are intentional second-review sets, each carrying a distinguishing
  `text_blocks` header, not duplicates.)**
- **Below-floor matchers (116, the "optional wave") — ASSESSED 2026-07-27, intentionally NOT
  forced.** Below-floor = a matching_pairs with <6 pairs; it is a recipe *preference*, not a
  gate (the publish/availability gate is maxed at ~92% and unaffected; 4-5-pair matchers generate
  and grade fine). Programmatic capacity analysis (current-slots vs same-constraint unit-scoped
  pool): only **6** of the 116 under-use a ≥6 same-theme pool; the other **110 are pool-limited**
  — their theme has <6 unit-scoped tokens, so raising them needs an off-theme union, which
  re-introduces exactly the Endless-Practice incoherence wave 3/4 removed ("a wrong union is worse
  than the status quo"). The 6 "raisable" are all en-nl a2 units (27/28/74/75/77) and are marginal
  or net-negative: a2_75's two matchers share one 6-token pool (raising both → duplicate matchers);
  a2_28's pool is exactly 6 (raising → zero-slack exact-fit). Conclusion: the 110 stay honest-thin;
  the ~6 are low-value churn on non-launch-gating units. If Ramin wants the floor enforced anyway,
  the 3 with real slack (a2_27 pool 7, a2_74 pool 8, a2_77 pool 7) are the clean candidates.
- ~~**`proper_noun` self-gloss (§6.1):** en-prs a1_02 name_gloss now has 3/4 name-gloss options
  after a re-auth widening ("spot the non-name" instead of translation). Narrow that one slot.~~
  **FIXED 2026-07-24** (commit c2e6caba): re-anchored to noun-only name_word∪relationship_word∪title
  (5 distinct real glosses); names stay translation-only.
- ~~**Course-scope grammaticality:** en-prs a1_28 pet-frame `{animal_word}` is fine at checkpoint
  (unit pool = cat/dog/fish/bird) but at Endless-Practice course scope pulls zoo animals →
  "the lion is my pet." Reframe or subset the tag.~~ **FIXED 2026-07-24** (commit c2e6caba):
  new `pet_animal` subset tag; both a1_28 claim frames pinned to it (needs lexeme re-backfill
  on deploy, same run as confirm_word).
- ~~**POS-only matching_pairs at course scope (systemic re-auth trade-off):** many re-authored
  matching_pairs were fixed by dropping the semantic tag to a bare `part_of_speech` pool. That's
  correct at CHECKPOINT scope (unit pool = the intended few tokens), but Endless Practice serves
  matching at COURSE scope, where POS-only matches the whole level's adjectives/adverbs/nouns
  (e.g. en-prs a1_25 emotion_pair → 163 off-theme tokens). Not a grading/checkpoint defect (the
  launch gate is fine); Endless-Practice coherence only. Follow-up: narrow those matching pools
  to a real semantic union (keep POS-only for word_order / bare-translation, its stated safe case).~~
  **ADDRESSED 2026-07-25 (polish wave 2, same commits as the tier-thinness fix above):** every
  flagged matcher whose unit carries semantic tags is now a real union; the rest are measured,
  documented honest-leaves blocked on the "semantic-tag deserts" backfill item above (each pack's
  review.notes records the exact max-reachable pool so future waves don't re-litigate).
- ~~**Invariant-answer frames (pre-recipe):** en-fa a1_01–04 word_order frames with no `{slot}`
  placeholder (self-ref scanner flags them) — SRS mis-attribution; give a real placeholder.~~
  **FIXED 2026-07-24:** all 5 scanner hits (the 4 en-fa + nl-en b1_08 order.001 "as soon as"
  self-reference) re-slotted so the placeholder is real and every pool candidate is grammatical;
  a1_04 is now genuinely variable (بزرگه/شلوغه/کوچیکه). New single-member `confirm_word` tag on
  درسته in `backfill_lexemes.py` anchors a1_03 (needs the usual lexeme re-backfill on deploy).
  Scanner now reports 0 hits; en-fa + nl-en practice-validate clean; scope check still 0 DEAD.
- **Backfill bugs the agents logged (route to a backfill pass):** tokens with trailing
  punctuation baked in (nl-en/prs-en/fa-en unit33: `work?`,`office.`) — DONE 2026-07-24 (earlier
  session); `hand`→idiom-fragment gloss (nl-en) + `گوش` gloss — DONE 2026-07-24 (Codex gloss2,
  commit 1bbe5f11); ~~`هستم` off-theme in some prs pools still open.~~ **DONE 2026-07-27:**
  هستم ("I am") is a register variant re-taught only in en-prs a1_unit36's cooking lesson, so the
  wave-4 generated tag pulled it into that unit's cooking_pair matcher. Held out at the source via
  `OFF_THEME_TOKENS` in backfill_lexemes_en_prs.py (a1_36 cooking pool 12→11, still ≥floor; the
  on-theme copulas in their own intro units stay taggable). Ledger unchanged; guard test added.

**DEFERRED — the real root cause, needs your call (a big change):** the backfill classifier
keys a lexeme to the FIRST unit that teaches a token, so a token re-taught in a later unit
contributes 0 to that unit's checkpoint pool (that's WHY the templates were dead). The re-auth
works around it pack-side. The permanent fix — register a unit-scoped lexeme in EACH teaching
unit — would balloon lexeme counts and shift every checkpoint pool + DB import, so I did NOT
do it autonomously. If done, the dropped templates could be restored. Your scope call.

---

## ⭐ Practice-pack quality (2026-07-23 night) — SYSTEMIC pre-recipe defect (needs your call on scope)

A fresh-context review of the practice packs (fan-out over ~450 of the 553) found a
clean, consistent, **date-driven quality split** that is invisible to the compiler:

- **Pre-recipe packs = DEFECTIVE.** Everything authored **2026-07-05→09** (roughly
  `a1_unit01–24` in ALL 6 launch directions, plus `fa/nl/prs-en a2_unit25–29` and
  `en-fa/en-prs a2_unit09–10`) is riddled with structural defects.
- **Post-recipe packs = CLEAN.** Everything authored **2026-07-22+** (after
  `PRACTICE_PACK_RECIPE.md` was written — `a1_unit25–72`, `a2_unit11–18/30–40`,
  all `b1_*`/`b2_*`) is clean or honestly self-flagged thin.

**Root cause (multiple independent reviewers agree):** the early lane verified slot
capacity at **course scope** (all units/levels pooled) but `generate_checkpoint()`
uses **unit scope** (only that unit's own lexemes). So a template whose slot reuses
a tag whose vocabulary was first taught in an *earlier* unit has **zero** unit-scoped
candidates → it silently never generates at checkpoint time (recipe §1.1 / DO-NOT #2).
The self-check the early packs cite (`scripts/_practice_slot_check.py`) checks the
whole-direction pool, not unit scope — which is why they all self-certified "verified"
while being dead. **This means the earlier "~92% checkpoint availability" gate number is
OPTIMISTIC for the pre-recipe units** — several are fully/mostly checkpoint-DEAD
(`fa-en a1_unit14 & a1_unit17` are already named in the recipe's own DO-NOT #2 as
guaranteed-409; `nl-en a1_05/16`, `en-prs a1_18`, `fa-en a1_05/14/17` generate ~0–2
live templates).

**Defect classes (all compiler-invisible):** (1) dead templates (earlier-unit vocab —
the big one); (2) matching_pairs below the 6-pair floor / more slots than pool; (3)
**invariant-answer templates** (en-fa a1_03/04) — frame has no `{slot}` placeholder, so
every render is identical and the learner is credited toward a lexeme never shown (an
actual SRS mis-grade); (4) **narration-gloss** (en-fa a2_10, en-prs a2_09/10) — a
`translation` shows a 3rd-person narrated gloss but requires the 1st/2nd-person direct
answer → a faithful translation grades WRONG; (5) self-reference / ungrammatical pool
members (`nl-en a1_05` "ten past ten", `fa-en a1_07` "a bread", `fa-en a1_15` "one
dollars", en-nl number pool `eenheid`/`tiental`, weekday `hoofdletter`); (6) thin +
byte-identical duplicate-template padding (en-fa a1_31–36, en-nl/nl-en a1_43–48).

**SECOND, separate defect family — cross-unit homograph gloss collisions (affects the
CLEAN post-recipe b1/b2 packs too, so arguably higher-priority):** the backfill lexeme
classifier assigns the WRONG sense's gloss to a homograph, and it ships as the correct
answer. Confirmed in nl-en: `small`→"kleine maat" (should be plain klein), `manager`→"de
beheerder" (should be boss), `express`→"spoedpost" (should be the verb "uiten"), `left`→
"links" (should be "liet weg"/verb), `checking`→"betaal-" (banking sense leaked into a
narrative unit), `texts`→"appt; schrijft" (garbled). This is a `backfill_lexemes_<dir>.py`
classifier bug (recipe §0.1 / defect 1.29), invisible to the compiler AND every validator,
and it very likely also affects fa-en/prs-en b1/b2 (same classifier approach). Fix = add
homograph sense-disambiguation to the classifier (Codex lane) or narrow the affected packs'
pools by POS/tag. These are actual wrong-answer mis-teaches in packs we'd otherwise ship.
**Confirmed in prs-en (Dari) too** (short→"قد کوتاه", sound→"آواز", position→"پُست", run→
"دویدن", past→a malformed placeholder shown as the answer), plus a related **confusable-
distractor** sub-class (two English words sharing one gloss: coworker/colleague=همکار,
employees/staff=کارمندان, from/of=از → matching-pairs ambiguity and a valid synonym graded
wrong). **Scope warning:** the prs-en reviewer's gloss audit was a spot-check (~40 of ~900
lexemes) with a **~1-in-3 hit rate** — so this is pervasive across the X-en whole-unit-pool
packs, not a handful. Root: shared `scripts/_en_target_lexeme_common.py` flat gloss dict.
(Also minor: 13 prs-en b1/b2 packs have an English matching_pairs feedback string that should
be Dari — a one-string fix.) Separately, the post-recipe **fa-en b1/b2 packs** have two
authoring-consistency quirks (not wrong-grading): `listen_select` uses `slot_text` (audio→spelling
dictation) instead of `slot_gloss` (meaning-recognition) in ~13 packs, and ~12 packs use a
content-free fill_in_blank carrier "Please remember this word: {item}." with no meaning hint —
worth normalizing in the same pass.

**My recommendation (your call — scoped project, NOT an emergency; the base
realization/overlay content is fixed + committed, which matters more):**
- **(a)** Re-author the ~pre-recipe packs (a1_01–24 × 6 dirs + a2_25–29/09–10) against
  the current recipe (post-recipe packs are the proven-clean template). ~150 packs; wants
  a careful per-unit capacity pass, so I did NOT blast it autonomously — greenlight the scale.
- **(b) Highest-leverage tooling fix:** add a validator that checks **unit-scope**
  satisfiability (the one missing check) so this class can't ship again, and fix
  `_practice_slot_check.py` to report unit scope. (validator/Codex lane.)
- **(c)** I fixed one urgent blocker tonight (below).

**Fixed tonight (committing separately):** `scripts/backfill_lexemes.py` was missing a
`FA_GLOSSES` entry for `خونه‌اش` ("his house") — a token that IS introduced+glossed in
`realizations/fa/a1_unit33`. Its absence raised `ValueError` inside `iter_specs()`, which
crashed `_practice_content_integrity_check.py` for the entire fa direction, silently
downgraded the fill_in_blank ambiguity HARD-gate to a soft warning, and would block any
fa lexeme backfill run. Added the gloss (sibling of خونه‌ی/خونه‌ت); verified the checker
now runs to completion (iter_specs loads 3838 fa specs) instead of crashing.

**Codex** is re-doing the phantom-introduced_tokens validator (first cut = 597 findings,
~all false positives — 'the'/'with'/names — REJECTED per the zero-FP bar; not committed).

Full per-pack findings: coordinator scratchpad `pack_findings.md`.

---

## Decisions taken autonomously (FYI — reverse if you disagree)

- **2026-07-23 — Repo moved out of iCloud by `mv`, not the `git clone` the
  handover prescribed.** Now at `~/dev/LingoSquared`; the old iCloud copy no
  longer exists (GitHub `origin/master` is the backup). Chose `mv` because it
  preserved the untracked `.env` secrets and `node_modules`, and there were
  zero half-materialized iCloud placeholders at the time. Verified with
  `git fsck` (clean), identical `git status`, 2530 tracked files.

- **2026-07-23 — Local dev-DB admin password self-generated.** The fresh dev
  DB needs an admin to exist before `sync_dev_db.sh` can log in, and
  `~/.lingo_admin_pw` was never synced from the old Mac. Rather than block on
  you, generated a random 24-char password into `~/.lingo_admin_pw` (600) and
  registered `admin@example.com` against the LOCAL dev DB only. This is a
  throwaway local credential; nothing live is affected. If you later AirDrop
  your real file it simply overwrites this.

- **2026-07-23 — Registered `docker-compose` as a Docker CLI plugin.** The
  Homebrew `docker` CLI ships without the compose plugin, so `docker compose`
  (space) — which every script and doc here uses — failed. Symlinked
  `/opt/homebrew/opt/docker-compose/bin/docker-compose` into
  `~/.docker/cli-plugins/`. Local-machine setup only, nothing in the repo.

## Review wave 1 (2026-07-23) — 179 launch-gate files, 15 fresh-context workers

Full raw findings + triage: coordinator scratchpad `findings.md` (will fold into
`docs/CONTENT_DEFECT_REGISTRY.md` §4). Headline results — ~32 files had findings,
**1 real critical**, several real major classes, and **6 false "criticals"
correctly dismissed** (a reviewer flagged bare-string `accepted_answers` as a
compiler crash; `compile_content.py:1440` handles both shapes — verified at source).

**Fix wave 1 status (2026-07-23): items 1–5 below FIXED + committed** on branch
`fix/launch-gate-content-review-wave1` (commit `762e1315`), all-green
(content/backend/frontend). NOT pushed, NOT merged to master — yours to review
and merge. Items 6–7 (char-name, native-pass minors) and the matching_pairs
forward-reference cluster + §12 gaps are still queued.

Real defects (most are systemic classes, not one-offs):
1. **CRITICAL — prs-en `a1_unit18`: "dinner" glossed چاشت** (= midday/lunch per §3;
   should be شام) throughout the unit. Sibling `a1_unit24` already fixed the same bug.
2. **fa A2 units 11-18: phantom `introduced_tokens`** hiding untaught verb
   conjugations that the final writing exercise then demands (+ formal-register
   می‌کند in units explicitly marked casual). 7 files, one authoring habit.
3. **matching_pairs forward-reference** — lesson-01 matching tests vocab taught
   only in later lessons of the same unit. ~9 files across prs-en/nl-en/fa-en/en.
4. **prs-en `b1_unit16`: English word "overwhelmed" left untranslated** in 5
   Dari learner-facing strings (incl. exercise instructions).
5. **prs-en `a1_unit13`: "sad" and "worried" share خفه** as lead gloss —
   distinguishable only by the English word in a listening item.
6. **§12 gap** — some 2-clause free-text answers accept only period-joined forms,
   grading the natural comma/and-joined form wrong (nl-en a1_46 + its realization,
   en-fa a2_13).
7. Minor/native-pass: char-name دانیل vs دانیال split; a few gloss typos; stale
   `review.status: reviewed` on files whose own notes say review still pending.

**3 validator candidates** (automate per the tiered-review policy, Codex lane):
(a) matching_pairs no forward-reference; (b) introduced_tokens declared-but-
untaught-then-produced; (c) §12 2-clause answers must include comma/and variants.

Decision you may want to weigh in on (NOT blocking — I'll pick a default):
char-name spelling — standardize on دانیل (matches the A2 units) across B1? I'll
apply that unless you say otherwise.

## Practice-pack wave (2026-07-23) — checkpoints 52.7% -> 91.9%

Committed on branch `fix/launch-gate-content-review-wave1` (`6c5b284e`): ~246
practice packs across all 6 launch directions, closing the only open
publish-gate item. Measured against the REAL generate_checkpoint():

| dir | working | dir | working |
|---|---|---|---|
| en-fa | 83/83 (100%) | fa-en | 91/106 (86%) |
| en-nl | 88/88 (100%) | nl-en | 91/106 (86%) |
| en-prs | 81/82 (99%) | prs-en | 91/106 (86%) |
| **overall** | **525/571 = 91.9%** (was 52.7%) | | |

Method: fan-out of ~30 fresh-context authoring workers, each pack compiler-
validated (0 errors) + integrity-checked, registered centrally, imported, and
the whole gate re-measured. Pipeline was proven on a 5-pack pilot first.

**Two follow-ups this created (NOT blocking, but needed before ship):**
1. **Packs are `status: unreviewed`.** They validate and move the gate, but
   launch-gate content needs the standard fresh-context review before ship
   (tiered-review policy). ~246 packs to review — the next big review fan-out.
2. **The remaining X->en gap (~15 units/direction, all at 86%) is lexeme-thin
   recombination units** (3-14 new tokens — a1_unit60, 62-68, etc.), which
   cannot fill a 12-item checkpoint regardless of pack quality. This is a
   `backfill_lexemes_{nl,fa,prs}_en.py` extension = **Codex lane**, not
   authoring. Each affected pack's review.notes names its thin lessons. Also
   the X->en backfills emit polluting English `source_gloss` pseudo-lexemes
   (known handover bug) — worth cleaning in the same backfill pass.

## Checkpoint gate is effectively MAXED at ~92% — needs a PRODUCT decision to go higher

Final measured gate: **526/571 = 92.1%** (en-fa 83/83, en-nl 88/88, en-prs 81/82;
fa-en 92/106, nl-en 91/106, prs-en 91/106). The Codex lexeme-backfill attempt to
unblock the thin X→en units **failed to move the number** (created 0 new lexemes,
only updated existing). Root cause, now definitive: the ~45 still-unavailable
units are late-A1 **recombination units** that by design introduce FEWER THAN 12
genuinely-new tokens, and the backfill dedup key `(level, token)` assigns a
recombined token to its FIRST unit, not the recombination unit — so no backfill
can give them 12 own-unit checkpoint items.

**This is a content-design reality, not a fixable bug.** To push past ~92% you'd
need one of these PRODUCT/PEDAGOGY decisions (your call):
- (a) let a recombination unit's checkpoint draw on CUMULATIVE (through-this-unit)
  vocabulary instead of only its own new tokens;
- (b) exempt recombination units from the checkpoint requirement;
- (c) lower the 12-item floor for units with <12 new tokens.
The Codex backfill (`scripts/backfill_lexemes_*.py`) is uncommitted in the tree —
it did usefully remove the known nl-en English-`source_gloss` pollution and caused
no regression, so it's worth keeping, but it did NOT achieve the thin-unit unblock.

## Review wave 2 (non-launch ar/de/fr/it/ru) — findings logged, deferred

~20 of 24 batches reviewed (read-only). All NON-LAUNCH, so deferred. Real
classes found (for a future non-launch fix pass): matching_pairs/distractor
forward-reference (corpus-wide, en-it/en-ru/fr — same class as the launch fix),
untaught-in-production (ar a2_25 تأکید), a realization/overlay desync in the
pre-existing en-de b2_54 files, wrong subjunctive glosses (en-it b1), and
pervasive stale `status: reviewed` metadata (de b1). Several "critical" reports
(`teach_` underscore, example_gloss shape) were VERIFIED as FALSE POSITIVES
(compile clean / realization matches). Full log in coordinator scratchpad.

## Owner-reserved items still needing you (not blocking local work)

- **`~/.ssh/id_ed25519` (+`.pub`)** — needed only to reach the live server
  `ramin@192.168.4.4` for deploys. AirDrop/scp when convenient.
- **`ADMIN_EMAILS` on live is still `admin@example.com`** — must become your
  real address before any external beta invite (first registrant under a
  listed email silently becomes admin; no email verification).
- **`backend/scripts/remove_demo_courses.sql` on the LIVE DB** — dry-run
  verified safe (4 demo courses matched, 165 real untouched). Live DB is a
  destructive op, so it needs you present. (Dev DB I can do alone.)

## Tooling/doc gaps found (candidate fixes — low priority)

- **2026-07-23 — Fresh-DB setup is missing a bootstrap step in the docs
  AND in `sync_dev_db.sh`.** On a brand-new dev DB, the content import
  rejects EVERY course with 422 "source_language/target_language is
  unsupported", because `content/service.py:validation_errors` checks the
  `languages` table and that table is empty until
  `python -m app.content.seed --no-demo-courses` (the `bootstrap()` fn) is
  run. Neither HANDOVER step 7 nor `sync_dev_db.sh` runs it — the runbook
  mentions it only in the live-deploy section. I ran it by hand and the sync
  now works. **Candidate fix:** have `sync_dev_db.sh` call bootstrap before
  the content phase (idempotent, create-missing-only), and add the step to
  HANDOVER. Also worth noting `docker compose up -d` does not apply Alembic
  migrations — a fresh DB needs `docker compose run --rm api alembic upgrade
  head` first (also undocumented in HANDOVER; I ran it by hand).
  Not blocking — local dev DB is populating now.

## Deferred / parked

_(none yet)_

## Systemic: bare-word translation over UNTAGGED (course-wide) pools — design decision

Pack-fix sweep found the duplicate-gloss mis-grading has two layers:
1. Concrete, fixed: proper_noun in slot pools (prs-en a1_43-61, 19 files, fixed);
   a few nl-en broad-union same-gloss pairs (also/too, paint/painting, etc.).
2. SYSTEMIC (needs your call): the prs-en/en-prs packs (no semantic tags in their
   backfill) use "whole-vocabulary review" templates whose translation/matching
   slots pool the ENTIRE course vocabulary with only a part_of_speech filter. That
   pool inevitably contains many same-gloss English tokens (good/fine/okay→خوب),
   so a bare-word translation can mis-grade at scale. This can't be fixed by
   narrowing one tag — it's how the untagged-direction recipe works. Options:
   (a) scope these templates to lesson-taught vocab only; (b) add semantic tags to
   the prs-en/en-prs backfills so slots can be narrowed; (c) accept it (matching
   shows both sides; only bare-word translation is exposed). Your design decision.
