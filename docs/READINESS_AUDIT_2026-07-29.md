# LingoSquared readiness audit — 2026-07-29

Four read-only auditor sweeps (backend / frontend / tests+CI / deploy+infra) plus the
content-gate + branch facts. **Bottom line: the app is *built*, not *launched*.** The software
(backend + frontend) is mature and essentially feature-complete for the learner experience; what's
missing is shipping it safely + finishing the content vetting.

## Dimension summary

| Dimension | Status | Headline |
|---|---|---|
| Backend | ✅ mostly complete | 62 routes, all real logic (no stubs/TODOs/501s); grading/SRS/TTS/STT/push/social/checkpoints genuine; Alembic linear + drift-tested. |
| Frontend | ✅ mostly complete | React 19/TS builds+lints clean; covers whole learner surface; 17/19 exercise types; i18n parity ×4. |
| Tests | ✅ strong | 285 backend + 50 frontend + 34 content + 15 e2e; grading has a corpus-wide regression guard. |
| CI | ✅ ADDED 2026-07-29 | Was mobile-only. Now `.github/workflows/ci.yml` runs content+frontend+backend. |
| Deploy/infra | ❌ not ready | Manual SSH+rsync to one home server never deployed to; no TLS; ADMIN_EMAILS placeholder; CORS LAN-only. |
| Content gate | ⏳ ~13% | 72/553 packs reviewed; new defect classes each batch; many fixes deploy-effect (blocked). |

## Autonomous items — DONE this session (2026-07-29)
- **Red `backfill_lexemes` test fixed** (commit 87fad49b): stale unique-identity invariant (didn't
  account for a1/a2/b1 = separate courses, nor 2 documented phrase sense-splits). Content suite 34/34.
- **Stale frontend test** (799a752f): MatchingPairs asserted "Check" vs the mocked key "common.check".
  Frontend suite 50/50.
- **fib/faqa docker-compose port collision** (799a752f): both mapped API→8060; fib moved to 8065.
- **CI added** (39cd9ef0): content (verified 34/34) + frontend (verified 50/50+build) + backend
  (Postgres service, mirrors conftest/verify.sh — UNVERIFIED locally: no 3.12/Postgres here).

## What stands between here and a beta (ordered)

**Must-fix before any external user — BLOCKED on Ramin/infra:**
1. Set + register a real `ADMIN_EMAILS` (first-registrant-becomes-admin; even local .env fails
   `check_deploy_config.sh`). — needs Ramin's real email.
2. Execute the deploy pipeline once, live (migrate→seed→register-admin→content-import→backfill→
   practice-import) — it has never run against 192.168.4.4. — needs SSH + Ramin present for DB ops.
3. TLS/HTTPS + real `CORS_ORIGINS` if beta reaches beyond the LAN (also blocks any app-store path).
4. External cron for the two push triggers, or push silently never fires.
5. Run the new backend CI once (Postgres) — clears the residual on the casefold fix's integration
   verification too; **verify the `fastapi==0.139.0` pin resolves on public PyPI** (local index couldn't).

**Autonomous (in progress / doable without secrets/infra):**
- Content review gate: keep grinding batches (self-re-invoking). ~480 packs remain.
- Consolidated deploy-effect backfill wave (RAMIN_REVIEW_BACKLOG "BATCH 3/4 ★"): leaked-annotation
  glosses (strip English parentheticals, collision-checked), `_pure`/narrow tags (DEAD-verify unit
  scope first), bare-POS re-anchoring. Source-correct now; live on next re-backfill.

**Product decisions (yours):** password-reset flow, social-login UI (backend endpoint exists, no UI),
legal review (pages are self-flagged unreviewed drafts). Several already "accepted gaps" for beta.

**Cheap cleanups remaining:** stale PrivacyPolicy "no export tool" copy (export shipped); stale
backend/README "no refresh tokens" (they exist); dead `LearningPath` schema; dead slot anchors
(prs-en u14 content_pool, u15 number_no_hundred).

See `docs/RAMIN_REVIEW_BACKLOG.md` for the content-defect detail and `docs/PRE_DEPLOY_RUNBOOK.md`
for the deploy sequence.
