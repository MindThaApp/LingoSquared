# Session handoff — 2026-08-01 (autonomous burn: overlay review + nl-en checkpoints)

## ⚡ RELAUNCH FOR PHONE ACCESS (do this first if you want to text the assistant)

Prereqs are DONE this session: **bun 1.3.14 installed**, **Full Disk Access granted**
to Terminal (verified: chat.db opens). iMessage is allowlisted to **+447768619958**
+ self-chat. Telegram: **token still needed** (BotFather → paste to `/telegram:configure <token>`).

Relaunch a NEW session with the channel flag (a channel'd session is a FRESH session —
it won't be the one that made these commits, but it has the same repo/CLAUDE.md/skills):

```sh
cd ~/dev/LingoSquared
claude --channels plugin:imessage@claude-plugins-official
# once the Telegram token is saved, use both:
# claude --channels plugin:imessage@claude-plugins-official,plugin:telegram@claude-plugins-official
```

Then text yourself → reaches the assistant (first outbound reply pops an "Automation"
prompt → OK). Telegram: after saving the token, DM the bot, then `/telegram:access pair <code>`.

---

## Git state
- Branch: `fix/launch-gate-content-review-wave1`. **NO upstream — nothing pushed.**
  Do NOT push/merge/deploy without an explicit ask from Ramin.
- **10 commits this session** (b7455e99..443bd21b), all content-compile-verified
  (`verify.sh --content-only` = `content: pass`, 0 errors). Tree clean apart from
  pre-existing untracked (`frontend/.env.faqa`, `.pyc`, repo `settings.json`).

## What landed (10 commits)
1. `ae409381` overlay in-lane fixes from the **full 420-pack answer/gloss review** (all 7 directions).
2. `cfb1fd30` CLAUDE.md: coordinator-delegation rule + retired stale handover banner (395→380).
3. `9e0915f3` **two real grading bugs**: de-en a1_14 listen_select punctuation misgrade (learner
   tapping the correct option graded wrong) + repaired a **pre-existing** nl-en/prs-en a2_unit30
   matching_pairs mirror break (from a0c5dcd2) that was FAILING the content compile — masked because
   verify.sh exits 0 despite per-course COMPILE FAILED.
4. `06ab3ae3` CLAUDE.md footgun: judge verify.sh by the printed `content: pass/fail`, NOT `$?`.
5. `93d504db` backlog: checkpoint-gate status.
6. `304c029e` **nl-en lexeme backfill** for a2_unit35-40 (Codex; unblocked 6 nl-en checkpoints).
7. `4aca7c92` practice integrity/ambiguity checkers now cover **b1/b2** (119 packs were silently
   skipped by the `a*_unit*` glob) + ZWNJ boundary false-positive fix. Sweep found 0 b1/b2 defects.
8. `9e5ca493` **compiler validator/grader-gap fix** (Codex): option-answer validator now mirrors the
   punctuation-SENSITIVE grader (root cause of the listen_select class). 0 false positives on corpus.
9. `2354a894` **5 nl-en practice packs** (a2_unit35/36/38/39/40) — authored + fresh-reviewed.
10. `443bd21b` **nl-en a2_unit37 pack** (re-authored to exclude opposite-sense `turn`).

**Net: the 6 nl-en a2_unit35-40 checkpoints are closed (compile-verified).**

## Key reference produced
- Memory `reference_grading-normalization-spec`: exact grading rules (no punctuation stripping;
  fa/prs graded EXACT; latin distance-1; MCQ/option types punctuation-sensitive; `case_sensitive` flag).
  This decides what is a real content defect.

## NEXT — priority order (all detail in `docs/RAMIN_REVIEW_BACKLOG.md`, 2026-08-01 sections)

1. **fa-en + prs-en a2_unit35-40 (12 checkpoints) — BLOCKED ON RAMIN (native).** Their backfills
   (`backfill_lexemes_{fa,prs}_en.py`) stop at unit34 and need **native Farsi/Dari lexeme glosses**
   for units 35-40 (a wrong gloss ships as the shown answer). Once glossed → author 12 packs (6 per
   direction) exactly like the nl-en wave, register in `practice_manifest.txt`, compile.
2. **Systemic backfill homograph disambiguation (architecture decision).** The backfill keys glosses
   by BARE TOKEN, one per direction, so reused tokens carry another unit's sense (`turn`=sla af/turn-off,
   `order`=bestellen/verb, `correct`=juist/adj, `meeting`=afspraak). `slot_gloss` has no pack-level
   override. Same class as the known en-nl B1 five (was/waar/vroeg/rust/regel). Needs per-unit/per-sense
   gloss override in the backfill (or a pack slot_gloss override) — fixes it corpus-wide.
3. **Live checkpoint confirmation.** The nl-en packs are compile-verified; run the real
   `generate_checkpoint()` on nl-en a2_unit35-40 against a **seeded dev DB** (Docker up + sync_dev_db.sh)
   to confirm each flips `checkpoint_unavailable`→available.
4. **Native/pedagogy review queue** (from the 420-pack sweep) — fa-en/prs-en answer bugs, en-nl
   underdetermined free-text prompts (a1_10/a1_12), German ß→ss / casefold grading-POLICY decision.
   All itemized in the backlog with exact CKs.

## Hard constraints (unchanged)
- Never push/merge/deploy without an explicit ask. Dev-DB/deploy owner-reserved.
- Do NOT author fa/prs sentences or glosses (native-reserved). Dutch/German/French authoring is
  sensitive — prefer flag-and-queue; single-word fixes confirmed by sibling/realization files are OK.
- Coordinator commits with explicit pathspecs. Delegate heavy work to sub-agents/Codex; keep the
  main chat clean (CLAUDE.md POLICIES + memory `feedback-keep-coordinator-chat-clean`).
- `verify.sh` content stage: grep output for `content: pass` / `COMPILE FAILED`, not the exit code.
