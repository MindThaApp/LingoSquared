# Session 2 (CONTENT) — queued notes for BUILD_LOG.md / CLAUDE.md

Per the parallel-session ownership map in `docs/SONNET_BUILD_PROMPT_UPGRADES.md`:
Session 1 is the default editor for the build log. This file queues
Session 2's entries for Session 1 to fold in — not edited directly into
`CLAUDE.md`/`docs/BUILD_LOG.md` to avoid a concurrent-write collision.

## 2026-07-05 overnight — es/fr unit01 review finished, nl unit01 authored + reviewed (both directions)

Self-identified as Session 2 (CONTENT) this session, per the ownership
map. All work below: authored/reviewed via Codex (`--background --write`,
fresh context per review pass), independently verified by the driving
Claude session (real compiler validation re-run, not just trusting
Codex's self-report; actual file reads to spot-check claimed fixes).

**es/fr unit01 review cycle finished** (both were drafted,
`status: unreviewed`, per the content-program instruction to finish
in-flight units before starting nl):
- Spanish: fixed an incorrect dialogue answer key (a disambiguation
  issue — "Yo también" appears twice in the dialogue for different
  reasons; the exercise's target text now pairs it with an adjacent
  disambiguating phrase), an ambiguous formal/plural question, weak
  distractors, incomplete accent variants, self-revealing prompts, and
  lesson-pacing violations.
- French: fixed an invalid "Bonjour, vous" fragment used standalone, a
  nonsensical "Vous êtes un atelier" liaison-drill sentence (now two
  separate sentences: "Vous êtes. Un atelier." — verified this is
  actually what's in the file now), an ambiguous liaison distractor, a
  role-selection answer-key defect, missing variants, and pacing
  violations.
- Both now `review: {status: reviewed, required_next_reviewer: null}`
  (verified against the file directly), 0 errors/0 warnings on
  `compile_content.py compile` (re-run independently, not just Codex's
  claim).
- Per the plan of record: es/fr are now parked until nl is done — do
  not resume es/fr work without checking whether nl still needs
  attention first.

**nl unit01 authored AND reviewed, BOTH directions** — this is the
first real content for the reference language:
- `docs/content/realizations/nl/a1_unit01_greetings.yaml` +
  `docs/content/overlays/en-nl/a1_unit01.yaml` (en→nl). Matches the
  established "Latin cohort" unit01 scope (6 lessons, covers both
  `universal.a1.greetings.open_close_exchange` and
  `universal.a1.introductions.exchange_identity` in one unit, same
  shape as es/fr) — deliberately NOT templated off es/fr (Codex was
  explicitly told not to open those files at all). Core teaching point
  is the jij/je vs u register distinction with correct matching verb
  forms (Ben jij / Bent u, kom je / komt u). Full audio-ready: nl has
  real Google TTS support (`nl-NL` confirmed in
  `backend/app/services/tts.py`'s `GOOGLE_TTS_SUPPORTED_LANGUAGES`), so
  this unit uses real listen_select/listen_type/listen_order exercises
  (16 listening exercises + 2 audio dialogue-comprehension), unlike
  fa/prs which exclude these for lack of a TTS voice. 48 exercises, 53
  teaching cards.
  - Fresh-context review found and fixed real issues: a mismatched
    register answer key, a genuinely ambiguous Belgium/language
    pairing (Belgium has multiple official languages, so pairing it
    with "Dutch" as a language-match was legitimately wrong — now uses
    the unambiguous nationality adjective "Belgisch" instead — verified
    this fix is actually in the file), accidentally-valid and
    weak/random distractors across five lessons, a stilted/repetitive
    closing dialogue (reworked and verified more natural in the actual
    file), and added missing "Tot ziens" teaching coverage.
  - `status: reviewed`, `required_next_reviewer: null`. 0 errors/0
    warnings. **This is now ready for Ramin's native-speaker review
    gate — that step is explicitly his, not something I can do.**
- `docs/content/overlays/nl-en/a1_unit01.yaml` +
  `docs/content/overlays/nl-en/a1_unit02.yaml` (nl→en, reusing the
  EXISTING shared English realization unchanged — no new English
  content, matching the fa-en/prs-en reuse pattern). Applied the
  strong "treat sibling *-en overlays as if they don't exist" rule
  from the start (documented failure mode from earlier prs-en work) —
  verified independently via an exact-string-match scan against
  fa-en/prs-en: found 72/71 matches respectively, but confirmed every
  single one is either shared metadata (`status`, `ai_generated`) or
  legitimately-shared ENGLISH target-answer text (all three overlays
  teach the same English realization, so identical correct answers are
  expected, not contamination) — zero matches in the actual Dutch
  prose. Read a sample of the Dutch directly: genuinely natural,
  idiomatic, with real Dutch-specific contrastive-grammar notes (e.g.
  explaining English "you" collapses jij/u, do-support in questions,
  a/an vs "een", the vs de/het).
  - Fresh-context review fixed an overbroad question-word-order
    explanation, replaced a distractor that was actually also a valid
    English echo-question, removed untaught distractor vocabulary, and
    improved several stilted Dutch notes.
  - Both units now `status: reviewed`, `required_next_reviewer: null`.
    0 errors/0 warnings.

**Net state**: nl unit01 is fully authored and AI-reviewed in both
directions (en→nl and nl→en) and is the most complete single unit in
the project outside fa/prs. It has NOT been imported into any running
course, backfilled into the Lexeme table, or browser-verified — that
needs Session 1 (Docker owner) plus Ramin's native review, in whatever
order makes sense to them. I did not touch Docker, migrations, or any
code file this session, per the CONTENT lane boundary.

**New context absorbed mid-session** (found by reading the
Session-1/3-updated CLAUDE.md, not told directly): publish-gate scope
narrowed to en↔nl and en↔fa/prs only (6 paths) — es/fr and the rest
are post-launch drip content. This retroactively confirms tonight's
prioritization (finish es/fr's in-flight review, then focus on nl) was
correct per the actual current plan of record, not just the version of
the plan visible when the night started. Also noted: Endless Practice
(built earlier this session, fa-en only so far) is now a stated
publish-gate requirement to extend to all 6 launch paths — that will
need practice-template-pack authoring for en-fa (partial - unit1/2
exist)/fa-en/en-prs/prs-en/en-nl/nl-en once each language's core
content is stable. Flagging for whoever picks up practice-pack work
next; have not started this.

## 2026-07-05 overnight, continued — nl unit02 (numbers) authored + reviewed

`docs/content/realizations/nl/a1_unit02_numbers.yaml` +
`docs/content/overlays/en-nl/a1_unit02.yaml` — covers
`universal.a1.numbers.use_basic_numbers`. 6 lessons (0-12, teens/tens
inversion, phone/house numbers, ages/quantities, euro prices,
integrated registration dialogue), continuing unit01's
Lotte/Omar/taalcafé continuity. Independently verified the trickiest
part by hand (Dutch tens-inversion + diaeresis rules: eenentwintig=21,
tweeënveertig=42, etc. — all correct). Fresh-context review found no
number-formation errors, fixed some overlay wording (jargon
simplification, missing answer variants). `status: reviewed`,
`required_next_reviewer: null`, 0 errors/0 warnings solo and combined
with unit01.

**Running content-depth tally toward the ≥10hr publish-gate target**:
2 of ~22 estimated nl units done (en→nl direction only so far;
nl→en direction currently only has unit01+02 via the existing shared
English realization, done earlier). This is a large remaining gap —
flagging so whoever picks this up next doesn't assume it's close to
done. Continuing unit-by-unit as of this note.

## 2026-07-05 overnight, continued — nl unit03 (dates) authored + reviewed

`docs/content/realizations/nl/a1_unit03_dates.yaml` +
`docs/content/overlays/en-nl/a1_unit03.yaml` — covers
`universal.a1.dates.exchange_calendar_dates` (depends on unit02's
numbers, correctly built on top rather than re-taught). 6 lessons
(weekdays, months, ordinals 1st-31st, asking/stating dates, a library
due-date scenario, closing dialogue), day-month-year order throughout,
lowercase weekday/month convention enforced, full irregular-ordinal
set (eerste/derde/achtste/elfde/twaalfde etc.) hand-verified correct.

**Real bug caught by the fresh-context review, not by my own
spot-check**: the authored content asserted "Friday 12 April 2026" in
one exercise — 12 April 2026 is actually a Sunday (verified by hand:
`python3 -c "import datetime; print(datetime.date(2026,4,12).strftime('%A'))"`
→ Sunday). Fixed to Friday 12 April 2024 (verified correct). I had
only spot-checked the *dialogue's* 2024 dates in my own review of the
authoring pass and missed this separate 2026-dated exercise elsewhere
in the file — worth remembering that a single spot-check of "the
obvious dates" isn't the same as checking every date instance in a
file; this is exactly why the independent fresh-context review pass
matters even after the driving session's own check.

`status: reviewed`, `required_next_reviewer: null`, 0 errors/0
warnings solo and combined with unit01+02.

**Content-depth tally**: 3 of ~22 estimated nl units done (en→nl
direction). Continuing.

## 2026-07-05 overnight, continued — nl unit04 (time) authored + reviewed; Codex rate-limited

`docs/content/realizations/nl/a1_unit04_time.yaml` +
`docs/content/overlays/en-nl/a1_unit04.yaml` — covers
`universal.a1.time.ask_tell_time`. Correctly handles Dutch's
notorious half-before-the-hour convention (half drie=2:30, half
vier=3:30 — verified consistent throughout, e.g. "half drie, dus om
14.30 uur"), kwart over/voor, 24hr clock. Deliberately scoped out the
harder voor-half/over-half five/ten-minute interval system for A1
(confirmed absent via grep).

The review task technically reported `status: "failed"` — Codex hit a
usage/rate limit ("try again at 5:16 AM", timezone unconfirmed) while
composing its final report, AFTER its actual edits were already
applied. Verified this myself rather than assuming the work was lost:
compiler validation 0/0 (solo and combined with units 1-3), review
block shows `status: reviewed` with specific real notes, no
voor-half/over-half drift, all media_asset_key references resolve to
declared assets except one legitimately unused declared-but-unreferenced
asset (`nl.a1.audio.time.two_oclock.01`) — minor, non-breaking, left
for the next Codex task to clean up rather than editing content myself
(not my lane). Net: unit04 is genuinely done despite the wrapper
task's "failed" status — don't assume "failed" always means lost work,
but don't skip re-verifying either.

**Codex is rate-limited as of ~04:06 BST.** Pausing new Codex
dispatches until a retry succeeds. If you're reading this and it's
now well past 5:16 AM your time and nothing further has happened,
Codex may still be limited or something else stalled — check
`codex login status` and try a small task manually before assuming
the pipeline is just idle-by-design.

**Content-depth tally**: 4 of ~22 estimated nl units done (en→nl
direction).

## 2026-07-05 overnight, continued — Codex still rate-limited; authored nl unit05 myself as a stopgap

Per Ramin's explicit direction ("continue whatever codex was working
on before it got interrupted... check codex later to hand over"), I
authored `docs/content/realizations/nl/a1_unit05_family.yaml` +
`docs/content/overlays/en-nl/a1_unit05.yaml` directly myself (covers
`universal.a1.family.describe_relationships`) rather than idling.
6 lessons: immediate family, extended family (with an explicit note
that neef/nicht are genuinely ambiguous in Dutch — male
cousin/nephew and female cousin/niece share one word each — and
deliberately NOT tested in an exercise, only flagged for recognition),
mijn/je/jouw, zijn/haar, a written family profile (Lotte), a closing
Lotte/Omar dialogue. Deliberately avoided onze/ons (our) to sidestep
the de/het gender-agreement complexity at A1 — used only the
gender-invariant possessives (mijn/je/jouw/zijn/haar).

Caught and fixed one real bug in my own draft via the compiler's
untaught-vocabulary validator (not a rubber stamp — it actually
caught something): an exercise's tested_text referenced "taalcafe"
(the recurring setting from unit01) without re-introducing it locally
in unit05, and without the accent to match "taalcafé". Fixed by
rewording the tested_text to only use tokens genuinely introduced
within unit05 itself. Also caught and fixed a stray leftover
placeholder overlay entry from my own drafting process before even
running the validator.

Validated: unit05 solo = 0 errors/0 warnings; combined with units
01-04 = 0 errors/0 warnings.

**IMPORTANT — this is authored-but-UNREVIEWED, explicitly.** Both
files' review blocks are `status: unreviewed`,
`required_next_reviewer: claude`, and say so honestly in their notes.
I did NOT mark this reviewed myself — a same-session author cannot
also be the fresh-context reviewer, that defeats the entire point of
the review step this project has relied on all night to catch real
bugs (see: the Belgium-language ambiguity, the wrong calendar weekday,
the unconstrained-distractor bugs, etc. — all caught by review, not
by the author's own check). **Next Codex session/task: run the same
fresh-context review cycle on unit05 that every other unit has
gotten, before it's considered done.**

Codex hit a usage/rate limit at ~04:06 BST tonight ("try again at
5:16 AM", timezone unconfirmed). Checked again at 04:19 BST — likely
still too early to retry meaningfully. Continuing to author further
units myself in the meantime per Ramin's direction, accumulating a
review backlog for whenever Codex is back, rather than idling.

**Content-depth tally**: 5 of ~22 estimated nl units exist (en→nl
direction), but unit05 specifically needs its review before it counts
as "done" the way units 1-4 do.

## 2026-07-05 overnight, continued — nl unit06 (food) authored myself, also unreviewed

`docs/content/realizations/nl/a1_unit06_food.yaml` +
`docs/content/overlays/en-nl/a1_unit06.yaml` — covers
`universal.a1.food.order_simple_meal`. 6 lessons (drinks, "Ik wil
graag" ordering phrase, quantities + alstublieft/alsjeblieft register
split, wilt-u/wil-je formal-informal question forms with the correct
t-drop-in-inversion rule, menu reading, closing taalcafé ordering
dialogue with staff). Continues the jij/je vs u register thread from
unit01, now applied to a formal service interaction (Lotte orders
formally from café staff despite being informal with Omar).

Caught and fixed two more real bugs myself via the compiler (same
validator that's been catching real issues all night, not a rubber
stamp): (1) used "appelsap" (apple juice) without ever teaching it as
its own compound-word vocabulary item — Dutch compounds don't
decompose into their parts for the untaught-vocabulary check, teaching
"appel" and "sap" separately does not cover "appelsap"; added an
explicit teaching card. (2) three exercises' tested_text used
descriptive words never actually taught (goedkoopst/bestelt/besteld) —
reworded to only reference already-introduced tokens.

Validated: unit06 solo = 0/0; combined with units 01-05 = 0/0.

**Also authored-but-UNREVIEWED**, same as unit05 — both need Codex's
fresh-context review before being considered done.

**Content-depth tally**: 6 of ~22 estimated nl units exist (en→nl
direction); units 05-06 specifically are pending review.

Codex still showing rate-limited as of ~04:25 BST (haven't wasted a
real attempt testing since too little time has passed since the
04:06 failure — will test again after a longer gap).

## 2026-07-05 overnight, continued — Codex back online, nl unit05 reviewed

Codex usage limit reset (confirmed working again ~04:35 BST, roughly
30 min after the failure, closer to the local-time interpretation of
"5:16 AM" than I'd assumed — though still not fully clear which
timezone that was).

Fresh-context review of my self-authored unit05 found REAL issues,
validating the decision not to review my own work: a listening
exercise referenced the full multi-line dialogue audio instead of a
dedicated short clip for "Ja, elke maand"; two recognition/production
pacing regressions; two production prompts broader than their
accepted-answer lists actually supported; one ungrammatical
distractor; and — notably — **I had personally introduced the exact
jargon-leak bug class this project keeps finding**, using raw
linguistics terms ("invariant", "plural subject") directly in
learner-facing teaching notes. Confirmed neef/nicht ambiguity claim
and de/het claims via cited dictionary sources, confirmed not tested
in any exercise. `status: reviewed`, `required_next_reviewer: null`,
0/0 solo and combined with units 1-4 (independently re-verified, not
just trusted).

**Lesson reinforced**: even the driving/orchestrating session isn't
immune to the mistakes it's been catching all night — this is exactly
why the fresh-context review step can't be skipped or self-administered,
regardless of who authored the draft.

nl unit06 (food) still needs the same review — queuing next.

## 2026-07-05 overnight, continued — nl unit06 reviewed; review backlog cleared

`docs/content/overlays/en-nl/a1_unit06.yaml` review found real issues
too: menu prices weren't in standard Dutch notation (fixed to €2,50
comma-decimal format), an ambiguous duplicate-price matching pair,
narrow accepted-answer coverage, a pacing regression, and — same
pattern as unit05 — a listening exercise reused the full multi-line
dialogue audio instead of a dedicated short clip for "Komt eraan!".
Confirmed the wilt-u/wil-je t-drop grammar claim against Onze Taal
(cited sources), confirmed appelsap is explicitly taught as its own
token. `status: reviewed`, `required_next_reviewer: null`, 0/0 solo
and combined with units 1-5 (independently re-verified).

**Review backlog from the Codex outage is now fully cleared** — all 6
nl units (en→nl direction) are authored AND reviewed:
1. Greetings (jij/je vs u)
2. Numbers
3. Dates
4. Time (half-hour convention)
5. Family (possessives)
6. Food ordering

Recurring pattern worth noting for future units: BOTH of my
self-authored units had the same "reused full dialogue audio for a
short exercise instead of a dedicated clip" issue — I should watch for
this myself before handing off, not just rely on review to catch it
every time.

Codex is confirmed fully back online. Resuming normal Codex-authored
content from here (next: nl unit07, or whatever Ramin/the next session
prioritizes).

## 2026-07-05 overnight, continued — nl unit07 (shopping/market) authored + reviewed, fully Codex

`docs/content/realizations/nl/a1_unit07_shopping.yaml` +
`docs/content/overlays/en-nl/a1_unit07.yaml` — covers
`universal.a1.shopping.ask_prices_quantities`, first unit authored
entirely by Codex since the rate-limit recovery. 6 lessons (market
vocabulary, asking/stating prices per kilo, kilo/gram/pond/stuk
quantities, reading price labels, paying, closing market dialogue).
Deliberately distinct from unit06 (café ordering) — general produce
shopping instead. Consistent formal u/alstublieft register with the
unfamiliar vendor throughout.

Explicitly avoided both pitfalls from my earlier self-authored units
(flagged in the authoring prompt): dedicated audio clips per exercise
throughout, "prijskaartje" (price tag) taught as its own compound
token.

Review found: a real €3.00/€2.50 price inconsistency between a
listening exercise and the capstone dialogue total (fixed), and
refined the "een pond = 500g" claim with better sourcing — clarified
it's informal/traditional usage, not an official metric unit, and
cited the precise international pound value (453.59237g) rather than
a rough approximation. `status: reviewed`, `required_next_reviewer:
null`, 0/0 solo and combined with units 1-6 (independently
re-verified).

**Content-depth tally**: 7 of ~22 estimated nl units done (en→nl
direction), all authored and reviewed. Codex fully operational again.

## 2026-07-05 overnight, continued — nl unit08 (places) authored + reviewed

`docs/content/realizations/nl/a1_unit08_places.yaml` +
`docs/content/overlays/en-nl/a1_unit08.yaml` — covers
`universal.a1.places.locate_common_places`. 6 lessons (7 everyday
places, naast/tegenover, achter/voor, tussen/bij/in de buurt van +
"Waar is...?", reading a neighbourhood map, closing dialogue locating
the bus stop/supermarket/library). Correctly stayed within
location-stating scope, no drift into turn-by-turn direction-giving
(verified: no linksaf/rechtsaf/rechtdoor vocabulary present) — that's
reserved for the next spine outcome. All compounds
(supermarkt/ziekenhuis/postkantoor/bushalte/buurtkaart) explicitly
taught, all 11 listen_* exercises confirmed using distinct dedicated
audio clips (the two-unit pattern of reusing full-dialogue audio for
short exercises has now been avoided cleanly by Codex three units in a
row). Review found only minor issues (jargon simplification, one weak
distractor). `status: reviewed`, `required_next_reviewer: null`, 0/0
solo and combined with units 1-7.

**Content-depth tally**: 8 of ~22 estimated nl units done (en→nl
direction), all authored and reviewed.

## 2026-07-05 overnight, continued — nl unit09 (directions) authored + reviewed

`docs/content/realizations/nl/a1_unit09_directions.yaml` +
`docs/content/overlays/en-nl/a1_unit09.yaml` — covers
`universal.a1.directions.ask_follow_basic_directions`. 6 lessons
(links/rechts/linksaf/rechtsaf/rechtdoor, bare-stem imperatives
ga/sla/loop, "Hoe kom ik vanaf hier bij...?", 1-2 step routes reusing
unit08's places/prepositions, reading a marked map route, closing
Lotte-gives-Omar-directions dialogue). Correctly built on unit08
rather than re-teaching it, correctly scoped to 1-2 step routes only
(no overbuilt multi-step complexity). Review caught a real
answer-key-honesty bug: an incomplete one-step answer was incorrectly
being accepted for an exercise that required a full two-step route.
`status: reviewed`, `required_next_reviewer: null`, 0/0 solo and
combined with units 1-8.

**Content-depth tally**: 9 of ~22 estimated nl units done (en→nl
direction), all authored and reviewed. Session 1 has meanwhile started
Phase F (CheckpointPage.tsx observed) — unit checkpoint tests, now a
hard publish-gate requirement per the earlier scope decision.

## 2026-07-05 overnight, continued — nl unit10 (routines) authored + reviewed; new FSI-adaptation directive

`docs/content/realizations/nl/a1_unit10_routines.yaml` +
`docs/content/overlays/en-nl/a1_unit10.yaml` — covers
`universal.a1.routines.describe_daily_routine`. Correctly modeled
Dutch separable verbs (opstaan/aankleden/afwassen) with the prefix
split to clause-end in every example, including with time expressions
and reflexives in between, plus correct V2 word order after
eerst/dan/daarna. Review caught a real person-agreement bug (a
tested_text mismatch used "Omar" where the dialogue's first-person
"ik" was required) and a weak distractor. `status: reviewed`,
`required_next_reviewer: null`, 0/0 solo and combined with units 1-9.

**Content-depth tally**: 10 of ~22 estimated nl units done (en→nl
direction), all authored and reviewed.

**New directive, verified against the actual source docs (not just
taken on faith from the paste)**: `docs/content/AUTHORING_GUIDE.md`
§10 (added 2026-07-05) confirms FSI/Peace Corps course material for
nl/fa/prs is genuine US-government public domain — usable as a real
scaffold (vocabulary progression, grammar sequencing, dialogue
scenarios) with a MANDATORY modernization pass, never verbatim.
CLAUDE.md's division-of-labor section confirms Claude (not just Codex)
can now author content directly via this adaptation lane specifically
— a different task shape from Codex's from-scratch generation, same
identical review/validation bar, no shortcut. Priority: push this at
the ≥10hr content target for en-nl/en-fa/prs. Investigating actual FSI
source material availability next (Live Lingua / archive.org).

## 2026-07-05 overnight, continued — FSI/DLI scaffold investigation: inconclusive, deferred

Investigated actual availability of public-domain scaffold material for
Dutch per the new AUTHORING_GUIDE.md §10 directive. Findings:
- Live Lingua (livelingua.com) hosts DLI (Defense Language Institute)
  Dutch material, not "FSI" by that exact name — but DLI is the same
  category of US government work (17 USC 105 public-domain rationale
  applies equally), and Live Lingua's own site copy states DLI courses
  are public domain. Reasonable to treat as covered by the same
  directive, though it's technically DLI not FSI — flagging the
  substitution explicitly rather than silently treating the names as
  interchangeable.
- Installed poppler (`brew install poppler`) to actually read a
  fetched PDF directly rather than trust WebFetch's summary of it
  (WebFetch alone couldn't parse the binary PDF content at all).
- The actual "Book 1" PDF (https://www.livelingua.com/dli/Dutch/book
  1/DLI Dutch - Book 01 Part 01.pdf) is explicitly titled, on its own
  cover page, "AN INTERMEDIATE-ADVANCED LEVEL DUTCH REFRESHER COURSE"
  (1961, Defense Language Institute / English Language Services Inc.)
  — its unit topics (The Delta Plan, Elections in Holland, A Dutch
  Delicacy, The Fresh Water Shortage) are intermediate-advanced
  narrative/current-events content, not A1 beginner survival
  vocabulary. This directly contradicts the catalog page's generic
  blurb calling it a "Beginner Level Dutch Refresher Course" — trusted
  the PDF's own title page (primary source) over the catalog summary.
- Did not locate a confirmed genuinely-beginner-level Dutch DLI/FSI
  course within a reasonable time budget tonight.

**Decision**: not sinking further overnight time into sourcing the
right document. Continuing nl unit11 onward via the proven
from-scratch Codex authoring + fresh-context review cycle, which has
produced 10/10 solid, independently-verified units so far. Flagging
for whoever picks up the FSI-adaptation lane next: the right starting
point is probably checking Live Lingua's fa/prs (Persian/Dari) FSI
listings instead, since those were the languages explicitly named in
the original Fable planning conversation as having confirmed FSI
courses — Dutch's public-domain scaffold may need a different source
entirely (e.g. archive.org directly, or a different DLI/FSI Dutch
title than the one found tonight).

## 2026-07-05 overnight — coordination note for Session 3 (now also doing content work)

Session 3 (INFRA) is picking up Endless Practice template-pack
extension (docs/content/practice/**) per the publish-gate's "≥10hrs
practice via Endless Practice, not hand-authored drills" requirement.
To avoid duplicate/colliding Codex dispatches:

- **My (Session 2) exclusive scope**: core teaching units —
  `docs/content/realizations/nl/**` and
  `docs/content/overlays/en-nl/**` (also `nl-en/**`, done). Currently
  11/11 nl units authored+reviewed (greetings through plans). Not
  touching `docs/content/practice/**` at all.
- **Session 3's scope**: `docs/content/practice/**` template packs.
  The existing pilot (fa-en, units 1-2, 72 templates) is the reference
  pattern — see the Endless Practice build history earlier in
  `docs/BUILD_LOG.md` for the template schema and the same
  author→validate→fresh-context-review cycle applies there too.
  Suggest Session 3 claim en-fa/en-prs (the other two publish-gate
  languages) or nl once enough nl teaching units exist to give the
  lexeme pool real depth — either works from my side, just pick one
  and note it here or in its own log so we don't both dispatch a
  "nl practice pack" Codex task at the same time.

Continuing nl core units (unit12 next) and the native-review loop
with Ramin on completed units in the meantime.

## 2026-07-05 overnight, continued — nl unit11 (plans) authored + reviewed

`docs/content/realizations/nl/a1_unit11_plans.yaml` +
`docs/content/overlays/en-nl/a1_unit11.yaml` — covers
`universal.a1.plans.make_simple_plans`. 6 lessons (Zullen we...?/Heb
je zin om...?, accepting/declining, date+time scheduling reusing
units 03/04, reading an invitation, writing a plan message, closing
Lotte/Omar negotiation dialogue). Review caught a real narrative-logic
bug: coffee was proposed "after the taalcafé" at 2:30, the exact time
the café starts per unit04 — internally inconsistent timing, fixed.
Also verified 17/18 April 2026 genuinely fall on Friday/Saturday
(independently re-confirmed by hand). `status: reviewed`,
`required_next_reviewer: null`, 0/0 solo and combined with units 1-10.

**Content-depth tally**: 11 of ~22 estimated nl units done (en→nl
direction), all authored and reviewed.

## 2026-07-05 — nl unit12 (past events) authored+reviewed; first Claude-direct-authored content (fa unit05)

**nl unit12 (past events)**: `docs/content/realizations/nl/a1_unit12_past_events.yaml` +
`docs/content/overlays/en-nl/a1_unit12.yaml` — covers
`universal.a1.past_events.describe_recent_event`. Correctly modeled the
Dutch perfect tense (hebben/zijn + participle) as the everyday past-tense
default. Verified every participle by hand: drinken→gedronken(hebben),
eten→gegeten(hebben), werken→gewerkt(hebben), kopen→gekocht(hebben),
gaan→gegaan(zijn), komen→gekomen(zijn), doen→gedaan(hebben) — all
correct. 0/0 solo and combined with units 1-11. **12 of ~22 estimated
nl units now done.**

**IMPORTANT — real cross-session collision found and resolved**: while
starting the first Claude-direct-authored content (per the repeated
FSI-adaptation directive), I initially wrote `fa/a1_unit03_places.yaml`
+ `en-fa/a1_unit03.yaml` before checking — another session had ALREADY
authored a DIFFERENT fa unit03 (Numbers) and fa unit04 (Family), both
already through one review round. My overlay Write was safely blocked
by the tool (file existed, hadn't been read first) before any damage;
my realization Write had gone through since that exact filename didn't
collide, but the content_keys did (`fa.a1.unit03.*` used by both).
**Renamed my files+content_keys to unit05** (`a1_unit05_places.yaml`,
`en-fa/a1_unit05.yaml`) before any real harm — verified 0 remaining
`unit03` references via grep, validated clean solo and combined with
units 3-4.

**Also found while validating**: fa units 01 and 02 have a **pre-existing,
unrelated compiler incompatibility** — a dialogue-schema requirement
(one text_block per speaker turn, no embedded multi-speaker labels
with newlines) has apparently landed in compile_content.py since those
units were originally authored, and they haven't been migrated to the
new format. This affects the ORIGINAL fa content from earlier in the
project, not anything from tonight. Confirmed it's unrelated to my
work: units 3-4-5 validate cleanly together; only 1+2 fail. **Flagging
for whoever owns compile_content.py's schema changes or fa unit01/02 —
this needs a migration pass on those two files before the full fa
course can compile end-to-end again.** I did not attempt to fix this
myself (out of scope, and restructuring already-reviewed dialogue
content risks introducing new errors without careful review).

**First Claude-direct-authored unit (fa unit05, places/directions)**:
adapted vocabulary scope (not sentences) from the confirmed
public-domain 1963 FSI "Persian Basic Course" (verified directly by
reading the actual PDF — Foreign Service Institute/Dept. of State,
reprinted by the Center for Applied Linguistics, explicit permission
acknowledgment on the copyright page). 4 lessons (hotel/restaurant
vocab, right/left, straight-ahead + asking directions, closing
dialogue where Sara asks a stranger for the Azadi hotel). Caught and
fixed my own dialogue-format mistake before even sending for review
(split a combined two-speaker card into two single-speaker cards,
matching unit04's established correct pattern). Sent for a
fresh-context review with EXPLICIT instructions to scrutinize it at
least as rigorously as Codex output, since Claude (unlike Codex) has
no proven track record on Persian this session — review in progress,
will report the honest verdict once it lands, including if it turns
out NOT to be native-quality.
