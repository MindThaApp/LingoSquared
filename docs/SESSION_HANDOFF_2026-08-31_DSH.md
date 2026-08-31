# Session Handoff — 2026-08-31 (DeepSeek Harness session, continued the Italian C1 rollout)

Read root `CLAUDE.md` + `docs/content/CLAUDE.md` + `docs/SESSION_HANDOFF_2026-08-31.md` (the
prior Claude/Codex handoff) first. This file records what THIS session (the DeepSeek Harness /
deepseek-worker session) did after Claude paused.

## What this session did
Continued the Italian C1 rollout from where the Claude session paused (units 01-04 done,
committed locally, unpushed). Built the remaining **Italian C1 units 05-08** via the
`~/bin/deepseek --pro --yolo` worker (DeepSeek balance had been restored after the `402
Insufficient Balance` Claude hit):

| unit | slug | outcome | file(s) | status |
|---|---|---|---|---|
| 01 | mobilita | discourse.structure_extended_discourse | (prior session) | committed c9e2c753 |
| 02 | ironia | inference.infer_implicit_meaning | (prior session) | committed c910793a |
| 03 | registro | register.control_tone_and_register_precisely | (prior session) | committed c910793a |
| 04 | concedere_e_controbattere | argumentation.concede_and_counter_with_subtlety | (prior session) | committed c910793a |
| 05 | ipotesi_controfattuali | hypothesis.reason_about_counterfactuals | this session | unreviewed, wired |
| 06 | idiomi_e_figurato | idiom.use_idiomatic_and_figurative_language | this session | unreviewed, wired |
| 07 | mediazione_sintesi | mediation.mediate_and_synthesize_complex_sources | this session | unreviewed, wired |
| 08 | persuasione_retorica | persuasion.persuade_with_rhetorical_devices | this session | unreviewed, wired |

All 8 realizations in `docs/content/realizations/it/c1_unitNN_*.yaml`; all 8 overlays in
`docs/content/overlays/en-it/c1_unitNN.yaml`. content_keys match (`it.c1.unitNN.<slug>` ↔
`en-it.c1.unitNN`). `scripts/content_manifest.txt` line 74 now lists all 8 units (both fields).

## Verification status
- `verify.sh --content-only`: **content: pass**; the `en-it-c1` stanza validates + full-assembles
  with **0 errors** (re-run after each of units 05, 06, 07, and after wiring unit08).
- Worker self-validations: units 05/07/08 single-unit runs showed ONLY the documented phantom
  "tokens not introduced" findings (course-cumulative check); unit08's 9 `è` findings were
  verified phantom by a two-unit re-run. Unit06 retained one justified §16 matching_pairs
  soft-warning (5 pairs, first lesson — no prior vocab to pool; "do not pad").

## NEXT STEPS (in order)
1. **Full fresh-context review of the COMPLETE it C1 tier is MANDATORY** (it's this language's
   first C1 tier, and units 01-08 are all `unreviewed`). Dispatch a fresh (non-fork) reviewer
   with zero authoring context over all 16 files (8 realizations + 8 overlays), the binding docs
   (AUTHORING_GUIDE.md, AUTHORING_PREFLIGHT.md), and paste the accumulated cross-tier lessons
   verbatim. Call out the historical defect classes: punctuation matching, open-ended production
   prompts, speaking-vs-writing asymmetry, teaching-card-vs-audio mismatch, regret/concession
   framing contradictions, dictation asset byte-equality, untaught tokens, Italian morphology.
2. **Fix every finding** in one consolidated worker dispatch; independently re-run course-scoped
   `verify.sh --content-only` after (grep the en-it-c1 stanza + COMPILE FAILED — `content: pass`
   alone is insufficient).
3. **Commit** the new it C1 units 05-08 + the manifest update with EXPLICIT pathspecs
   (never `git add -A`). Then ask Ramin before pushing (owner-reserved). Note: commits for units
   01-04 (`c9e2c753`, `c910793a`) are still unpushed and `origin` is behind.
4. **Then roll the same 8-outcome C1 tier out to fr, ru, ar, ro, pl, hi** (all currently C1=0).
   fa/prs remain native-reserved/blocked. de-en is a separate underbuilt X→en lane, not part of
   this rollout.

## Worker mechanics (this session)
- **DeepSeek is back online** (balance restored). Command: pipe prompt via stdin:
  `eval "$(grep -E '^export DEEPSEEK_API_KEY' ~/.zshrc)" && ~/bin/deepseek --pro --yolo < prompt.md`
  (run in background; do NOT embed the key in the command line). Workers are stateless and
  reliable; ~0 failure rate this session.
- If DeepSeek hits `402` again, use **Codex** instead (see `docs/SESSION_HANDOFF_2026-08-31.md`
  §3a): `node ".../codex-companion.mjs" task --cwd <repo> --background --write --fresh
  --prompt-file <file>` (first dispatch in a session uses `--fresh`; later ones `--resume`).
- **Dispatch prompts** were written to /tmp/it_c1_unitNN_prompt.md and must include: AUTHORING_
  PREFLIGHT.md verbatim; structural template pointer; exact spine-outcome text (grep fresh from
  `universal_spine.yaml`); register pin (informal tu, Sam=American engineer in Milan,
  Elena=Italian teacher); STRONG sibling-isolation; the 8 accumulated cross-tier lessons
  verbatim; and a self-compile requirement. Prompt files for the next languages' unit01 can be
  modelled on these (recreate them; they're ephemeral in /tmp).
- Serialize authoring: one worker dispatch at a time (verify files exist after each; the
  previous Claude/Codex session's note says ~1-in-4-5 deepseek dispatches produced nothing and
  needed a retry — that did NOT recur this session).

## Character canon (verified for all 8 it C1 units)
Sam = American engineer (ingegnere) from Chicago, working in an office in Milan, masculine forms.
Elena = Italian teacher (insegnante) from Milan, feminine forms. Established colleagues, informal
`tu` throughout. "la direttrice" (female director) introduced in unit03 as formal-register audience.

## Open decisions / reserved for Ramin
- **Push** the it-C1 commits (c9e2c753, c910793a, + the new units 05-08 commit once made) —
  owner-reserved, ask before pushing.
- **DeepSeek balance** — appeared restored this session (pro worked for units 05-08). Confirm
  before relying on it long-term.
- App name, friend-beta loop, live deploy — unchanged/reserved per the prior handoff.

## Repo hygiene
- Untracked infra files to NOT sweep into commits: `.firecrawl/`, `.playwright-mcp/`,
  `backend/docker-compose.faqa.yml`, `backend/docker-compose.play.yml`, `backend/web_dist/`,
  `frontend/.env.faqa`, `docs/SESSION_HANDOFF_2026-07-17.md`.
- Branch: `fix/launch-gate-content-review-wave1`. Use explicit pathspecs when committing.

## UPDATE (same session, later) — review + fixes completed
- **Fresh-context review of the complete it C1 tier ran** (independent reviewer, zero authoring context, all 16 files). Result: **2 blockers, 8 should-fix**, plus nits and 2 native-judgment items. Units 05/07/08 were fully clean; defects concentrated in units 01-03 (authored by the prior Claude/Codex session) + one each in 04 and 06.
- **Blockers:** B1 = unit03 lesson05.speak_two_tones vs lesson06 model contradiction (emphatic-vs-ironic to Elena, grading one of the two correct answers wrong); B2 = unit02 lesson06.comprehend_full had untaught vocabulary in reading `prompt.target_blocks` (compiler-invisible gap).
- **Should-fixes:** S1 = unit01 three declared-but-absent `introduced_tokens` (proponi, e, rischi); S2 = unit02 two untaught-vocab accepted answers; S3 = unit02 speaking act missing the "explain the unstated judgement" half; S4 = unit03 diplomatic register label blur + production; S5 = unit04 confusable matching_pairs lefts (match_oral_moves, match_concessione); S6 = unit06 underdetermined translate_toro prompt.
- **All blockers + should-fixes fixed in one consolidated worker dispatch.** Independently re-verified course-scoped: `en-it-c1` = **0 errors, content: pass** (single pre-existing §16 warning on unit06 L01 ex03, untouched). Blockers B1/B2 spot-checked applied.
- **Left for native-Italian/human judgment** (NOT fixed, noted): unit06 `modello_pasta` "Ho le mani in pasta in questo progetto" (double "in" — arguably acceptable); unit01 dettato trailing period + parentesi.01 audio truncation (harmless); unit02 listen_irony tested_text vs audio fragment (choice-based, harmless); unit03 lesson01 exercise numbering gap (ex01→ex03, cosmetic, content_key renames risky).
- **Next:** commit the 11 modified it C1 files (units 01-06) with explicit pathspecs; ask Ramin before pushing; then roll C1 out to fr/ru/ar/ro/pl/hi.
