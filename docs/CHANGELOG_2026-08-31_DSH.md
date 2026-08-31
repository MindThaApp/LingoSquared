# Change Log — LingoSquared C1 rollout (2026-08-31, DeepSeek Harness session)

Running record of pushes and content changes made this session. Companion to
`docs/SESSION_HANDOFF_2026-08-31_DSH.md` (state/handoff). Branch:
`fix/launch-gate-content-review-wave1`. Remote: `git@github.com:ramin-azizi/LingoSquared.git`
(redirects to `MindThaApp/LingoSquared`).

## PUSH LOG
| When | Range pushed | Commits | Result |
|---|---|---|---|
| 2026-08-31 | `d3de583f..ca58f533` to `origin/fix/launch-gate-content-review-wave1` | 5 (it C1: c9e2c753, c910793a, 743d839c, fc6c4d76, ca58f533) | **Pushed** (owner-authorized). `origin` == local tip `ca58f533`; `origin..HEAD` = 0. |

## ITALIAN C1 — shipped to origin
All 8 units, reviewed, blockers/should-fixes fixed, course-scoped verified (0 errors), committed + pushed.
- c9e2c753 — it C1 unit01 (discourse)
- c910793a — it C1 units 02-04 (inference, register, argumentation)
- 743d839c — docs: session handoff update
- fc6c4d76 — it C1 units 05-08 (counterfactuals, idioms, mediation, persuasion) + manifest + DSH handoff
- ca58f533 — fresh-context review fixes to it units 01-06
- Working tree clean of it C1 changes.

## FRENCH C1 — in progress (new course `en-fr-c1`, NOT yet committed/pushed)
16 new files (8 realizations + 8 overlays) + `scripts/content_manifest.txt` line for `en-fr-c1`.
Course-scoped verify: **en-fr-c1 = 0 errors, content: pass** (2 intentional §16 soft-warnings).
Fresh-context review: dispatched (pending). None of this is committed yet.

| Unit | Realization (realizations/fr/) | Overlay (overlays/en-fr/) | Outcome |
|---|---|---|---|
| 01 | c1_unit01_structure_discours.yaml | c1_unit01.yaml | discourse.structure_extended_discourse |
| 02 | c1_unit02_implicite_ironie.yaml | c1_unit02.yaml | inference.infer_implicit_meaning |
| 03 | c1_unit03_tone_et_registre.yaml | c1_unit03.yaml | register.control_tone_and_register_precisely |
| 04 | c1_unit04_conc_et_contredire.yaml | c1_unit04.yaml | argumentation.concede_and_counter_with_subtlety |
| 05 | c1_unit05_contrefactuel.yaml | c1_unit05.yaml | hypothesis.reason_about_counterfactuals |
| 06 | c1_unit06_idiomes.yaml | c1_unit06.yaml | idiom.use_idiomatic_and_figurative_language |
| 07 | c1_unit07_mediation_sources.yaml | c1_unit07.yaml | mediation.mediate_and_synthesize_complex_sources |
| 08 | c1_unit08_persuasion_retorique.yaml | c1_unit08.yaml | persuasion.persuade_with_rhetorical_devices |

## CURRENT UNCOMMITTED STATE (`git status --short`)
- `M scripts/content_manifest.txt` (en-fr-c1 line added)
- `M docs/SESSION_HANDOFF_2026-08-31_DSH.md`
- `?? docs/content/realizations/fr/c1_unit0{1..8}_*.yaml` (8)
- `?? docs/content/overlays/en-fr/c1_unit0{1..8}.yaml` (8)
- Unrelated (not mine, do NOT commit): `docs/SESSION_HANDOFF_2026-07-17.md`, `docs/SESSION_HANDOFF_2026-08-30.md`, plus the infra files noted in the handoff.

## TODO LOG (next steps in order)
1. Collect fr C1 fresh-context review findings (subagent 63ec9115) → apply consolidated fixes → re-verify course-scoped.
2. Commit fr C1 (16 files + manifest) with explicit pathspecs; update this changelog; ask Ramin before push.
3. Roll C1 out to ru, ar, ro, pl, hi (same 8-outcome tier; fa/prs native-reserved; de-en separate axis).
## FRENCH C1 — review + fix (same session)
- **Fresh-context review done**: 3 clean units (01, 03, 08); 5 units with should-fixes, NO blockers.
  - F1 unit04 confusable matching_pairs lefts (néanmoins/cependant/toutefois).
  - F2 unit06 confusable matching_pairs lefts (mettre la main à la pâte / donner un coup de main).
  - F3 unit07 mediation framing contradiction: graded model dropped the real disagreement ("la concertation n'a jamais eu lieu").
  - F4 unit05 overlapping matching lefts (whole sentence vs result clause).
  - F5 unit02 production under-delivered the "explain the unstated judgement" half.
  - Human-check: unit05 pins Inès "originally from Paris" — verify against prior fr content.
  - Recurring nit (not rewritten): writing/speak prompts embed the full target sentence (copy-task trade-off).
- **Consolidated fix dispatched** (deepseek worker, job bash-26). After fix: re-verify course-scoped, then commit.
