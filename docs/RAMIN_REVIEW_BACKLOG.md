# Ramin's review backlog

Things the autonomous coordinator (Claude) decided or deferred that Ramin may
want to review when he has a moment. **Nothing here is blocking** — it is a
queue, not a set of questions. Newest at top. The coordinator appends; Ramin
prunes.

Standing mandate (2026-07-23): Claude runs the build autonomously as
coordinator/architect/engineer with a subagent team; only genuinely blocking
or owner-reserved decisions interrupt Ramin. Everything else lands here.

---

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
- **1 dead template left:** en-nl a1_29 lesson05.match.001 — a heterogeneous matching whose
  2nd group (freq_adverb) has 2 unit-native members for 4 slots. Non-breaking (pack still
  generates from its other live templates); needs a 4→2 slot trim.
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
  below-floor matchers. Small concrete backfill bugs found en route: en-prs a2_12/13/14 have one
  phrase lexeme each with the ENGLISH GLOSS BAKED INTO THE TOKEN («از دو روز پیش (since two days
  ago)» etc. — self-answering card); fa-en unit32 `walks` gloss ends with a stray Arabic comma;
  fa-en a1_31 translate_sentence.005 maps genderless «چشماش» onto "Her eyes…" (His/Her
  underdetermined for typed answers).
- **Duplicate `volume_match`/`volume_translate` templates (units 31–40, all directions):** the
  2026-07-11 authoring pass emitted literal-duplicate matching/translation templates (and a
  degraded bare-`{word}` feedback_frame on the translation ones). Systemic; wants one cleanup pass.
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
  commit 1bbe5f11); `هستم` off-theme in some prs pools still open.

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
