# Task for tomorrow — friend beta + feedback loop

**Goal:** get the current app (with all this session's lessons) into a friend's hands;
friend submits feedback via the in-app **Feedback** button; Claude reads it directly
and acts on it.

## Verified ready (2026-08-02)
- **Feedback loop works end-to-end.** The Feedback widget POSTs `/feedback` →
  `ContentIssueReport` row. No admin read endpoint — read it directly:
  ```sql
  SELECT created_at, category, page_path,
         (SELECT email FROM users u WHERE u.id=reporter_user_id) AS reporter,
         description
  FROM content_issue_reports ORDER BY created_at DESC LIMIT 50;
  ```
  Valid categories: wrong_answer_key, mistranslation, untaught_vocabulary, audio_issue,
  unclear_instruction, app_bug, general_feedback, other. Anonymous feedback is allowed
  (reporter null). `client_context` JSON carries UA/page detail.

## Decision needed before executing (how the friend accesses the app)
1. **Friend on the home LAN** → serve the live app at `http://192.168.4.4:8011`; feedback
   lands in the LIVE DB; Claude reads it via `ssh ramin@192.168.4.4 "... psql ..."`. Cleanest.
2. **Friend remote** → live server is LAN-only; expose via a tunnel OR ship the Android
   APK pointed at a reachable backend (APK Capacitor origin `https://localhost` must be in
   the backend `CORS_ORIGINS`, per backend/CLAUDE.md).
3. **Together / borrows device** → any of the above; simplest.

## Steps (assuming the live-server route — the default)
1. **Deploy current content to the live server** (owner-present; follow
   `docs/PRE_DEPLOY_RUNBOOK.md`). The live server's content is from 2026-07-12 and is
   MISSING everything this session added: nl-en a2_unit35-40, the B2 tier (nl/fa/prs),
   and the homograph gloss fixes. Order: rsync backend+docs → migrate → content import →
   **lexeme backfills** → practice import (that order is mandatory).
   - The homograph backfills are now deploy-safe: `backfill_lexemes_en_nl.py` uses
     migrate-in-place (no orphan-delete FK failure); `backfill_lexemes_nl_en.py` is
     gloss-only. Verify both after backfill (regel→noun "the rule", order→"de bestelling").
2. **Pre-beta checklist** (backend/CLAUDE.md): confirm live `ADMIN_EMAILS` is Ramin's real
   email (not admin@example.com) and `CORS_ORIGINS` lists the origin the friend loads.
3. **Smoke test** as a guest on the live app: pick nl-en, play a lesson + a checkpoint,
   submit a test Feedback, confirm it appears in the live `content_issue_reports`.
4. Hand the URL/APK to the friend. Then Claude polls the feedback query and triages.

## Not yet done / open
- fa/prs a2_unit35-40 still native-blocked (12 checkpoints); drafts for native review in
  `docs/FA_PRS_GLOSS_DRAFTS_a2_unit35-40.md`. Friend beta can proceed on nl-en meanwhile.
- Branch `fix/launch-gate-content-review-wave1` is 250 commits ahead of master (PR #1);
  deploy runs from this branch's working tree, not from master.
