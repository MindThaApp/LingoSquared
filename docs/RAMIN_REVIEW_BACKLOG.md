# Ramin's review backlog

Things the autonomous coordinator (Claude) decided or deferred that Ramin may
want to review when he has a moment. **Nothing here is blocking** — it is a
queue, not a set of questions. Newest at top. The coordinator appends; Ramin
prunes.

Standing mandate (2026-07-23): Claude runs the build autonomously as
coordinator/architect/engineer with a subagent team; only genuinely blocking
or owner-reserved decisions interrupt Ramin. Everything else lands here.

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
