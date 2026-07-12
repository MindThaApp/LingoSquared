# Session handoff — written 2026-07-12 ~17:45 (supersedes the morning doc)

Read this + `docs/COORDINATOR_HANDBOOK.md` + root `CLAUDE.md` to resume
coordinating. Everything below is committed & pushed (master `485823a`,
private GitHub ramin-azizi/LingoSquared). The 2026-07-12 morning doc
(`SESSION_HANDOFF_2026-07-12.md`) holds the overnight session log —
still worth skimming for the depth-measurement history.

## State as of this handoff

- **Working tree clean** (only the usual untracked `.firecrawl/`,
  `.playwright-mcp/`, per-session docker-compose files, `.env.faqa`).
  Zero open worktrees, zero running workers, zero running Codex tasks.
  Dev-DB sync11 completed clean; dev DB fully reflects master.
- **Full-corpus content validation is GREEN** (first time ever,
  achieved today) — `bash scripts/verify.sh --content-only` passes.
  German lane recovered (dead session's WIP landed + 23 fixes, all
  reviewed); en-de/de-en imported to dev DB for the first time.
- **Live server (192.168.4.4) is current**: frontend deployed today
  with feedback image-attachments UI + localized language names
  (`--mode production.lan` build, rsync'd, bundle hash verified).
  Ramin confirmed it works. **Coordinator now has STANDING DEPLOY
  AUTHORITY** (root CLAUDE.md OPERATIONS) — verification bar first,
  destructive live-DB ops still need Ramin.
- **Codex quota**: last reset 11:39; ~15 tasks run today, one quota
  bounce mid-afternoon. Check before big waves.
- **Claude budget**: heavy Opus review usage today — the tiered-review
  data now justifies 1-in-3 sampling for it/ru lanes (see registry) to
  economize.

## What shipped today (all reviewed + merged + synced + pushed)

1. **Feedback attachments frontend** — live on 192.168.4.4 + dev.
2. **X→en B1 closed at 11 units** (nl-en/fa-en/prs-en 07-11).
3. **Two compiler validators** (pairs-mirror, audio-containment) — 0
   false positives, caught real bugs incl. a de-en regression later.
4. **Italian + Russian: 15 fully-reviewed A1 units each** with
   reviewed en-it/en-ru overlays, manifest-wired, imported.
5. **English A1 units 59-68** (10 new topical units) + all three X→en
   overlay sets, all reviewed. fa-en had a register-divergence incident
   (fixed + prevented via per-lane register pins in content CLAUDE.md).
6. **Practice**: +90 templates (43-48/31-36 ranges) + format-monotony
   fix (MC share modeled 60-82% → 44-50%); practice depth measured
   145-219h/direction — **practice launch bar CLOSED**.
7. **§16 matching_pairs retrofits**: en-fa (25 exercises) + shared-en
   units 04/05 (with all FOUR overlay mirrors — see footgun below).
8. **fa/prs UI locale register normalization**; **wrong-language bug
   fixed** (course-picker language names now localized via
   `language_names` i18n block, `localizedLanguageName()` helper).
9. **German lane recovery** (Ramin declared the session dead).
10. **Local-model experiment**: qwen3:14b BARRED from content
    (verdict in COORDINATOR_HANDBOOK). Ramin: never use local AI.

## Launch-gate scoreboard

- Practice depth: **PASS** everywhere (145-219h vs 10h bar).
- Teaching depth: en→X **PASS** (11.25/13.8/15.3h). X→en **7.90h per
  direction** — passes per-PAIR (19-23h), short per-DIRECTION.
  **OPEN QUESTION FOR RAMIN: is the 10h teaching bar per-pair or
  per-direction?** If per-direction: author denser English B1 units
  12+ (most efficient; ~19 more light A1 units otherwise). X→en unit
  waves are PAUSED pending this ruling.
- Checkpoints: built (Phase F). "Minimum bugs" live verification:
  report-button loop live; Ramin's Dutch native pass + phone QA still
  the human gates.

## Queued / natural next work (in priority order)

1. Ramin's per-pair ruling → possibly English B1 12+ wave (Codex,
   3 overlay sets each, register pins quoted verbatim in EVERY prompt).
2. it/ru units 16+ drip (recipe proven; lanes eligible for 1-in-3
   review sampling per registry — coordinator may apply it).
3. Small-fix backlog: fa u37 lesson03 match_asking_color_words has two
   synonym lefts both glossed "What color is it?" (ambiguous matching);
   §1.22 same-speaker-distractor validator (listen_select) still on
   Codex backlog; sync_dev_db.sh mid-run 401 token-refresh (Codex).
4. Variety re-audit (isolated stack harness in
   PRACTICE_VARIETY_AUDIT_2026-07-11.md) to confirm the MC% fix
   empirically — modeled only so far.
5. Remaining §16 warnings are all documented genuine caps (~14 en,
   ~25 fa, 13 it, 13 ru) — no action unless the guide changes.

## RAMIN'S LIST (unchanged from morning doc, minus resolved items)

1. Domain + Cloudflare Tunnel (~$10/yr) — unlocks public HTTPS, OAuth,
   VITE_FEEDBACK_API_URL.
2. Apple Developer / Google Play / Google OAuth client ID
   (docs/ACCOUNT_SETUP_CHECKLIST.md).
3. Azure Speech key → real Farsi TTS.
4. Live ADMIN_EMAILS swap before any external beta user.
5. Dutch native review pass + phone QA evening (http://192.168.4.4:8011;
   PWA install: browser → address-bar install icon).
6. ja/ko typing IME decision (blocks ja/ko production-typing only).
7. C1/C2 planning decision.
(Wrong-language bug: RESOLVED today — was unlocalized language names.
German session: RESOLVED — declared dead, lane recovered.)

## Footguns learned today (also in registry/CLAUDE.md)

- **The shared English realization has FOUR X→en overlay consumers:
  nl-en, fa-en, prs-en AND de-en** — update all four mirrors or the
  compiler mirror-validator fails de-en (happened today, caught in
  review). Now in docs/content/CLAUDE.md.
- **Per-lane register pins** exist in docs/content/CLAUDE.md — quote
  them VERBATIM in every authoring dispatch (prevented a recurrence
  when done; caused a full 5-file conversion when not).
- **Fixer/worker self-reports lie**: one fixer "validated" the wrong
  file set and reported success; Codex acceptance twice passed its own
  harness while the real one failed. ALWAYS run the acceptance command
  yourself before commit; put the verbatim command in the prompt.
- **Opus reviewers sometimes get no worktree** (2 of 3 in one batch
  committed straight to master — commits were fine, but diff git log
  after every batch, per the standing rule).
- **Don't run sync_dev_db.sh while a merge is mid-conflict** (it reads
  the working tree); its admin token can also expire mid-run (401s) —
  re-run works.
- Grepping sync logs for "401" false-positives on container IDs —
  grep for `"-> 401"` or `Traceback` instead.

## Session infra notes

- Vite dev server on :5180 was restarted today (PID changed; log at
  scratchpad/vite5180.log of the old session dir). If the Mac mirror
  looks blank after shared-package export changes: root `npm install`
  + restart Vite.
- Depth ruler: `.content-venv/bin/python scripts/measure_content_depth.py`
  (teaching, no DB) / `--practice-only` via the docker-compose run
  documented in the script header.
- Five-module backfill acceptance harness (run before committing ANY
  backfill script change): import backfill_lexemes{,_en_nl,_nl_en,_fa_en,_prs_en}
  from scripts/ and fully iterate iter_specs() on each.
