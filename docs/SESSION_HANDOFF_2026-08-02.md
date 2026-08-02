# Session Handoff — 2026-08-02

Branch: `fix/launch-gate-content-review-wave1` · **267 commits unpushed** to `origin/master`.
Directive in force (Ramin): **"don't stop building until I tell you I'm ready."** — continuous autonomous build.

---

## TL;DR — where things stand

1. **Launch-gate content (en-nl / en-fa / en-prs): content-complete + grading-clean** (26k+ answer-shape/grading tests pass). Two known gaps, both non-blocking:
   - 12 fa/prs `a2_unit35–40` glosses need **native review** (drafted, not merged) — see `docs/FA_PRS_GLOSS_DRAFTS_a2_unit35-40.md`.
   - 3 thin-breadth units flagged in `docs/LAUNCH_GATE_PUBLISH_READINESS_2026-08-02.md`.
2. **NEW this session — full Dutch B2 tier authored** (8 units, `en-nl-b2`). All authored + fresh-context reviewed + defect-fixed + committed; compiles **0 errors**. **DRAFT status** — only open item is Dutch *naturalness*, queued for Ramin (native). Per-unit review blocks list the specific idiom/word-order flags.
3. **B2 lexeme backfill wired** (`scripts/backfill_lexemes_en_nl.py`: +168 glosses, 165 POS, 46 lesson-cats + migrate-in-place upsert).
4. **Deploy to live (192.168.4.4) NOT done.** Blocked twice — see "Deploy" below. Latest B2 lessons + a2_35-40 checkpoints are **only in the local dev DB / local branch**, not on the live server.

---

## What shipped this session (commit range on the branch)

- `d378a82a` B2 lexeme backfill extension (en-nl)
- `5bd6b743`→`9c5931d4` nl **B2 units 01–08** authored + reviewed + fixed (argumentatie, speculatie, nuance, verhaal, register, abstractie, onderhandelen, synthese). Reuses Lotte/Omar canonical informal pair.
- Earlier in session: 9 homograph gloss fixes (en-nl/nl-en); imported 30 missing B2-tier checkpoints (nl-en/fa-en/prs-en) into **dev** DB; Dari fixes `a1_unit19`, `a2_unit11`, `b1_unit05`.

Files: `docs/content/realizations/nl/b2_unit0[1-8]_*.yaml` + `docs/content/overlays/en-nl/b2_unit0[1-8].yaml`. `en-nl-b2` registered in `scripts/content_manifest.txt`.

---

## Systematic authoring learnings (bake into every B2 dispatch)

- **respond_/dialogue_response `type` MUST match overlay shape**: free-text→`accepted_answers` only; MC→`correct_option`+`distractors`; never mix (u01 L06ex07 would have graded an open question against one string).
- **B2 multi-sentence writing needs a punctuation variant set** (all-periods / no-trailing-period / comma-joined) or it's brittle under exact grading.
- **Item-7 must deliver the outcome's PRODUCTION act** (whole act, not drilled pieces) — the very first B2 wave failed this.
- New tier = **FULL fresh-context review each unit** (no sampling).

---

## Immediate next steps (in priority order)

1. **B2 checkpoint-enabling** (not started). The B2 units are LESSONS only — no practice/checkpoints yet. To enable, like the a2_35-40 wave:
   - Backfill already wired (`UNIT_FILES_B2` + NL_GLOSSES delta done).
   - Author **8 en-nl b2 practice packs** → register in `practice_manifest.txt` → import → verify checkpoints AVAILABLE (need ≥12 items each). Backfill is **Codex-lane**.
2. **Deploy to live** (below) so Ramin/friend can try B2 + a2_35-40.
3. **Native-Dutch review** of the 8 B2 drafts (naturalness) + fa/prs glosses — Ramin.

---

## Deploy — blocked, needs Ramin to run

Live server `ramin@192.168.4.4` (API :8010, web :8011, repo `/home/ramin/LingoSquared` is an **rsync target, NOT a git clone** — `git fetch` there fails by design).

Blockers hit this session: (a) no authorized SSH key on the box; (b) app-admin login 401 (wrong live admin password). The coordinator will not type the SSH password to authenticate (standing safety rule — held even after chat authorization).

**Ramin runs this himself** (rsync + content sync via ControlMaster, one SSH-password prompt, then app admin email/password prompt):
```
scripts/sync_dev_db.sh http://192.168.4.4:8010
```
…preceded by an rsync of the built `web_dist` + backend per `docs/PRE_DEPLOY_RUNBOOK.md`. Verify afterward at `http://192.168.4.4:8011` that B2 lessons + a2_35-40 checkpoints appear.

---

## Verification bar (must stay green — NON-NEGOTIABLE)

- Content compiler: `en-nl-b2` compiles **0 errors** ✓
- **Always run pytest against an ISOLATED test DB** — this session wiped the dev DB once by running `test_content_answer_shapes.py` against the default DB (recovered via `sync_dev_db.sh`; had to re-register admin first). See `incident_2026-08-02_dev-db-wipe.md`.
- Frontend: full `npm run build` (not `tsc --noEmit`).
- Live browser check with a fresh test account for anything user-facing.

---

## Open threads / deferred

- **Content-scaling strategy** (Ramin raised, unresolved): build gold reference langs (English X→en + Dutch en→X) fully, then machine-adapt → automated-check (compilers + 26k grading tests + grammar pass) → native-refine outward to other pairs. nl B2 IS gold-reference step 1. If Ramin confirms adopt-outward, switch main thrust to standing up that pipeline. See `project_2026-08-02_nl-b2-build-and-strategy.md`.
- **App-store shipping + feedback wiring + Google/Apple sign-in**: social login already built (`POST /auth/social`, provider google|apple). Runbook published as artifact `ship-guide.html` (scratchpad). Hosting decision pending.
- **App name**: Ramin unhappy with suggestions. Current best fresh direction = mimic-bird metaphor: **Mynah** (lead), **Lyra**, **Yabber**, **Flume**. Awaiting a vibe steer (playful vs premium).
- Uncommitted in tree (leave alone — not this session's): `.claude/settings.json`, pyc, `.firecrawl/`, `.playwright-mcp/`, `backend/docker-compose.{faqa,play}.yml`, `frontend/.env.faqa`.

---

## Key file map

- B2 content: `docs/content/{realizations/nl,overlays/en-nl}/b2_unit0*.yaml`
- Backfill: `scripts/backfill_lexemes_en_nl.py` (B2 wiring at `UNIT_FILES_B2`)
- Manifests: `scripts/content_manifest.txt` (en-nl-b2 ✓), `scripts/practice_manifest.txt` (B2 packs NOT yet added)
- Deploy: `scripts/sync_dev_db.sh`, `docs/PRE_DEPLOY_RUNBOOK.md`
- Readiness/drafts: `docs/LAUNCH_GATE_PUBLISH_READINESS_2026-08-02.md`, `docs/FA_PRS_GLOSS_DRAFTS_a2_unit35-40.md`, `docs/PRS_DRAFT_REVIEW_2026-08-02.md`
- Memory: `project_2026-08-02_nl-b2-build-and-strategy.md`, `project_2026-08-01_checkpoint-and-homograph.md`, `incident_2026-08-02_dev-db-wipe.md`
