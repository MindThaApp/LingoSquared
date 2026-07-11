# Endless Practice variety audit — 2026-07-11

Prompted by Ramin's report that Endless Practice used to feel "full of
repeated words or slight variations of the same words repeated non
stop." This audit measures the **actual** learner-perceived variety of
the generated feed for all six launch directions, against a hard
learner-experience bar, and diagnoses the one real weakness it found.

**Bottom line:** the thing Ramin complained about — the *same word*
cycling back over and over — is **not happening**. Lexeme-level
repetition is well controlled in every direction (no word appears more
than 4× in 60 items, never 3× in a row, ≥20 distinct words in the first
20 items everywhere). The feed *does* still feel repetitive for four of
six directions, but the cause is **format monotony, not word
repetition**: for `nl-en`, `fa-en`, `prs-en`, and especially `en-prs`,
73–100% of generated items are the same shape — a bare single-word
`multiple_choice` "what does this word mean?" card. Same word, no; same
*kind of question* over and over, yes. Root cause and fix below.

## Method

Isolated stack (`docker compose -p lingo-varaudit`, DB
`lingosquared_varaudit`, never the shared dev DB). Fresh migrate →
imported all A1/A2/B1 content for the 6 launch courses via the real
`POST /admin/content/import` → ran all six `backfill_lexemes*.py`
scripts → imported every practice pack from
`scripts/practice_manifest.txt` via the real
`POST /admin/courses/{id}/practice/import` (A1: 347–386 templates per
direction; all 200 OK). A fresh learner registered through the real
API then completed real lessons and drew the feed through the exact
frontend endpoints — `POST /practice/{course_id}/batch` (size 10) with
every item answered through `POST /practice/items/{id}/answer` (~75%
correct / 25% wrong, deterministic) to advance the feed the way a real
session does. 70 items drawn per direction. Per-item lexeme / type /
rendered prompt read back from the DB.

Two learner states were tested, because the complaint is
pool-size-sensitive:

- **SMALL** — 2 units completed (~6–12 lessons), SRS pool 54–286
  lexemes. This is the early-learner regime where repetition is most
  likely — and the regime Ramin was almost certainly in when he
  noticed the problem.
- **BIG** — 8 units completed, SRS pool 195–607 lexemes. A learner a
  couple of weeks in.

## The bar

In any 60 consecutive items: no lexeme more than ~5×; no 3+ consecutive
items on the same word; ≥12 distinct lexemes in the first 20 items.

## Results

`d20/d40/d60` = distinct target lexemes in the first 20 / 40 / 60
items. `maxLex` = most appearances of any single lexeme in 60 items.
`runLex` = longest run of consecutive items on the same lexeme. `MC%` =
share of the 60 items that are `multiple_choice`. `dupPr` = count of
literal duplicate rendered prompts (same type + same text) within 60
items.

### SMALL (2 units done) — the complaint regime

| dir | pool | d20 | d40 | d60 | maxLex | runLex | MC% | dupPr | vs bar |
|-----|-----:|----:|----:|----:|-------:|-------:|----:|------:|--------|
| en-nl  | 189 | 20 | 40 | 60 | 1 | 1 | 77 | 0  | PASS |
| nl-en  | 110 | 20 | 33 | 33 | 4 | 1 | 73 | 16 | PASS |
| en-fa  | 286 | 20 | 40 | 60 | 1 | 1 | 18 | 4  | PASS |
| fa-en  | 54  | 20 | 40 | 40 | 3 | 1 | 78 | 12 | PASS |
| en-prs | 120 | 20 | 40 | 60 | 1 | 1 | 100| 0  | PASS |
| prs-en | 54  | 20 | 39 | 39 | 4 | 2 | 72 | 13 | PASS |

### BIG (8 units done)

| dir | pool | d20 | d40 | d60 | maxLex | runLex | MC% | dupPr | vs bar |
|-----|-----:|----:|----:|----:|-------:|-------:|----:|------:|--------|
| en-nl  | 429 | 20 | 40 | 60 | 1 | 1 | 73 | 0 | PASS |
| nl-en  | 404 | 20 | 40 | 60 | 1 | 1 | 87 | 0 | PASS |
| en-fa  | 607 | 20 | 40 | 60 | 1 | 1 | 20 | 4 | PASS |
| fa-en  | 196 | 20 | 40 | 60 | 1 | 1 | 95 | 0 | PASS |
| en-prs | 195 | 20 | 40 | 60 | 1 | 1 | 98 | 0 | PASS |
| prs-en | 196 | 20 | 40 | 60 | 1 | 1 | 90 | 1 | PASS |

**Every direction passes the lexeme-repetition bar in both regimes.**
Even the tightest pool (fa-en / prs-en, 54 lexemes) holds any single
word to ≤4 appearances across 60 items and never repeats a word 3× in
a row. The generator's "one item per scheduled lexeme before any
reinforcement repetition" pass plus the 50-item rolling signature
window are doing their job — the literal "same word non-stop" symptom
is gone.

The columns that tell the real story are **MC%** and **dupPr**.

## What still feels repetitive — and why

Look at the same 20-item opening for two directions, drawn from the
identical app with the identical fresh-learner state:

```
===== prs-en (English for Dari speakers) — first 20 items =====
 1. [multiple_choice] hello
 2. [multiple_choice] afternoon
 3. [multiple_choice] evening
 4. [multiple_choice] hi
 5. [multiple_choice] goodbye
 6. [multiple_choice] morning
 7. [multiple_choice] bye
 8. [multiple_choice] are
 9. [fill_in_blank ]  ___ are you?
10. [translation   ]  خوب
11. [multiple_choice] thanks
12. [translation   ]  خوب
13. [multiple_choice] i'm
14. [translation   ]  بد
15. [multiple_choice] nice
16. [multiple_choice] see
17. [multiple_choice] later
18. [multiple_choice] day
19. [multiple_choice] your
20. [multiple_choice] what
```

```
===== en-fa (Farsi) — first 20 items =====
 1. [multiple_choice]  ا
 2. [multiple_choice]  س
 3. [multiple_choice]  م
 4. [matching_pairs ]  Match each word with its meaning
 5. [multiple_choice]  ل
 6. [matching_pairs ]  کلمات را به معنی انگلیسی‌شان وصل کنید
 7. [word_order     ]  Put the words in order: *afternoon / evening* *good; well*
 8. [fill_in_blank  ]  خوبم، ممنون. ___
 9. [word_order     ]  از آشنایی با شما خوشوقتم
10. [translation    ]  thank you
11. [word_order     ]  خیلی خوبم
12. [translation    ]  your condition (polite)
13. [translation    ]  how is it?
14. [word_order     ]  *day* *good; well*
15. [matching_pairs ]  خداحافظ
16. [multiple_choice]  خواهش می‌کنم
17. [translation    ]  request; kindness
18. [word_order     ]  به امید دیدار
19. [word_order     ]  فعلاً
20. [translation    ]  به امید دیدار
```

`prs-en` is a wall of near-identical single-word recognition cards —
different words, but the same question shape every time, exactly the
"slight variations of the same thing repeated non-stop" feeling.
`en-fa`, in the same app and the same session length, is genuinely
varied: recognition, matching, sentence re-ordering, cloze, and
production all interleave. Note that these two transcripts are
**identical between the SMALL and BIG runs** for prs-en — the monotony
is not a thin-vocabulary artifact of early units; it is structural and
persists at an 8-unit / 196-lexeme pool (MC% 90–98).

The `dupPr` column is the same phenomenon at the prompt level: in the
tight pools, `nl-en` served 16 and `prs-en` 13 *literally identical*
`multiple_choice` prompts (e.g. `what`, `my`, `i`, `evening`, `okay`,
`fine`, `later` each recurring 2–3× across 60 items) — high-frequency
function words that the recognition templates keep re-surfacing.

## Root cause

The generator's format ladder (`_tier_order()` in
`backend/app/practice/service.py:525`) picks an exercise format by the
target lexeme's mastery:

```python
if mastery < 0.3:
    return RECOGNITION_TYPES, STRUCTURED_TYPES, PRODUCTION_TYPES   # MC/listen_select FIRST
if mastery <= 0.7:
    return STRUCTURED_TYPES, RECOGNITION_TYPES, PRODUCTION_TYPES
return PRODUCTION_TYPES, STRUCTURED_TYPES, RECOGNITION_TYPES
```

`_generate_target_item()` (line 665) walks these tiers **in order and
returns the first template that can build a valid item.** For a fresh
learner every lexeme sits below mastery 0.3, so the recognition tier
(`multiple_choice`, `listen_select`) is tried first — and in the
`X→en` and `en→prs` packs, the `multiple_choice` templates are broad
enough to fill for essentially *any* single lexeme. So recognition
always succeeds and the ladder short-circuits before it ever reaches
the abundant `word_order` / `translation` / `matching_pairs` templates
that also exist in the pool.

This is not a shortage of varied templates. The imported A1 pools are
well balanced — e.g. `en-prs` has 99 `multiple_choice`, 105
`translation`, 87 `word_order`, 80 `matching_pairs` templates — yet the
generated feed was 98–100% `multiple_choice`. The sentence-frame
templates are present; the tier-first selection simply never reaches
them for a beginner.

Why `en-fa` escapes: its `multiple_choice` templates are narrowly
tagged (they match letters and a few specific words, not arbitrary
lexemes), so for most lexemes the recognition tier *fails to build* and
the ladder correctly falls through to matching/word_order/translation.
`en-fa` is accidentally varied because its MC templates are
constrained; the `X→en`/`en-prs` packs are monotonous because theirs
are permissive.

## What I fixed vs. recommend

**Nothing implemented.** The lexeme-repetition bar passes everywhere,
so there is no correctness bug to fix. The format-monotony finding has
two possible levers, and neither is a small/obviously-safe content
edit:

1. **Engine-level (recommended, primary fix — Codex's lane).** Stop
   strictly exhausting the recognition tier before structured/
   production for low-mastery lexemes. Interleave formats within a
   session so a beginner still gets a mix — options, cheapest first:
   - cap consecutive same-type items (e.g. no more than 2
     `multiple_choice` in a row) in `_generate_prioritized()`, forcing
     the next item to pick a different tier/type; or
   - rotate the tier priority per generated item (round-robin the
     first tier across recognition/structured/production) instead of a
     fixed mastery-only order; or
   - within the chosen first tier, weight template *type* selection so
     `multiple_choice` doesn't monopolize when other buildable types
     exist for the same lexeme.

   Any one of these fixes all four affected directions at once, with no
   content changes, and would surface the sentence-frame templates that
   are already imported and sitting unused. It should be verified with
   this same audit harness (re-run and confirm MC% drops from ~90–100%
   toward the ~20% `en-fa` already achieves).

2. **Content-level (secondary, large — not done).** Narrow the broad
   `multiple_choice` templates in the `nl-en`, `fa-en`, `prs-en`, and
   `en-prs` packs (constrain their slots the way `en-fa`'s already
   are) so the ladder falls through more often. This spans ~40 packs
   per direction, needs fresh-context review, and only partially
   addresses the structural tier-first issue — the engine change is
   strictly better. Not attempted.

## Caveats

- Mastery rises with correct answers, which shifts the ladder toward
  structured/production over time — so a diligent long-term learner
  sees more variety than these single-session snapshots. But the
  monotony hits hardest for exactly the population most likely to
  churn: a beginner in their first sessions. That is the case worth
  fixing.
- The audit measures the target lexeme per item; items with no single
  target (`matching_pairs`) are excluded from the distinct-lexeme
  counts, which slightly understates variety for matching-heavy
  directions (`en-fa`).
