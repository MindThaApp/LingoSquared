# Session Handoff — 2026-08-03

Branch: `fix/launch-gate-content-review-wave1` · **284 commits unpushed** to `origin/master`.
Standing directive (Ramin): **"don't stop building until I say ready"** — continuous autonomous build.
Local stack up (`colima` + `docker compose`): **API on host port 8020**, web on 8011, db healthy. Admin: `admin@example.com` + `~/.lingo_admin_pw` (a second admin, `[admin email]`, was added to LOCAL `ADMIN_EMAILS` this session — see below).

---

## TL;DR — what this session shipped (15 commits, all on the branch)

Two complete **new learning modalities**, each built → verified → rolled out across the full nl reference stack (A2/B1/B2), plus B2 checkpoints and the app-name shortlist.

1. **Dictation exercise type** (`35257028` type, `fd77707d` spec) — hear a TTS sentence → type it, graded **orthography-strict by type**. Reuses `Translation.tsx`; migration `0027` widened `ck_exercises_type`. Rolled out: nl **A2 (20) + B1 (22) + B2 (16) = 58 exercises** (`677f720f`,`c9ce57a0`,`98d4d2b8`), each reusing an already-taught sentence + existing audio.
2. **Reading track — tap-to-gloss** (`ae7beec8` MVP, `5b74bba8` spec) — tap any word in a `reading` passage → its gloss. Author-controlled `glosses:` map (overlay), compiled onto the card + served on `GET /lessons/{id}`; new `GlossableText.tsx`. Rolled out: nl **A2 (213) + B1 (259) + B2 (179) = 651 glosses on 29 passages** (`c8a13228`,`b2140da1`,`e863039e`).
3. **nl B2 checkpoints** (`a52269d3`, earlier) — 8 en-nl B2 practice packs; `POST /units/{id}/checkpoint` returns AVAILABLE/15-items for all 8. Dutch B2 course id in dev DB: `6b6dd1cd-6e39-4257-906c-2dd94dd99bed`.
4. **App-name shortlist** (`7cc00d66`) — `docs/APP_NAME_SHORTLIST.md`, 17 confirmed-clean names (no competing lang app + free `.io`). **Decision PENDING (Ramin).** Ramin liked the "au-/-vel" audio family (Auvel/Auvelo/Auvelio/Auverio/Auvano…).

Everything imported to the **dev DB** (localhost:8020) and committed. **NOT pushed. NOT deployed to live (192.168.4.4).**

---

## Verification status
Verified per feature: real grading code (dictation: exact→correct, 1-char typo→incorrect on nl; listen_type stays tolerant — proves strict-by-type), component/guardrail tests (`ExerciseRenderer.test.tsx` PROMPTS; `GlossableText.test.tsx`), **full isolated-DB pytest green**, full `npm run build` green, compile 0 errors per tier, and live serve confirmed (`GET /lessons/{id}` returns glosses).
**One honest caveat (both features):** no manual browser click *all the way to* a deep in-lesson card was done (grading/serve verified via real code, render via tests). Low residual risk (reused, test-covered components). A guided browser play-through is the one remaining optional check.

---

## Immediate next steps / open decisions
1. **Ramin's calls:** (a) pick a name from `docs/APP_NAME_SHORTLIST.md`; (b) **live deploy** — still blocked (no authorized SSH key on 192.168.4.4; app-admin 401). The dev DB has all this session's work; live does not.
2. **Keep scaling (low value):** nl **A1** for either modality — A1 sentences are trivial (dictation) and passages simple (glossing), so marginal value is low; skipped deliberately.
3. **Other languages:** dictation/reading-audio need TTS. **fa** works once `AZURE_SPEECH_KEY` is provisioned; **prs** has zero TTS (do NOT author audio-prompt content for prs — silent/unanswerable). See `backend/CLAUDE.md`.
4. **Next feature:** skill-targeted practice (3rd lingua.com finding) — spec it like the other two if pursued.
5. **Browser verify** the two new features live (see caveat above).

---

## Known follow-ups (minor, non-blocking)
- **Reading-track tokenizer mismatch:** the compiler's gloss-key validator (`validate_reading_glosses`, `[\w‌]+`) SPLITS the possessive apostrophe (`collega's`→`collega`+`s`) while the frontend `GlossableText` tokenizer KEEPS it. Effect: a `collega's` gloss key WARNs at compile but still taps in-app. B2 unit01 kept it (warns, taps); B1 unit03 skipped it. **Fix = align the validator to allow internal apostrophes** (Codex, `scripts/compile_content.py`).
- **Dictation backfill homograph mis-glosses** (excluded-from-pool but wrong in DB): was/stellen/eten/begin/waar/best/Met/tot/over/se/Beste — needs the homograph-override mechanism (Codex). List in `docs/CONTENT_DEFECT_REGISTRY.md`-adjacent notes / prior handoffs.
- **`ADMIN_EMAILS`:** local dev now `admin@example.com,[admin email]` (recreated api). **LIVE still needs the same env change + Ramin registering that account** (deploy-time). See `project-admin-credentials` memory.
- 2 B2 units have a SECOND reading card that's un-glossed (I glossed the primary passage per unit).

---

## Session learnings (reusable conventions + gotchas)
- **Dictation authoring** (AUTHORING_GUIDE §14a): reuse an already-taught sentence + its single-sentence audio; `correct_response` byte-matches `tested_text`; **strip terminal `.?!`** from the graded string (keep sentence-initial capital + internal commas) for consistent strict grading; NO options/distractors; `orthography_strict: true`; TTS-only languages (nl now). Avoid multi-turn dialogue assets (a future recording plays the wrong audio — b1_unit08 fix precedent).
- **Reading glosses** (READING_TRACK_SPEC §4-5, brief at `scratchpad/reading_gloss_brief.md`): overlay-only `glosses:` map; keys = **exact surface tokens** (case-sensitive — the frontend matches exactly; the validator casefold-matches, so use exact case to satisfy both); gloss content/hard words (~40-70%), skip function words + proper names + apostrophe tokens; homograph-in-one-gloss → write a gloss covering both senses.
- **Import order / serve:** content import is additive (updates by unit order). Dictation content needs the `ck_exercises_type` constraint widened first (migration 0027 applied to dev DB via `alembic stamp 0026 && alembic upgrade head` — the dev DB is create_all/unversioned). Reading glosses ride in the existing `ContentItem.content` JSON (no migration).
- **Gotchas hit:** (a) `docker compose run` pytest exceeds the 120s Bash timeout — run `run_in_background: true`; and a stale isolated test DB with open connections blocks recreate → use a fresh unique DB name + `pg_terminate_backend`. (b) `UID` is a **readonly** bash var — don't use it as a loop var (use `UNIT_ID`). (c) This shell is **zsh** — unquoted `$VAR` does NOT word-split (write bash scripts to a file and run with `bash`, or use `${=VAR}`). (d) macOS `sed` has no `\b`. (e) recreate the running api container (`docker compose up -d --force-recreate api`) after backend code changes — `.env`/code changes need it; and rsync `frontend/dist/ → backend/web_dist/` + `nginx -s reload` to serve a new frontend build locally.
- **Codex dispatch:** `node <companion 1.0.6> task --cwd $REPO --background --write --fresh --prompt-file <file>`; poll `status <job> --json`, get `result <job>`. Always diff Codex's output before applying. Both Codex tasks this session were clean.

---

## Key file map
- **Specs (buildable, with build prompts):** `docs/DICTATION_EXERCISE_SPEC.md`, `docs/READING_TRACK_SPEC.md`.
- **Roadmap:** `docs/SONNET_BUILD_PROMPT_UPGRADES.md` (Phase H = dictation, Phase I = reading track).
- **State:** `docs/PROJECT_STATE.md` (Phases A–I shipped; dictation + reading track entries).
- **Authoring rules:** `docs/content/AUTHORING_GUIDE.md` §14a (dictation).
- **Name shortlist:** `docs/APP_NAME_SHORTLIST.md`.
- **Content:** dictation in `docs/content/realizations/nl/{a2,b1,b2}_unit*.yaml` + `overlays/en-nl/…`; reading `glosses:` maps in `docs/content/overlays/en-nl/{a2,b1,b2}_unit*.yaml`.
- **Ship runbook (Ramin's, from a prior session):** claude.ai artifact "Ship Lingo² — store, sign-in & feedback runbook" (Phase 1 = public HTTPS backend, the gating blocker).
- Memory: `project_2026-08-03_dictation-reading-modalities.md` (this session) + `project-admin-credentials` (updated).
