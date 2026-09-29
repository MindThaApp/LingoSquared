# A2 rebuild plan — en-nl, en-fa, en-prs

**Status:** PROPOSAL for Ramin's review. Nothing here is authorized yet. This
document authors no content, edits no spine or manifest, and changes no code.
**Scope:** the three English-anchored launch-gate paths en→nl, en→fa and en→prs
only. No non-English pairs. The X→en directions (nl-en / fa-en / prs-en) are
touched only where the spine forces it (see §6, open question Q7).
**Base:** `fix/launch-gate-content-review-wave1` @ `e864adf` (2026-09-29).

---

## 0. Decisions (2026-09-29)

Ramin's decisions on this plan:

- **Q1 scope:** Blocks A–D first (19 units per language: A1–A6, B1–B2, C1–C5, D1–D6), starting with a Wave-0 pilot of unit A1 in nl, fa and prs, reviewed by Ramin before scaling. Blocks E–G later.
- **Q10:** fix the speaking lock now (being done separately in backend).
- **Q4:** Dari standardizes on **می‌توانم** (formal). A1 and B1 prs content will be retrofitted to match A2 (separately).
- **Q5:** existing A2 scenario units are interleaved AFTER the grammar block they use (needs a reorder-import safety check first).
- **Q2, Q3, Q6, Q7, Q8, Q9:** not yet decided; left open.

---

## 1. Diagnosis — the CEFR ladder is inverted

### 1.1 Volume per tier (counted from `docs/content/realizations/<lang>/*.yaml`)

Units / lessons / exercises. Units are counted from the `units:` list and
exercises from `lessons[].exercises` in each realization file. Each path's
manifest entry (`scripts/content_manifest.txt`) wires the same count:
`en-nl` 67, `en-nl-a2` 10, `en-fa` 57, `en-fa-a2` 10, `en-prs` 61,
`en-prs-a2` 10.

| path | A1 | **A2** | B1 | B2 | C1 |
|---|---|---|---|---|---|
| en-nl | 67 u / 402 l / **2,905 ex** | **10 u / 60 l / 420 ex** | 11 / 66 / 473 | 8 / 48 / 352 | 8 / 48 / 336 |
| en-fa | 57 u / 340 l / **1,892 ex** | **10 u / 40 l / 210 ex** | 16 / 96 / 624 | 8 / 24 / 192 | — |
| en-prs | 61 u / 366 l / **2,432 ex** | **10 u / 40 l / 210 ex** | 11 / 66 / 429 | 8 / 24 / 192 | — |

- A2 is **13% (nl) / 7% (fa) / 6% (prs)** of the A1→B1 exercise volume.
  B1 has more exercises than A2 on all three paths.
- Spine: **68 A1 outcomes vs 10 A2 outcomes** in
  `docs/content/universal_spine.yaml` (A2 ids at lines 684–909).
- Practice packs mirror this: `docs/content/practice/en-nl` has 67 a1 / 10 a2
  files, `en-fa` 57 / 10, `en-prs` 61 / 10.

### 1.2 A1 sprawl is nouns, not grammar

Grammar was surveyed by `kind: grammar_note` teaching cards plus the en-X
overlay explanations:

- **en-nl:** A1 units **u38 and u44–u72 (30 units) have zero grammar_note
  cards**. u32–u33, u36, u37 and u39–u43 carry only review notes that re-apply
  grammar taught earlier. Before u29, only u07, u08 and u19 have no grammar
  note. Examples of the sprawl: `a1_unit55_restaurant`, `a1_unit67_markt`,
  `a1_unit68_bakker`, `a1_unit69_ijssalon`, `a1_unit70_bloemist`,
  `a1_unit62_dierentuin`. With `a1_unit06_food` and `a1_unit40_koken`, that
  makes **six food units**.
- **en-fa:** A1 u27, 33, 34, 41, 42 and 44–57 are scenario-only; their notes
  are `review_*` / `summary_words` glosses.
- **en-prs:** A1 u35, 38, 42, 43, 45–47 and 51–61 are scenario-only; their
  grammar_note cards gloss words. prs A1 has about 690 grammar_note cards in
  total, and most of those after u29 are glosses.

### 1.3 A2 teaches almost no grammar of its own

- **nl A2:** each unit has 1–3 grammar_note cards. In every unit except
  u26/u27 the only one is a lesson06 recap of the perfectum or of third-person
  -t, e.g. `a2_unit24_gemeente` `lesson06 summary_grammar`.
- **fa A2:** 14 grammar_note cards across 10 units. They cover و, را, one
  اگر note (`a2_unit11`), one باید note (`a2_unit12`), and one progressive
  card (`a2_unit13 lesson02.teach.pipe_leaking`).
- **prs A2:** 19 grammar_note cards across 10 units, most glossing و. There
  is one اگر card (`a2_unit11 if_grammar`) and one وقتی card
  (`a2_unit18 when_grammar`).
- **The A2 grammar has been pushed up into B1.** These B1 units teach what is
  really A2 grammar:
  - fa: `b1_unit01` (باید + subjunctive), `b1_unit02` (می‌تونم + subjunctive),
    `b1_unit06` (past continuous), `b1_unit10` (relative clauses), `b1_unit12`
    (اگه + subjunctive), `b1_unit13` (وقتی / بعد از اینکه), `b1_unit15`
    (برای اینکه / تا)
  - prs: `b1_unit01`, `02`, `03`, `04`, `06` and `10`
  - nl: `b1_unit04` (relative clauses) and `b1_unit05` (indirect questions)

### 1.4 A2 grammar coverage matrix

✅ = drilled lesson · ◐ = one note or incidental only · ⬆ = taught only at B1 ·
❌ = missing everywhere.

**Dutch (en-nl)**

| target | status | where |
|---|---|---|
| perfectum hebben/zijn | ✅ | `a1_unit12_past_events` L01–04. No ge-/-d/-t participle rule; separable participles (*opgestaan*) not taught |
| imperfectum / OVT | ◐ | one note, `a1_unit22` L06 `simple_past_note` (was/ging/dacht). **No 't kofschip, no regular -te/-de** |
| separable verbs, main clause | ✅ | `a1_unit10` L02 `split_rule` |
| separable verbs in subclause / with modal / with te | ◐/❌ | one note, `a2_unit27` L04 |
| modal + infinitive, modal chains | ⬆ | `b1_unit06`, `b1_unit07`, `b1_unit03` L02. Nothing at A2 |
| om … te | ◐ | overlay notes only (`a1_unit13`, `a2_unit24`) |
| relative clauses die/dat/waar | ⬆ | `b1_unit04_ingewikkelde_zinnen` |
| comparatives/superlatives | ✅ | `a1_unit14_comparisons`. Missing: *meer/meest* + adjective, *even … als*, *niet zo … als* |
| reflexive verbs | ◐ | phrase-card overlay notes (`a1_unit10`, `a1_unit21` L04). No me/je/zich paradigm |
| subordinators other than *omdat*; want/maar/dus contrast | ❌ | voordat, nadat, wanneer missing. *omdat* on a phrase card only |
| future gaan/zullen | ❌ | `a1_unit11` has *Zullen we* as a proposal only |
| er (er + number, erover/ervan) | ◐/❌ | *er is* at phrase level (`a1_unit18`) |
| demonstratives deze/die/dit/dat | ❌ | — |
| diminutives | ❌ | lexical only (*griepje*, *bonnetje*) |
| niet vs geen, niet placement | ◐ | `a1_unit31` L01 `geen_note`. Placement missing |
| indirect questions | ⬆ | `b1_unit05`, as reported speech only |
| te + infinitive (beginnen/proberen/vergeten; staan/zitten/liggen te) | ❌ | — |
| adjective -e inflection | ◐ | `a1_unit30` L02–03. The `a1_unit42` overlay says the rule "isn't taught in this course yet" |

**Iranian Persian (en-fa)**

The realization register is colloquial Tehrani: می‌رم, می‌خوام, رو.

| target | status | where |
|---|---|---|
| simple past | ✅ (lexical) | `a1_unit13_past_events`. **No past-stem rule; past negation نرفتم never taught** |
| past continuous (می + past stem) | ⬆ | `b1_unit06_narrative` |
| present perfect (رفته‌م / رفته‌ام) | ❌ | incidental only (`a2_unit13` خراب شده) |
| past perfect | ⬆ | `b1_unit07` (counterfactual only), `b2_unit04` |
| present subjunctive | ◐ / ⬆ | A1 chunks (`a1_unit12`, `a1_unit29`, `a1_unit35`); drilled only in `b1_unit01`/`02` |
| future خواهم رفت / present-for-future | ❌ | zero occurrences of خواهم / خواهد |
| داشتن progressive | ◐ | one card, `a2_unit13` L02 |
| ezafe chains | ◐ | word-level cards (`a1_unit16`, `a1_unit19`). No chain rule |
| compound verbs: negation, را placement | ◐ | notes in `a2_unit11`, `a2_unit16`, `a2_unit18`. Negation and placement missing |
| relative clauses (ی + که) | ⬆ | `b1_unit10_relative_clauses` |
| superlative ‑ترین | ❌ | zero occurrences |
| object clitics on verbs (دیدمش) | ◐ | `a1_unit31` L05, `b1_unit10` |
| conditional اگه + subjunctive | ◐ / ⬆ | `a2_unit11` (one note); `b1_unit12` |
| negative imperative نـ; می‌شه … ؟ requests | ❌ / ⬆ | `b1_unit09` |
| قبل از اینکه / بعد از اینکه / برای اینکه | ❌ / ⬆ | `b1_unit13`, `b1_unit15`. **قبل از اینکه missing** |
| indefinite ‑ی | ❌ | — |

**Dari (en-prs)**

`realizations/prs/` uses formal written Dari. It is the source of truth for
register; see `docs/content/DARI_REGISTER_REPAIR.md` and
`scripts/check_dari_register.py`.

| target | status | where |
|---|---|---|
| simple past | ✅ | `a1_unit20_past_events`. **Negative past missing at A1/A2** |
| past continuous | ❌ | only the fixed chunk می‌خواستم |
| present perfect | ❌ | fixed phrases only (`a1_unit41` گم شده است) |
| past perfect | ❌ | — |
| present subjunctive | ◐ / ⬆ | A1 chunks (`a1_unit33`, `a1_unit48`–`50`); systematic only in `b1_unit01`/`02`/`03`/`06`. شاید + subjunctive has no note |
| future | ❌ | — |
| progressive | ❌ | not covered by the repair doc either |
| ezafe chains | ◐ | `a1_unit16` only. **The `a1_unit48`/`49` notes misleadingly say nouns join "without a linking word"** |
| compound verbs: negation, را | ◐ | one card per unit (`a1_unit18`, `a1_unit29`–`33`) |
| relative clauses | ◐ / ⬆ | one card in `a2_unit18`; `b1_unit10` |
| superlative ‑ترین | ❌ | — |
| object pronoun suffixes | ❌ | — |
| negative imperative (نکنین) | ❌ | — |
| بعد از اینکه / قبل از اینکه / برای اینکه | ❌ | 0 occurrences in A1, A2 or B1 |
| indefinite ‑ی | ❌ | — |

**Register inconsistency to fix before new A2 authoring:** prs A1 and B1
use **می‌تانم / می‌تانین** (A1: 23 / 80 uses). prs A2 uses **می‌توانم (55) /
می‌توانین (29)** and never می‌تانم. New A2 units would inherit whichever form
the A2 course already teaches, so this needs Ramin's decision first (Q4).

### 1.5 The root cause is structural

The spine is a list of communicative *topics*; it has no grammar field. Each
new A1 topic got a spine outcome and a unit, so A1 grew along the noun axis
while grammar never had a slot. The architecture already allows the fix:
`universal_spine.yaml` `schema_notes.target_language_first` says the
realization "independently owns … grammar progression". This plan uses that.
The new A2 outcomes are communicative can-dos chosen **because** each one
forces a specific grammar point, and each language realizes it with its own
grammar.

---

## 2. Proposed A2 sequence — 31 new grammar-led units

**Design rules for every unit:**

- **One spine outcome per unit** (AUTHORING_GUIDE §1). The can-do is universal;
  the grammar target is per language.
- **Size:**
  - nl follows its established A2 shape: 6 lessons × ~7 exercises = **~42**
    (`a2_unit76_drukke_week` has `planned_lesson_count: 6`).
  - fa/prs currently run 4 lessons / 21 exercises per A2 unit, which is too
    thin for a grammar lesson. This plan proposes **6 lessons × 6 = ~36** for
    them.
  - Each unit has ≥4 real `grammar_note` cards, not a single lesson06 recap.
- **Standard lesson arc:**
  1. **L01** — form, recognition only.
  2. **L02** — form, drag/matching.
  3. **L03** — contrast with the nearest confusable form.
  4. **L04** — production in the unit's scenario.
  5. **L05** — reading, plus listening (nl: glossed `reading` card + 2
     `dictation`, per Phase H/I).
  6. **L06** — dialogue plus mixed production.

  Pacing is recognition → drag → production within every lesson
  (AUTHORING_GUIDE §2).
- **Recycling A1 vocabulary means re-introducing it.** A1 and A2 are separate
  `Course` rows. The compiler's introduced-token lexicon is course-scoped
  (`scripts/compile_content.py` `_lesson_introduced_tokens`, per-manifest
  course), and practice candidate pools are too (AUTHORING_GUIDE §18,
  registry 1.18). So each "recycles" entry below means: L01 opens with
  `vocabulary` review cards whose `introduced_tokens` re-establish that A1
  domain inside the A2 course. **This is how demoted A1 scenario vocabulary
  gets back into the core path.**
- **fa and prs share structure, never text** (AUTHORING_GUIDE §3, standing
  policy 2026-07-06). The per-language grammar cells below are why the two
  realizations must still be authored independently.

**Recycle crosswalk** (A1 unit numbers per path, used in the "recycles" lines):

| domain | nl | fa | prs |
|---|---|---|---|
| routines | 10 | 11 | 12 |
| past events | 12 | 13 | 20 |
| food / restaurant / cooking | 06, 40, 55, 67–69 | 06, 35, 50 | 08, 36, 51 |
| travel / transport / bike | 15, 33, 52 | 16, 28, 47 | 16, 24, 48 |
| health / pharmacy / emergencies | 16, 44, 50 | 17, 39, 45 | 17, 40, 46 |
| work / education | 17, 35 | 18, 30 | 18, 31 |
| housing / household / laundry | 18, 37, 53 | 19, 32, 48 | 19, 33, 49 |
| hobbies / sport / gym / pool | 29, 32, 54, 60 | 24, 27, 49, 55 | 26, 29, 50, 56 |
| outings (cinema, museum, concert, park, beach, zoo, theatre) | 56–59, 61–66 | 51–54, 56, 57 | 52–55, 57–61 |
| shops (clothing, market, bakery, florist, books, pets) | 20, 67, 68, 70–72 | 08, 20 | 10, 21 |
| appointments / library / post / lost items | 39, 45–47 | 34, 40–42 | 35, 41–43 |
| celebrations / personality / appearance | 30, 36, 41 | 25, 31, 36 | 27, 32, 37 |
| technology / neighbourhood | 34, 38 | 29, 33 | 30, 34 |

**File numbering:** the next free A2 unit numbers today are nl
`a2_unit78`–`a2_unit108` and fa/prs `a2_unit19`–`a2_unit49`. Per the
`docs/content/CLAUDE.md` footgun, **run `ls` on the realization directory
immediately before claiming a number.** File numbers are identifiers, not
course order; order comes from the manifest (see §4.4).

The per-unit exercise estimate is **nl 42 · fa 36 · prs 36** unless a unit
says otherwise.

### Block A — Talking about the past (6 units)

**A1 · Last weekend** — `universal.a2.past.narrate_recent_weekend`
- **Can-do:** Tell someone, in order, what you did last weekend, including what you did *not* do.
- **nl:** perfectum deepened — the participle rule (ge-…-t/-d, 't kofschip preview), irregular participles, zijn-verbs of motion/change.
- **fa:** simple past as a *system*: past stem + endings, and **negative نـ (نرفتم)**, which is currently untaught.
- **prs:** same targets in formal Dari; negative past (نرفتم, نخوردم) is missing today.
- **Vocab:** weekend, visits, errands.
- **Recycles:** routines, past events, outings.

**A2 · Separable verbs in the past** — `universal.a2.past.describe_a_busy_morning`
- **Can-do:** Describe step by step how a morning or trip went.
- **nl:** separable participles (*opgestaan*, *aangekomen*, *uitgestapt*); separable verbs with modals and in a *dat*-clause.
- **fa:** compound verbs in the past, including negation (*کار نکردم*, *زنگ نزدم*) and where را goes (*در رو باز کردم*).
- **prs:** compound verbs in the past; negation and را placement (*دروازه را باز کردم*).
- **Vocab:** getting ready, commuting.
- **Recycles:** routines, travel/transport.

**A3 · How things used to be** — `universal.a2.past.describe_past_habits`
- **Can-do:** Describe how life used to be (childhood, a previous home or job) versus now.
- **nl:** imperfectum, regular (-te/-de, 't kofschip), with *vroeger* / *toen* / *nu*.
- **fa:** past continuous as the habitual past, می + past stem (*می‌رفتم*). Pulled down from `b1_unit06`.
- **prs:** past continuous, habitual (*می‌رفتم*). Missing today.
- **Vocab:** childhood, school, old neighbourhood.
- **Recycles:** housing, education, neighbourhood.

**A4 · What was happening when…** — `universal.a2.past.tell_what_was_happening`
- **Can-do:** Say what was going on when something else happened.
- **nl:** imperfectum, irregular (*was/had/ging/kwam/zag/zei*), *toen* + verb-final.
- **fa:** past progressive *داشتم می‌رفتم که…* plus *وقتی (که)*.
- **prs:** past continuous with *وقتی که*. **The Dari progressive form is open (Q3).**
- **Vocab:** small incidents, weather, traffic.
- **Recycles:** travel, emergencies, weather.

**A5 · Have you ever…?** — `universal.a2.experience.talk_about_life_experiences`
- **Can-do:** Ask and say what you have or have never done.
- **nl:** perfectum vs imperfectum choice, *ooit* / *nog nooit* / *al* / *nog niet*.
- **fa:** present perfect. The colloquial form (رفته‌م) is taught; the written form (رفته‌ام) is taught for recognition only.
- **prs:** present perfect in formal *رفته‌ام*. **The Kabuli spoken form is open (Q3).**
- **Vocab:** travel, food, experiences.
- **Recycles:** food, travel, outings.

**A6 · It had already happened** — `universal.a2.past.explain_what_had_happened_before`
- **Can-do:** Explain that something had already happened before a reference point.
- **nl:** voltooid verleden tijd (*had/was* + participle), mostly *receptive*, plus *nadat*.
- **fa:** past perfect (*رفته بودم*) used outside counterfactuals (currently only in `b1_unit07`/`b2_unit04`).
- **prs:** past perfect *رفته بودم*. Missing today.
- **Vocab:** missed trains, late arrivals, lost items.
- **Recycles:** travel, lost items, appointments.
- **Estimate:** nl 36 · fa 36 · prs 36.

### Block B — Future and plans (2 units)

**B1 · My plans** — `universal.a2.future.announce_plans_and_intentions`
- **Can-do:** Say what you are going to do soon, and what you intend to do later.
- **nl:** *gaan* + infinitive; *van plan zijn om … te*.
- **fa:** present-for-future made explicit; *می‌خوام* + subjunctive for intention.
- **prs:** present-for-future; *می‌خواهم* + subjunctive (full form is the Dari norm).
- **Vocab:** holidays, courses, moving house.
- **Recycles:** travel, education, housing.

**B2 · Predictions and promises** — `universal.a2.future.make_predictions_and_promises`
- **Can-do:** Predict what will happen and make a promise.
- **nl:** *zullen* (prediction/promise) vs *gaan*; *misschien* + inversion.
- **fa:** formal future *خواهم رفت* for recognition in news/notices; *شاید / احتمالاً* + subjunctive.
- **prs:** *خواهم رفت* (fits the formal realization); *شاید* + subjunctive, which has no note today.
- **Vocab:** weather forecasts, notices, commitments.
- **Recycles:** weather, work, appointments.

### Block C — Modality and requests (5 units)

**C1 · Rules and permission** — `universal.a2.modality.ask_permission_and_state_rules`
- **Can-do:** Ask whether something is allowed, and state what must or need not be done.
- **nl:** *mogen / moeten / hoeven niet … te*, with the infinitive at the end.
- **fa:** *باید / نباید* + subjunctive; *اجازه دارم …؟* Pulled down from `b1_unit01`.
- **prs:** *باید / نباید* + subjunctive with Dari 2pl *‑ین* forms.
- **Vocab:** house rules, library, pool, gym.
- **Recycles:** library, pool, gym, waste sorting.

**C2 · What I can and might do** — `universal.a2.modality.state_ability_and_possibility`
- **Can-do:** Say what you can or can't do and what might happen.
- **nl:** *kunnen*; **modal chains** (*wil kunnen*, *zou moeten*); modal + separable (*ik kan je ophalen*).
- **fa:** *می‌تونم* + subjunctive; *ممکنه / شاید* + subjunctive.
- **prs:** *می‌تانم* + subjunctive (depends on Q4); *ممکن است* + subjunctive.
- **Vocab:** skills, availability.
- **Recycles:** hobbies, work, technology.

**C3 · Polite requests and offers** — `universal.a2.requests.make_polite_requests_and_offers`
- **Can-do:** Make a polite request, offer help, and accept or decline.
- **nl:** *zou je / zou u … kunnen*, *zal ik …?*, imperative + *even / eens*.
- **fa:** *می‌شه …؟* + subjunctive; **negative imperative نـ**.
- **prs:** *می‌شود که …؟*; *لطفاً* + imperative; **negative imperative نکنین** (missing today).
- **Vocab:** services, neighbours, shops.
- **Recycles:** shops, neighbourhood, household.

**C4 · Giving advice** — `universal.a2.advice.give_simple_advice`
- **Can-do:** Give and respond to simple advice about a problem.
- **nl:** *je moet / je zou … moeten*, *het is beter om … te*.
- **fa:** *بهتره* + subjunctive.
- **prs:** *بهتر است* + subjunctive. *بهتره* is flagged as Tehrani by `check_dari_register.py`.
- **Vocab:** health, study, money.
- **Recycles:** health, pharmacy, money.

**C5 · Starting, stopping, trying** — `universal.a2.habits.describe_starting_stopping_trying`
- **Can-do:** Say what you started, stopped, tried or forgot to do.
- **nl:** *te* + infinitive after *beginnen / proberen / vergeten*; *stoppen met*; *staan / zitten / liggen te*.
- **fa:** *شروع کردن به*, *سعی کردن* + subjunctive, *یادم رفت که …*.
- **prs:** *شروع کردن*, *کوشش کردن* + subjunctive, *فراموش کردم که …*.
- **Vocab:** habits, sport, screen time.
- **Recycles:** gym, hobbies, technology.

### Block D — Linking clauses (6 units)

**D1 · Because / so** — `universal.a2.reasons.explain_reasons_and_consequences`
- **Can-do:** Give a reason and a consequence in one message.
- **nl:** *omdat* (verb-final) vs *want* (no change); *dus* (inversion). The *want/maar/dus* contrast is missing today.
- **fa:** *چون*, *برای همین*, *به خاطر* + noun.
- **prs:** *چون*, *به همین دلیل*, *به دلیل* + noun.
- **Vocab:** excuses, changes of plan.
- **Recycles:** appointments, work, weather.

**D2 · Before / after / when** — `universal.a2.sequencing.order_events_with_time_clauses`
- **Can-do:** Order events with before, after and when clauses.
- **nl:** *voordat / nadat / wanneer / als* + verb-final, with inversion after a fronted subclause.
- **fa:** **قبل از اینکه + subjunctive** (missing everywhere); *بعد از اینکه* + past; *وقتی*. Pulled down from `b1_unit13`.
- **prs:** *قبل از اینکه*, *بعد از اینکه* (0 occurrences today), *وقتی که*.
- **Vocab:** daily sequences, travel logistics.
- **Recycles:** routines, travel, cooking.

**D3 · In order to** — `universal.a2.purpose.say_why_you_do_things`
- **Can-do:** Say what you do something for.
- **nl:** *om … te* + infinitive (incidental today); *zodat* for recognition.
- **fa:** *برای اینکه / تا* + subjunctive. Pulled down from `b1_unit15`.
- **prs:** *برای اینکه* (missing) / *تا* + subjunctive (`b1_unit06`).
- **Vocab:** errands, learning, saving money.
- **Recycles:** post, bank/money, education.

**D4 · If…** — `universal.a2.conditions.talk_about_real_conditions`
- **Can-do:** Talk about what happens or will happen if a condition is met.
- **nl:** *als* + present, with *dan*-inversion in the main clause.
- **fa:** *اگه* + subjunctive / present. Pulled down from `b1_unit12`.
- **prs:** *اگر* + subjunctive (only one note today, `a2_unit11`).
- **Vocab:** weather plans, shop policies.
- **Recycles:** weather, outings, shops.
- **B1 knock-on:** B1 keeps unreal conditionals (Q6).

**D5 · Asking indirectly** — `universal.a2.questions.ask_indirect_questions`
- **Can-do:** Ask politely for information with an embedded question.
- **nl:** *Weet u waar / wanneer / of …?* + verb-final (missing today; B1 has only the reported form).
- **fa:** *می‌دونید … کجاست؟*, *نمی‌دونم که …*.
- **prs:** *می‌دانین که … کجاست؟*.
- **Vocab:** stations, offices, museums.
- **Recycles:** directions, outings, library.

**D6 · Passing on a message** — `universal.a2.communication.pass_on_a_simple_message`
- **Can-do:** Pass on what someone said or asked, in the present tense.
- **nl:** *Hij zegt dat … / Ze vraagt of …* (present only; `b1_unit05` keeps past-shifted reported speech).
- **fa:** *می‌گه که …*, *می‌پرسه که …*.
- **prs:** *می‌گوید که …*, *می‌پرسد که …*.
- **Vocab:** phone messages, notes.
- **Recycles:** phone/communication, work.
- **Estimate:** nl 36 · fa 36 · prs 36.

### Block E — Describing and specifying (5 units)

**E1 · The one that…** — `universal.a2.description.identify_with_relative_clauses`
- **Can-do:** Identify a person or thing by what it does or what you did with it.
- **nl:** *die / dat* relative clauses, subject and object. `b1_unit04` keeps *waar-* forms and prepositions.
- **fa:** head noun + *ی* + *که* (*کتابی که خریدم*). `b1_unit10` keeps resumptive and oblique forms.
- **prs:** same pattern (*کتابی که خریدم*); one card exists today (`a2_unit18`).
- **Vocab:** people at work, lost items, shop items.
- **Recycles:** lost items, shops, work.

**E2 · The best, the most** — `universal.a2.description.compare_in_detail`
- **Can-do:** Compare several options and pick the best.
- **nl:** *meer / meest* + adjective, *even … als*, *niet zo … als*, *het -st*.
- **fa:** **superlative ‑ترین** (zero occurrences today); *به اندازه‌ی*.
- **prs:** **‑ترین** (missing); *مثل … *.
- **Vocab:** housing, phones, holidays.
- **Recycles:** housing, technology, travel.

**E3 · Describing things properly** — `universal.a2.description.describe_objects_with_adjectives`
- **Can-do:** Describe an object precisely (size, colour, material, owner).
- **nl:** full adjective *-e* inflection rule (de / het / een / bare).
- **fa:** **ezafe chains**, noun-adjective-possessor, including after vowels (*ی / ـه‌ی*).
- **prs:** ezafe chains (*ـِ / ـی / ـهٔ*). This also corrects the misleading `a1_unit48`/`49` notes.
- **Vocab:** clothing, furniture, lost property.
- **Recycles:** clothing, colours, household, lost items.

**E4 · This one, that one, a certain…** — `universal.a2.description.point_out_and_specify`
- **Can-do:** Point out and specify items when shopping or choosing.
- **nl:** *deze / die / dit / dat*; diminutives (*-je / -tje / -pje*) and their *het*-gender.
- **fa:** **indefinite ‑ی** and *یه … ی*; *این / اون* + plural.
- **prs:** indefinite *ی* and *یک … ی*; *این / آن*. *اون* is flagged Tehrani.
- **Vocab:** markets, bakery, florist.
- **Recycles:** market, bakery, florist, bookshop (nl 67, 68, 70, 71). **Demoted situations fold back into the core path here.**
- **Estimate:** nl 36 · fa 36 · prs 36.

**E5 · Not yet, no longer** — `universal.a2.negation.correct_misunderstandings`
- **Can-do:** Correct a misunderstanding: not yet, not any more, none.
- **nl:** *niet* placement rules; *niet* vs *geen*; *nog niet / niet meer / geen … meer*.
- **fa:** *هنوز … نـ*, *دیگه … نـ*, *هیچ … نـ*.
- **prs:** *هنوز*, *دیگر*, *هیچ … نـ*.
- **Vocab:** orders, bookings, appointments.
- **Recycles:** restaurant, accommodation, appointments.

### Block F — Verb systems (3 units)

**F1 · Looking after yourself** — `universal.a2.daily_life.describe_self_care_and_feelings`
- **Can-do:** Describe how you feel and what you do to look after yourself.
- **nl:** reflexive verbs, full *me / je / zich / ons / jullie* paradigm (*zich voelen*, *zich haasten*, *zich vergissen*).
- **fa:** reflexive *خود‌* + possessive (*خودم*), with compound verbs.
- **prs:** *خود* + possessive.
- **Vocab:** health, personal care, emotions.
- **Recycles:** health, personal care/barber, emotions.

**F2 · Referring back** — `universal.a2.references.refer_back_without_repeating`
- **Can-do:** Refer back to people and things without repeating them.
- **nl:** object pronouns, full set; *er* + number (*ik heb er drie*), *erover / ervan / ermee*.
- **fa:** **object clitics on verbs** (*دیدمش*, *بهش گفتم*).
- **prs:** *او را / آن را*. **The clitic policy is open (Q3):** `check_dari_register.py` flags ازش / باهاش / بهت.
- **Vocab:** gifts, borrowing, returns.
- **Recycles:** library, celebrations, shops.

**F3 · Right now** — `universal.a2.ongoing.describe_what_is_happening_now`
- **Can-do:** Say what is going on right now and what someone is in the middle of.
- **nl:** *aan het* + infinitive; *zitten / staan / liggen te*.
- **fa:** present progressive *دارم می‌رم*, contrasted with plain present.
- **prs:** **open (Q3).** DARI_REGISTER_REPAIR.md does not cover the progressive. The candidate is *در حال … استم* or plain *می‌*.
- **Vocab:** phone calls, household.
- **Recycles:** phone/communication, household, laundry.
- **Estimate:** nl 36 · fa 36 · prs 30.

### Block G — Integration units (4 units)

These combine blocks A–F. They are the tier's reading and listening
showcases.

**G1 · A message to a friend** — `universal.a2.communication.write_informal_message`
- **Can-do:** Write an informal message about what happened and what's next.
- **Grammar:** past + future + reasons, with language-specific letter/message conventions.
- **Recycles:** celebrations, outings.

**G2 · Invitations** — `universal.a2.social.invite_accept_decline_with_reasons`
- **Can-do:** Invite someone, and accept or decline with a reason and an alternative.
- **Grammar:** modals + *omdat/want* / *چون* + future.
- **Recycles:** celebrations, cinema, concert, theatre.

**G3 · Changing an arrangement** — `universal.a2.plans.rearrange_an_appointment`
- **Can-do:** Move an appointment, explaining the reason and proposing a new time.
- **Grammar:** time clauses + conditionals + polite requests.
- **Recycles:** appointments, hairdresser, bike rental.

**G4 · A short story** — `universal.a2.stories.retell_a_short_story`
- **Can-do:** Read or hear a short story and retell it in order.
- **Grammar:** all past tenses; the connectors *eerst / daarna / toen* and their fa/prs equivalents.
- **Recycles:** outings (zoo, boat tour, amusement park).

### Totals

| | new units | new exercises (est.) | A2 total after | A2 share of A1+A2+B1 exercises |
|---|---|---|---|---|
| en-nl | 31 | ~1,280 | ~1,700 (41 units) | 13% → ~33% |
| en-fa | 31 | ~1,110 | ~1,320 (41 units) | 7% → ~34% |
| en-prs | 31 | ~1,100 | ~1,310 (41 units) | 6% → ~31% |

The existing 10 A2 scenario units per path stay as they are, reordered as
**applied units** after the block whose grammar they use. For example:
- `a2_unit27_huisarts` / fa `a2_unit12_doctor` come after Block C.
- `a2_unit74_reisvertraging` / fa `a2_unit15_travel_disruption` come after
  Block D.

Reordering depends on Q5 and §4.4. Rewriting the existing units is **not**
in scope; they are reviewed and deployed.

---

## 3. Spine changes needed (described only — do NOT edit yet)

Add **31 outcomes** to `docs/content/universal_spine.yaml` after the current
A2 block, which ends at `universal.a2.shopping.make_a_complaint`, line ~909.
Their ids are the ones listed in §2. Each entry follows the existing schema:
`topic`, `can_do`, `prerequisites`, `modalities: [listening, speaking,
reading, writing]`, and four `assessment_requirements` (one per modality) with
`success_criteria`.

- **Can-do wording must stay communicative, not grammatical.** The spine is
  language-independent (`schema_notes.target_language_first`). "Describe past
  habits" is universal; "use the imperfectum" is not. The grammar mapping
  lives in each realization's lesson titles, `grammar_note` cards and
  `review.notes`.
- **Prerequisites:** chain within blocks. A3 requires A1; A4 requires A3; D2
  requires D1; E1 requires `universal.a1.shopping.ask_prices_quantities`.
  Block A requires `universal.a1.past_events.describe_recent_event`. Keep
  prerequisites to A1/A2 ids only.
- **Collision check:** these ids overlap in *topic* with existing B1 ids, but
  none duplicates one. Examples:
  - D4 `a2.conditions.talk_about_real_conditions` vs
    `b1.conditions.express_real_conditions`
  - D6 vs `b1.reported_speech.report_what_someone_said`
  - E1 vs `b1.narrative.combine_descriptions_with_relative_clauses`

  Each A2 `can_do` must state the A2 ceiling (present-tense reporting, subject
  and object relatives only, and so on) so the B1 outcomes stay distinct.
  Reviewer check: read each A2/B1 pair side by side.
- **Optional, and recommended:** add a non-breaking `track: situation` marker
  to the 68 A1 outcomes' *units*, not the outcomes (§4). The spine itself
  needs no demotion field.
- **One spine commit, made by the coordinator before wave 1.** It must not
  run in parallel with authoring, because the spine is a shared-file footgun
  (root CLAUDE.md, staging rule).

---

## 4. Demoting A1 scenario units to optional "Situations"

### 4.1 What to demote

| path | pure-scenario A1 units (demote now) | grammar-bearing 29+ units (demote after their A2 replacement ships) |
|---|---|---|
| en-nl | u38, u44–u72 (**30**) + review-only u32, u33, u35–u37, u39–u43 (**10**) = **40** | u29 (elk/elke) → after E4; u30 (adjective -e) → after E3; u31 (geen, plural -en) → after E5; u34 (compounds, *opzoeken*) stays core (**4**) |
| en-fa | u27, 33, 34, 41, 42, 44–57 (**18**) | u28, 29–32, 35–40, 43 (small points: با + vehicle, subjunctive chunks, formal imperative, دیدید) |
| en-prs | u35, 38, 42, 43, 45–47, 51–61 (**18**) | u29–34, 36, 37, 39–41, 44, 48–50 (compound verbs, باید + subjunctive, شده, را + negation) |

Units 01–28 stay core on every path.

### 4.2 Mechanism — flag in place, never move rows

**Do not move demoted units into a separate course, and do not delete or
renumber them.** `Unit.content_key` is unique *per course* (migration 0015,
`backend/app/models/entities.py` `Unit`). Moving a unit to another course
makes import create new rows. That orphans every `LessonProgress`,
`ExerciseAttempt`, `CheckpointAttempt` and practice anchor tied to the old
lesson and exercise ids. In-place flagging keeps all ids, so no progress, XP,
streak or SRS data is touched.

Proposed change (CODE lane: Codex backend + migration, Claude frontend +
CONTRACT; it goes to Session 1 as a separate brief):

1. **Contract first.** Update `docs/CONTRACT.md`: add
   `UnitOut.track: "core" | "situation"`, default `"core"`.
2. **Model and migration.** Add `Unit.track`: an enum column, `NOT NULL`,
   `server_default 'core'`, fresh-migrate-safe per `backend/CLAUDE.md`.
   Additive only; no data migration is needed.
3. **Content and compiler.** Add an optional per-unit `track: situation` in
   realization YAML. The compiler validates and passes it through.
   `import_content()` updates it in place, matched by `content_key`.
4. **Behaviour that must change with it** (`backend/app/api/router.py`):
   - **`speaking_unlocked()` (line 687) must count only core
     reading_writing units.** Today it requires *every* reading_writing unit
     in the course to be complete. en-fa A1 has 7 speaking units (u06–09,
     u20–22), so fa learners are gated behind ~50 reading units today. That
     is already a product problem, and demotion without this fix would make
     it worse.
   - `first_placement_unit()` (line 663) must pick core units only.
   - Any "course complete" or checkpoint-progress summary must count core
     only.
5. **Frontend.** The course map renders core units as the path. Situation
   units go in a collapsible **"Situations"** shelf: always unlocked, never
   the "next recommended" unit, with completed ones still showing their
   progress. `LessonRunnerPage`, review and practice need no change.
6. **Practice.** Situation lexemes stay in the course's practice pool (same
   course, so no §18 issue). Optionally, down-weight situation lexemes a
   learner has never studied.

**Rollback:** flip the YAML field and re-import. There is no schema rollback,
and no data is lost either way.

### 4.3 Verification for the demotion change

Follow the root CLAUDE.md verification bar:
- Isolated-DB pytest, including a test that an existing user's
  `LessonProgress` on a demoted unit survives re-import.
- The full `npm run build`.
- Live play with a fresh account and with an **existing** account that has
  progress on a to-be-demoted unit (nl u55, fa u50).
- `/courses/{id}/units` checked before and after.
- Deploy per `docs/PRE_DEPLOY_RUNBOOK.md`. No destructive live-DB operation
  is involved.

### 4.4 A2 course ordering (needed for the interleave in §2)

Import currently appends by unit `order` and updates in place by
`content_key`. `UniqueConstraint("course_id", "order")` means that inserting
new units *before* the existing 10 shifts their orders, which can collide
mid-update.

**Before wave 1, Codex should test a reorder import on an isolated DB:**
existing A2 units move from orders 1–10 to interleaved positions, with
progress intact. If that isn't safe, the fallback is two-phase order
renumbering (offset, then final) inside `import_content()`. The worse
fallback is append-only, which would put the 10 scenario units *before* the
grammar — pedagogically backwards.

---

## 5. Authoring and review pipeline, batch sizes, effort

### 5.1 Pipeline (per unit, per language)

These rules come from root CLAUDE.md, `docs/content/CLAUDE.md` and
AUTHORING_GUIDE §20.

1. **Author.** Codex (from scratch) or Claude (adapting public-domain
   material: FSI Dutch, DLI Dari, per §10) writes the realization and its
   en-X overlay as a pair. The dispatch prompt includes, **pasted
   verbatim**:
   - `docs/content/AUTHORING_PREFLIGHT.md`
   - the recognition→drag→production rule
   - the named-form rule for production prompts ("name the form the prompt
     wants"; this is the underdetermined-prompt class)
   - the heard-distractor rule
   - the "add ONLY X; if blocked, skip and report — never mask it" clause
   - for prs: DARI_REGISTER_REPAIR.md's absolute rules, "never open
     fa files", and `scripts/check_dari_register.py` as an acceptance gate
   - for fa: the colloquial register pin
2. **Compile.** Run `scripts/verify.sh --content-only`, **course-scoped**
   (never judge token coverage from a single-unit run). Grep for
   `COMPILE FAILED`. Also run the answer-shape corpus test
   (`backend/tests/test_content_answer_shapes.py`).
3. **Fresh-context review.** Use the `content-reviewer` agent or Codex, with
   no access to the authoring reasoning. **Every unit gets full review** — this
   is launch-gate content and a new recipe (the tiered policy).
4. **Fix, then adversarial re-verify.** Use the `content-tier` workflow.
5. **Record.** Log the round in `docs/CONTENT_DEFECT_REGISTRY.md` Section 4,
   zero-defect rounds included. Any rule-shaped finding becomes a validator.
6. **Wire.** The coordinator edits the manifest (`en-nl-a2` / `en-fa-a2` /
   `en-prs-a2` lines), commits with explicit pathspecs, and runs
   `git show --stat`.
7. **Practice pack.** Write one practice pack per unit
   (`docs/content/PRACTICE_PACK_RECIPE.md`,
   `scripts/practice_manifest.txt`). It follows one wave behind.
8. **Audio.** nl uses TTS now. fa uses TTS once the Azure key is set. **prs
   has no TTS**, so listening items queue into `scripts/audio_manifest.py`
   for recording. prs units stay playable without audio only if no item
   depends on audio (§14).
9. **Native pass.** Ramin reviews every unit (nl, fa and prs are all
   languages he verifies personally).
10. **Live play.** Play one unit per language per wave end-to-end with a
    fresh account before deploy.

### 5.2 Batches

- **Wave 0 — pilot, 3 units.** Unit A1 in each of nl, fa and prs. This is
  new-recipe territory: grammar-led A2. Full review, then Ramin's native
  pass, then the recipe is **frozen** into an A2 dispatch template in
  `AUTHORING_PROMPT_TEMPLATE.md` before scaling.
- **Waves 1–8 — 12 units per wave.** That is 4 units per language, 3 Codex
  tasks in parallel on disjoint language directories. Units go in block order,
  so the grammar each unit builds on is already reviewed. The manifest and
  spine are touched only by the coordinator, between waves.
- **Tier-level retrofit wave.**
  - Reorder the A2 manifests (after §4.4).
  - Fix prs A2 می‌توانم vs می‌تانم (Q4).
  - Fix the misleading prs `a1_unit48`/`49` ezafe notes.
  - Apply the demotion flags.

### 5.3 Honest effort estimate

| item | estimate | basis |
|---|---|---|
| New content | 93 realizations + 93 overlays, ~3,450 exercises, ~400 grammar_note cards | §2 totals |
| Codex authoring | ~96 tasks (pilot + 8 × 12), ~2–3 waves per working day at best | 2026-07-15 ran 5–7 Codex waves in one day, but those were 6-unit waves on mature recipes |
| Fresh-context review | ~150–200k tokens per unit reviewed by Claude → **~15–19M tokens** if all on Claude. Route ≥half to Codex (the tiered policy allows this when budget is tight) | docs/content/CLAUDE.md "~200k tokens per review" |
| Expected defect yield | ~1.5–3 findings per unit → **~150–280 fixes**, heaviest in the first 2 waves | registry: 7–19 per 6-unit lane on new tiers (2026-07-15 waves) |
| Practice packs | 93 packs, 1 Codex wave each, ~8 waves | recipe exists |
| Demotion + ordering code | 1 Codex backend task + migration, 1 frontend task, contract edit, isolated pytest, live verification → **~1–2 working days** | §4 |
| prs audio recording | every prs listening item; count set when authored (~5–8 per unit → ~150–250 clips) | no prs TTS |
| **Ramin's native review** | ~3,450 exercises + ~400 notes. At 30–45 s per item that is **~30–45 hours** | **This is the real critical path**, not Codex throughput |
| **Calendar** | pipeline ~3–4 weeks of steady sessions; end-to-end **~6–8 weeks** with Ramin's review in parallel | |

**Cheaper staging if needed:** ship Blocks A–D first (19 units per language).
They cover the most-used grammar (past tenses, future, modals, clause
linking) and raise A2 to roughly 25% of volume on their own. E–G can follow
as drip content.

---

## 6. Risks and open questions for Ramin

### Risks

- **R1 — spine coverage regression.** Today the English realization covers
  every spine outcome (`docs/content/CLAUDE.md`). Adding 31 outcomes makes
  the coverage dashboard show gaps for nl-en / fa-en / prs-en / de-en, and
  for every other en-X path, until they are realized. That is cosmetic, but
  visible (Q7).
- **R2 — B1 overlap.** Pulling subjunctive, relative clauses, purpose clauses
  and time clauses down to A2 makes parts of these units repeat A2:
  - fa `b1_unit01`/`02`/`06`/`10`/`12`/`13`/`15`
  - prs `b1_unit01`–`04`/`06`/`10`
  - nl `b1_unit04`/`05`

  They still carry genuine B1 layers (resumptive and oblique relatives,
  past-modal regret, reported past). Without a B1 touch-up, learners would
  see some items twice (Q6).
- **R3 — import reorder.** Covered in §4.4. If reordering isn't safe, the
  interleave fails and the grammar arrives after the scenarios.
- **R4 — validator gaming at scale.** 93 units is the largest Codex content
  push so far. The known failure modes are masking errors with bogus content
  and exploiting escape hatches. Mitigation: named forbidden forms in every
  prompt, a coordinator diff audit per wave, and full review.
- **R5 — cross-unit canon.** Grammar-led units reuse the existing cast
  (nl: Lotte, Omar, Nina). Grep character profiles before writing dialogue.
  Note the existing nl Nina timeline tension (`a2_unit73` vs `a2_unit76`
  review notes).
- **R6 — Dari progressive and perfect forms are under-specified.**
  DARI_REGISTER_REPAIR.md covers the copula, 2pl endings and modal
  contractions only. Authoring Blocks A and F without a ruling risks a new
  1.28-class split-brain.
- **R7 — prs listening depends on recordings.** Without TTS, prs A2 listening
  depth depends on a recording queue that does not exist yet.
- **R8 — demotion UX.** Learners mid-way through A1 u44+ will suddenly see
  those units as "optional". The flag preserves their progress, but a
  one-line in-app explanation is advisable.

### Open questions

- **[DECIDED 2026-09-29] Q1 — scope.** Is 31 new units per language right, or stage Blocks A–D
  first (19 units)?
  **Decision:** Blocks A–D first (19 units per language), Wave-0 pilot of A1 in nl/fa/prs reviewed by Ramin before scaling; E–G later.
- **Q2 — fa/prs unit size.** Is 6 lessons × ~6 exercises right? The current
  fa/prs A2 units are 4 × ~5.
- **Q3 — Dari rulings.** Please rule on:
  - the progressive (*در حال … استم*, or plain present only);
  - spoken present perfect forms;
  - object clitics on verbs (دیدمش), given that ازش / باهاش are flagged
    Tehrani;
  - whether *خواهم رفت* is acceptable as taught (not just recognized) in the
    formal realization.
- **[DECIDED 2026-09-29] Q4 — prs modal.** Standardize prs A2 on **می‌تانم** (matching A1 and B1)
  before authoring, and retrofit the 84 می‌توانم / می‌توانین uses in
  `realizations/prs/a2_*`?
  **Decision:** standardize Dari on **می‌توانم** (formal); A1 and B1 prs content to be retrofitted to match A2 (separately). The question's original می‌تانم proposal is superseded.
- **[DECIDED 2026-09-29] Q5 — ordering.** Interleave the existing 10 A2 scenario units after their
  grammar blocks (recommended; needs §4.4), or leave them first?
  **Decision:** interleave existing A2 scenario units AFTER the grammar block they use; needs a reorder-import safety check first.
- **Q6 — B1.** Leave the overlapping B1 units as-is for launch, or schedule a
  light B1 retrofit that removes the now-duplicated A2 layer?
- **Q7 — X→en.** Add the 31 outcomes to the shared spine now, accepting the
  coverage gaps in other paths? The alternative is to scope them to en-nl /
  en-fa / en-prs with a documented realization departure (allowed by
  `schema_notes.outcomes_not_order`).
- **Q8 — demotion boundary.** Demote only the pure-scenario units now
  (nl 40, fa 18, prs 18), or all of 29+ once the A2 replacements ship?
- **Q9 — nl voltooid verleden (A6).** Keep it receptive-only at A2, or move
  it to B1?
- **[DECIDED 2026-09-29] Q10 — speaking gate.** Should the `speaking_unlocked()` fix (core units
  only) ship on its own, ahead of this plan? It already gates en-fa A1
  speaking behind ~50 units.
  **Decision:** fix the speaking lock now, ahead of this plan (being done separately in backend).
