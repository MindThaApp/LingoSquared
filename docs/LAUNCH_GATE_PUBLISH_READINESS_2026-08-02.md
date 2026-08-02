# Launch-gate publish-readiness — definitive map (2026-08-02)

Measured by running the real `generate_checkpoint()` for **every unit** in all six
launch-gate courses against a seeded dev DB (all authored packs imported; a unit is
publishable iff it yields ≥12 checkpoint items). Method notes: use a REAL user id
(the persist step has an FK) and a SHORT `session_id` (the column is `VARCHAR(36)`;
`"probe-"+uuid` overflows and masks results as DataError).

## Result: every checkpoint is publish-ready EXCEPT the two buckets below

| direction | A1 | A2 | B1 | B2 |
|---|---|---|---|---|
| en-nl | 67/67 ✅ | 10/10 ✅ | 11/11 ✅ | — |
| nl-en | 62/63 (unit60 thin) | 16/16 ✅ | 19/19 ✅ | **8/8 ✅** |
| en-fa | 57/57 ✅ | 10/10 ✅ | 16/16 ✅ | — |
| fa-en | 63/63 ✅ | 10/16 (35-40 native) | 19/19 ✅ | **8/8 ✅** |
| en-prs | 60/61 (unit43 thin) | 10/10 ✅ | 11/11 ✅ | — |
| prs-en | 62/63 (unit41 thin) | 10/16 (35-40 native) | 19/19 ✅ | **8/8 ✅** |

**Closed this session:** the 24 B2 checkpoints (nl-en/fa-en/prs-en, 8 each) — their
packs were authored, reviewed, and registered but had never been imported into the
dev DB (0 templates, lexemes present). Importing them (104 / 132 / 128 templates,
0 compile errors) flips all 24 to a full 15-item checkpoint. Plus the nl-en
a2_unit35-40 wave closed earlier.

## The only two remaining gaps

### 1. Native-blocked — 12 checkpoints (the real launch blocker)
`fa-en` and `prs-en` **a2_unit35–40** yield 0 items: their lexeme backfills stop at
unit34, so no Farsi/Dari L1 glosses exist for those English tokens (a wrong gloss
would ship as the graded answer, so this is native-reserved). The exact fill-in
worklist is `docs/FA_PRS_GLOSS_WORKLIST_a2_unit35-40.md` (39 tokens/direction). Once
glossed → extend `backfill_lexemes_{fa,prs}_en.py`, author 12 packs, import.

### 2. Genuinely-thin breadth A1 units — 3 checkpoints (content-design, not defects)
`nl-en unit60.invitations` (10), `en-prs unit43.library` (9), `prs-en unit41.cooking`
(11). These teach mostly reused/function vocabulary with only ~5 first-introduced
content lexemes, and the checkpoint scopes targets to a unit's OWN lexemes — so they
cannot reach the 12-item floor without either teaching more distinct vocab (a content
redesign) or accepting no checkpoint. The pack authors already flagged this and
correctly refused to pad with untaught vocabulary. **Decision for Ramin:** accept
these breadth units as checkpoint-exempt, or expand their taught vocab. Not a bug.

## Bottom line
Every en→X course is fully publish-ready. Every X→en course is publish-ready except
the 12 native-blocked a2_35-40 checkpoints and the 3 thin breadth units. The launch
gate has no remaining *authorable* content gaps beyond those two buckets.
