# Ramin's review backlog

Things the autonomous coordinator (Claude) decided or deferred that Ramin may
want to review when he has a moment. **Nothing here is blocking** — it is a
queue, not a set of questions. Newest at top. The coordinator appends; Ramin
prunes.

Standing mandate (2026-07-23): Claude runs the build autonomously as
coordinator/architect/engineer with a subagent team; only genuinely blocking
or owner-reserved decisions interrupt Ramin. Everything else lands here.

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
- **`می‌ته` vs `می‌ده` pattern** (prs-en units 30/34/35/36-39) — possible Pashto contamination (ته is a
  Pashto postposition); reviewer's best guess is it should be می‌ده. Native confirm → global replace.

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
