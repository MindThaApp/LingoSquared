# Native-gloss worklist — en.a2.unit35–unit40 (fa-en + prs-en)

## What this is

To publish the **X→en practice checkpoints** for English A2 units 35–40, each
direction's lexeme-backfill script must emit a lexeme for every newly-taught
English token whose **gloss is the learner's native (L1) word** for that token.

- `scripts/backfill_lexemes_fa_en.py` — Farsi glosses — currently stops at
  **unit34** (its `FA_EN_EXTRA_LEXEMES` dict jumps a2 unit34 → b1 unit01).
- `scripts/backfill_lexemes_prs_en.py` — Dari glosses — currently stops at
  **unit34** (same gap).

The **nl-en** direction is already done (`scripts/backfill_lexemes_nl_en.py`,
units 35–40 added). The token set below is taken **exactly** from the tokens
nl-en added for these six units — the authoritative "newly-taught" set. Tokens
already introduced in earlier units (e.g. *pharmacy, tablet, camera, neighbor,
offer, order, damaged, broken, replacement, message, reschedule, key, fixed*)
are **already glossed** in both the fa-en and prs-en dicts and are intentionally
**not** listed here.

The `POS` column and its example sense come straight from the source realization
files under `docs/content/realizations/en/`. A non-native must not invent Farsi
or Dari — every native-gloss cell is left blank on purpose.

## How to use it

1. A **native Farsi** reviewer fills the `Farsi gloss` blanks in the fa-en
   section; a **native Dari** reviewer fills the `Dari gloss` blanks in the
   prs-en section. Gloss the **sense in the "Intended sense / context" column**,
   not the token's most common dictionary meaning (several are homographs —
   see the flags at the bottom).
2. Hand the filled sheet back. The glosses are then transcribed into each
   script's own dict, keeping that script's existing entry format:
   - **fa-en** → add to `FA_EN_EXTRA_LEXEMES` as
     `"token": ("pos", "‹farsi›"),` grouped under a
     `# --- a2 unitNN: <title> ---` comment.
   - **prs-en** → add to the prs gloss dict as `"token": "‹dari›",` grouped
     under a `# -- a2 unitNN (<title>)` comment (POS comes from the shared
     `EN_POS`, so no tuple is needed).
3. Symbols/numbers (3092, 8154, 9am, 11am) are **not** translations — they only
   need the correct native-numeral / native time rendering (the existing dicts
   already do this, e.g. `"30": "۳۰"`, `"5:15": "۵:۱۵"`). The reviewer should
   supply the native-numeral form, or confirm the digits stay as-is.

## Count summary

| Unit | content_key | Tokens |
|------|-------------|-------:|
| unit35 | en.a2.unit35.prescription | 6 |
| unit36 | en.a2.unit36.document_correction | 10 |
| unit37 | en.a2.unit37.video_calls | 10 |
| unit38 | en.a2.unit38.repair_visit | 5 |
| unit39 | en.a2.unit39.after_the_interview | 4 |
| unit40 | en.a2.unit40.online_order_problem | 4 |

- **Grand total per direction: 39 tokens**
- **Both directions combined: 78 glosses needed**

The two sections below cover the **same 39 tokens** with the same intended
senses — only the blank column differs (Farsi vs Dari).

---

## fa-en (Farsi glosses needed)

### en.a2.unit35.prescription

| English token | POS | Intended sense / context | Farsi gloss |
|---------------|-----|--------------------------|-------------|
| dose | noun | amount of medicine to take — "The dose is one tablet twice a day." (nl: *de dosis*) |  |
| refill | noun | a repeat/renewal of a prescription — "I need a refill because my tablets are almost finished." (nl: *de herhaalmedicatie*) |  |
| side | noun | **only** the "side" in **side effects** — NOT a physical side/direction — "the side effects of this medicine" (nl: *de bijwerking (in side effects)*) |  |
| effects | noun | (side) effects of medicine — "the side effects of this medicine" (nl: *de bijwerkingen*) |  |
| shouldn't | verb | should not — negative advice/instruction — "You shouldn't stop early." (nl: *zou niet moeten*) |  |
| refills | noun | plural of refill — prescription refills — "How many refills does the label allow?" (nl: *de herhaalmedicatie*) |  |

### en.a2.unit36.document_correction

| English token | POS | Intended sense / context | Farsi gloss |
|---------------|-----|--------------------------|-------------|
| certificate | noun | an official document/certificate — "My registration certificate arrived two weeks after the appointment." (nl: *het officiële bewijs*) |  |
| spelled | verb | past/participle of *spell* — "My name is spelled with one L, not two." (nl: *gespeld*) |  |
| copy | noun | a duplicate of a document (NOT the verb "to copy") — "The office keeps a copy of every document." (nl: *de kopie*) |  |
| passport | noun | passport — "I always bring my passport to an official appointment." (nl: *het paspoort*) |  |
| mistakes | noun | plural of mistake — errors in a document — "There are two mistakes on my certificate." (nl: *de fouten*) |  |
| registration | noun | registration (as in *registration certificate/office*) — "Your registration certificate will be corrected." (nl: *de inschrijving*) |  |
| correction | noun | a correction (the act/result of correcting) — "How long will the correction take?" (nl: *de correctie*) |  |
| corrected | verb | past participle of *correct* — "will be corrected within five working days." (nl: *gecorrigeerd*) |  |
| reference | noun | reference, as in **reference number** — "Reference number 3092." (nl: *de referentie*) |  |
| 3092 | symbol | a reference number (native-numeral rendering) — "Reference number 3092." (nl: *3092*) |  |

### en.a2.unit37.video_calls

| English token | POS | Intended sense / context | Farsi gloss |
|---------------|-----|--------------------------|-------------|
| microphone | noun | microphone — "My microphone was off, so nobody could hear me." (nl: *de microfoon*) |  |
| connection | noun | network/internet connection — "The connection was bad, so the video stopped." (nl: *de verbinding*) |  |
| mute | verb | to mute (a microphone) — "I mute my microphone when I am not speaking." (nl: *dempen*) |  |
| face | noun | **only** the "face" in **face to face** (= in person) — NOT the body part in isolation — "meetings are better face to face than online." (nl: *het gezicht (in face to face)*) |  |
| calls | noun | plural — **video calls** (noun, not the verb, not phone calls) — "I think video calls are useful." (nl: *de gesprekken*) |  |
| headphones | noun | headphones — "I use headphones so my family cannot hear the meeting." (nl: *de koptelefoon*) |  |
| asks | verb | 3rd-person singular of *ask* — "until the teacher asks a question." (nl: *stelt*) |  |
| question | noun | a question — "the teacher asks a question." (nl: *de vraag*) |  |
| classmates | noun | fellow students — "I prefer meeting my classmates face to face." (nl: *de medestudenten*) |  |
| speaking | verb | present participle of *speak* — "I mute my microphone when I am not speaking." (nl: *pratend*) |  |

### en.a2.unit38.repair_visit

| English token | POS | Intended sense / context | Farsi gloss |
|---------------|-----|--------------------------|-------------|
| leak | noun | a water leak — "The leak under my kitchen sink is getting worse." (nl: *de lekkage*) |  |
| won't | verb | will not — "I won't be home in the afternoon." (nl: *zal niet*) |  |
| rescheduled | verb | past/participle of *reschedule* — "Repair 6180 has been rescheduled." (nl: *verzet*) |  |
| 9am | symbol | a clock time, 9:00 in the morning (native time rendering) — "between 9am and 11am." (nl: *9.00 uur*) |  |
| 11am | symbol | a clock time, 11:00 in the morning (native time rendering) — "between 9am and 11am." (nl: *11.00 uur*) |  |

### en.a2.unit39.after_the_interview

| English token | POS | Intended sense / context | Farsi gloss |
|---------------|-----|--------------------------|-------------|
| contract | noun | an employment contract — "The contract is for one year." (nl: *het contract*) |  |
| salary | noun | salary/pay — "We can talk about the salary next week." (nl: *het salaris*) |  |
| accept | verb | to accept (a job offer/position) — "I would like to accept the position." (nl: *aannemen*) |  |
| interested | adjective | interested (in a job) — "I am still very interested in the position." (nl: *geïnteresseerd*) |  |

### en.a2.unit40.online_order_problem

| English token | POS | Intended sense / context | Farsi gloss |
|---------------|-----|--------------------------|-------------|
| delivery | noun | a delivery (of goods) — "The delivery came on Tuesday morning." (nl: *de bezorging*) |  |
| parcel | noun | a parcel/package — "The parcel was left outside my door." (nl: *het pakket*) |  |
| lamp | noun | a lamp (the ordered item) — "The lamp inside the parcel was broken." (nl: *de lamp*) |  |
| 8154 | symbol | an order number (native-numeral rendering) — "My order number is 8154." (nl: *8154*) |  |

---

## prs-en (Dari glosses needed)

### en.a2.unit35.prescription

| English token | POS | Intended sense / context | Dari gloss |
|---------------|-----|--------------------------|------------|
| dose | noun | amount of medicine to take — "The dose is one tablet twice a day." (nl: *de dosis*) |  |
| refill | noun | a repeat/renewal of a prescription — "I need a refill because my tablets are almost finished." (nl: *de herhaalmedicatie*) |  |
| side | noun | **only** the "side" in **side effects** — NOT a physical side/direction — "the side effects of this medicine" (nl: *de bijwerking (in side effects)*) |  |
| effects | noun | (side) effects of medicine — "the side effects of this medicine" (nl: *de bijwerkingen*) |  |
| shouldn't | verb | should not — negative advice/instruction — "You shouldn't stop early." (nl: *zou niet moeten*) |  |
| refills | noun | plural of refill — prescription refills — "How many refills does the label allow?" (nl: *de herhaalmedicatie*) |  |

### en.a2.unit36.document_correction

| English token | POS | Intended sense / context | Dari gloss |
|---------------|-----|--------------------------|------------|
| certificate | noun | an official document/certificate — "My registration certificate arrived two weeks after the appointment." (nl: *het officiële bewijs*) |  |
| spelled | verb | past/participle of *spell* — "My name is spelled with one L, not two." (nl: *gespeld*) |  |
| copy | noun | a duplicate of a document (NOT the verb "to copy") — "The office keeps a copy of every document." (nl: *de kopie*) |  |
| passport | noun | passport — "I always bring my passport to an official appointment." (nl: *het paspoort*) |  |
| mistakes | noun | plural of mistake — errors in a document — "There are two mistakes on my certificate." (nl: *de fouten*) |  |
| registration | noun | registration (as in *registration certificate/office*) — "Your registration certificate will be corrected." (nl: *de inschrijving*) |  |
| correction | noun | a correction (the act/result of correcting) — "How long will the correction take?" (nl: *de correctie*) |  |
| corrected | verb | past participle of *correct* — "will be corrected within five working days." (nl: *gecorrigeerd*) |  |
| reference | noun | reference, as in **reference number** — "Reference number 3092." (nl: *de referentie*) |  |
| 3092 | symbol | a reference number (native-numeral rendering) — "Reference number 3092." (nl: *3092*) |  |

### en.a2.unit37.video_calls

| English token | POS | Intended sense / context | Dari gloss |
|---------------|-----|--------------------------|------------|
| microphone | noun | microphone — "My microphone was off, so nobody could hear me." (nl: *de microfoon*) |  |
| connection | noun | network/internet connection — "The connection was bad, so the video stopped." (nl: *de verbinding*) |  |
| mute | verb | to mute (a microphone) — "I mute my microphone when I am not speaking." (nl: *dempen*) |  |
| face | noun | **only** the "face" in **face to face** (= in person) — NOT the body part in isolation — "meetings are better face to face than online." (nl: *het gezicht (in face to face)*) |  |
| calls | noun | plural — **video calls** (noun, not the verb, not phone calls) — "I think video calls are useful." (nl: *de gesprekken*) |  |
| headphones | noun | headphones — "I use headphones so my family cannot hear the meeting." (nl: *de koptelefoon*) |  |
| asks | verb | 3rd-person singular of *ask* — "until the teacher asks a question." (nl: *stelt*) |  |
| question | noun | a question — "the teacher asks a question." (nl: *de vraag*) |  |
| classmates | noun | fellow students — "I prefer meeting my classmates face to face." (nl: *de medestudenten*) |  |
| speaking | verb | present participle of *speak* — "I mute my microphone when I am not speaking." (nl: *pratend*) |  |

### en.a2.unit38.repair_visit

| English token | POS | Intended sense / context | Dari gloss |
|---------------|-----|--------------------------|------------|
| leak | noun | a water leak — "The leak under my kitchen sink is getting worse." (nl: *de lekkage*) |  |
| won't | verb | will not — "I won't be home in the afternoon." (nl: *zal niet*) |  |
| rescheduled | verb | past/participle of *reschedule* — "Repair 6180 has been rescheduled." (nl: *verzet*) |  |
| 9am | symbol | a clock time, 9:00 in the morning (native time rendering) — "between 9am and 11am." (nl: *9.00 uur*) |  |
| 11am | symbol | a clock time, 11:00 in the morning (native time rendering) — "between 9am and 11am." (nl: *11.00 uur*) |  |

### en.a2.unit39.after_the_interview

| English token | POS | Intended sense / context | Dari gloss |
|---------------|-----|--------------------------|------------|
| contract | noun | an employment contract — "The contract is for one year." (nl: *het contract*) |  |
| salary | noun | salary/pay — "We can talk about the salary next week." (nl: *het salaris*) |  |
| accept | verb | to accept (a job offer/position) — "I would like to accept the position." (nl: *aannemen*) |  |
| interested | adjective | interested (in a job) — "I am still very interested in the position." (nl: *geïnteresseerd*) |  |

### en.a2.unit40.online_order_problem

| English token | POS | Intended sense / context | Dari gloss |
|---------------|-----|--------------------------|------------|
| delivery | noun | a delivery (of goods) — "The delivery came on Tuesday morning." (nl: *de bezorging*) |  |
| parcel | noun | a parcel/package — "The parcel was left outside my door." (nl: *het pakket*) |  |
| lamp | noun | a lamp (the ordered item) — "The lamp inside the parcel was broken." (nl: *de lamp*) |  |
| 8154 | symbol | an order number (native-numeral rendering) — "My order number is 8154." (nl: *8154*) |  |

---

## Reviewer flags (homographs / sense traps)

These tokens carry a **specific** sense that differs from the token's most
common standalone meaning — gloss the intended sense, not the default:

- **side** (unit35) — the "side" in **side effects** (medical), NOT a physical
  side or direction. nl deliberately glosses it *de bijwerking (in side effects)*.
- **effects** (unit35) — **side effects** of medicine specifically.
- **face** (unit37) — the "face" in **face to face** (= in person / meeting
  someone physically), NOT the body-part "face" in isolation. This is the known
  homograph class; nl glosses it *het gezicht (in face to face)* — the reviewer
  should confirm whether the native idiom for "face to face" needs a different
  word than the body part.
- **calls** (unit37) — the **noun** "video calls", NOT the verb "to call" and
  NOT phone calls.
- **copy** (unit36) — the **noun** (a document duplicate), NOT the verb "to copy".
- **reference** (unit36) — as in a **reference number** on a notice, NOT a
  personal/job reference.

## Notes on scope (for the transcriber)

- This list mirrors nl-en's per-unit additions **exactly** (39 tokens). Tokens
  taught in units 35–40 but first introduced earlier (*pharmacy, pharmacist,
  tablet, camera, neighbor, key, fixed, message, reschedule, offer, order,
  damaged, broken, replacement*) are already glossed in both fa-en and prs-en
  and were verified present — they are correctly **excluded**.
- No token in units 35–40 was ambiguous in the nl-en source: every entry maps
  to a single introduced sense in the realization files. The only items needing
  reviewer judgement are the homographs flagged above (the intended sense is
  named, so the reviewer only needs the right native word for that sense) and
  the four symbol/number tokens (native-numeral rendering).
