# Session handoff — 2026-07-13 (supersedes the 2026-07-12 NIGHT doc)

Read this + `docs/COORDINATOR_HANDBOOK.md` + root `CLAUDE.md` to resume.
**Everything below is committed and pushed to master. Verify state yourself
(`git log --oneline -5`, `git status --short`, `git worktree list`,
`bash scripts/verify.sh --content-only`) — do not trust this doc blindly.**

---

## 1. BUDGET & ROUTING (the thing that changed most)

- **Claude ~80% used, resets Friday 17:00. Codex ~95% LEFT, resets in ~6 days.**
  Ramin's standing instruction: **route aggressively to Codex.** Content
  authoring, content REVIEW, compiler validators, backend surgery, mechanical
  repair — all Codex. Reserve Claude for: coordination, verification, merges,
  and `frontend/src/**` (Codex does not own the frontend lane).
- **Codex can do fresh-context content review**, not just authoring — proved
  today on the de-en B1 wave (found 9 real defects). Use it; an Opus review
  costs ~200k tokens.
- **gpt-5.6 is NOT available on ChatGPT-account Codex.** Re-confirmed today
  with THREE model IDs (`gpt-5.6`, `gpt-5.6-codex`, `gpt-5.6-codex-high`) —
  all return a server-side 400 "not supported when using Codex with a ChatGPT
  account". The ChatGPT *website* offering 5.6 is a different product surface.
  gpt-5.5 is the ceiling. **DO NOT RE-PROBE THIS.**
- **Token economy:** the dominant cost is context re-sent per tool call.
  Polling Codex with status checks is the expensive anti-pattern. Instead
  background ONE watcher per task:
  `until <status-check> | grep -q completed; do sleep 90; done` with
  `run_in_background: true` — costs one call, wakes you once when done.

## 2. WHAT SHIPPED TODAY

**Speaking features (both Ramin-requested, backend complete):**
- **Pronunciation feedback.** `POST /stt/transcribe` takes optional
  `detail=words` → returns per-word `{word,start,end,probability}` from
  faster-whisper (`fda1641`, contract updated first). Frontend renders
  per-word clarity highlighting (`f1410aa`): `PronunciationFeedback.tsx`,
  wired through `useSpeechAnswer` → `VoiceCaptureControls`.
  **Invariant:** `probability` is a CLARITY heuristic, NOT phoneme-level
  accent scoring — never label a low-confidence word "wrong pronunciation".
  Only the SERVER STT path returns words (the client WASM model doesn't expose
  token probabilities), so absent feedback means "no signal", never "perfect".
- **Endless pronunciation practice.** `mode=speaking` on
  `POST /practice/{course_id}/batch` — generates `speak_repeat`/`speak_response`
  items from completed-lesson vocabulary, weakest-SRS-lexeme first, zero
  runtime LLM (`1aeeb25`).
- **Endless conversation practice.** `mode=conversation` — branching dialogue:
  app speaks a turn, learner replies (voice or typed), the matched variant
  selects the next node; unrecognized reply re-prompts instead of dead-ending.
  Node graph rides on the item (no migration) (`f894bce`).
- **Conversation runner UI DONE** (`e151f17`) — `ConversationRunner.tsx`.
  Multi-turn, so it does NOT go through `ExerciseRenderer` (which is one-shot):
  `PracticeCard` branches on `item.type === "conversation"`. Voice or typed
  replies, RTL + virtual keyboard, transcript history, never dead-ends.
  **Design note that matters:** `conversation` is deliberately NOT in
  `ExerciseType` — it's in a new `PracticeItemType = ExerciseType |
  "conversation"`, because adding it to `ExerciseType` would have broken the
  exhaustive exercise-type-registration test (the guard that exists precisely
  to stop unrendered types shipping). `asExerciseType()` narrows for the
  review/checkpoint/lesson runners, which can never receive one.
- **Both speaking features are now end-to-end usable. NEITHER HAS BEEN
  LIVE-PLAYED** — that is the outstanding verification (see §6).

**Content:**
- **B1 units 15-19 complete** across en + nl-en/fa-en/prs-en: 5 spine outcomes
  (complaints, advice, regret, future plans, summarizing) → 5 en realizations
  → 15 overlays. All fresh-context reviewed, manifest-wired, synced.
- **B2 SPINE TIER DESIGNED** (`0258a3f`) — 8 outcomes (argumentation, graded
  speculation, hedging/emphasis, complex narrative time, register adaptation,
  abstract discussion, negotiation, source synthesis). **B2 authoring is
  unblocked for all 24 English-anchored paths — nothing waits on Ramin.**
- **de-en B1 units 01-03** authored + reviewed + fixed (German lane opened).
- **+249 practice templates** across the 6 launch directions (`21b0ad4`),
  fill_in_blank-heavy, ZERO new multiple_choice — this is the fix for the
  "practice feels repetitive" complaint. Constraint discovered:
  `PracticeTemplateExerciseType` supports ONLY multiple_choice, fill_in_blank,
  word_order, translation, matching_pairs, listen_select.

**Validators (registry classes closed — backlog is now EMPTY):**
- boolean-coercion widened to all learner-facing fields (class 1.12)
- word_order/listen_order scrambled-answer (class 1.10) — hard-errors on
  bank-order copies, WARNS on other permutations (Dutch V2 alternates are
  legitimate alternate orderings, not bugs)
- media_asset_key (class 1.20) — dangling refs hard-error, text/audio
  mismatches warn. **Its first sweep found 6 real bugs** (fr/nl listen
  exercises playing the WRONG clip — unanswerable by listening), all fixed.
- Answer-shapes corpus is CLEAN — the "~226 known failing" note in
  docs/content/CLAUDE.md was STALE and has been corrected.

**Android APK:**
- `android-shell/` (Capacitor) + `.github/workflows/android-apk.yml`. CI builds
  the real web frontend (`--mode production.lan`), wraps it, Gradle-assembles a
  debug APK. Verified: 11.6 MB, web bundle inside, points at 192.168.4.4:8010,
  RECORD_AUDIO declared. **Deployed to `/home/ramin/shared/lingo.apk`** on the
  server (checksum-verified).
- **NOT VERIFIED: nobody has installed it and played a lesson.** Debug-signed
  (fine for side-loading, needs a keystore for Play Store). LAN-only.

## 3. LESSONS THAT COST REAL TIME TODAY

1. **Codex self-reports are unreliable in a specific way: it cannot run
   pytest or Docker.** It reported "py_compile passed" as verification twice.
   **Running the suite is ALWAYS the coordinator's job.** Isolated-DB recipe is
   in root CLAUDE.md; name a unique DB per run.
2. **A Codex validator passed ITS OWN armed test and still had a real gap.**
   The word_order validator only rejected answers matching the *bank* order;
   any other wrong permutation passed silently. Found by writing MY OWN armed
   test. **Always write your own adversarial test, never just re-run theirs.**
3. **Check diff SHAPE, not just validation-green.** The template expansion
   touched 101 files / 29k lines to add 249 templates — it had round-tripped
   every file through a YAML dumper. Validation was green and no boolean
   coercion occurred, but I only trusted it after a **semantic** comparison
   (parse old vs new, compare every template key: 0 lost, 0 altered). Do this
   for any suspiciously large diff.
4. **The first overlay compile catches realization token gaps.** Twice today
   (`leading` in u16, `months` in u18) a realization defect only surfaced when
   the first overlay for those units was compiled — because a realization can't
   be validated standalone (the compiler requires a paired overlay). Expect
   this in every new-unit wave; it is not a regression.
5. **Standalone validation runs produce FALSE "untaught token" errors** —
   vocabulary is cumulative across the course, so a unit must be validated with
   the full unit chain (01..N), not alone. Five of six "errors" in one wave were
   this. Put the CUMULATIVE command in the dispatch prompt.
6. **The preflight-verbatim effect held.** Defect yield per content wave:
   23 → 3 → 0. `docs/content/AUTHORING_PREFLIGHT.md` pasted VERBATIM into every
   authoring dispatch (not linked) remains the single highest-leverage practice.

## 4. DECISION BOUNDARY (Ramin corrected me on this — respect it)

Ramin's instruction: **"be the language expert, linguist, architect, engineer,
product manager — make the decision."** He does NOT want to be asked to approve
expert work, and does not want workflow-interrupting questions.

- **The coordinator OWNS:** curriculum design (I designed the whole B2 tier
  unilaterally — correct), architecture, review policy, model/budget routing,
  what to build next, technical trade-offs.
- **Ramin OWNS only:** money, legal (the CC BY-SA share-alike call), what "done"
  means commercially, launch timing, anything touching real users/credentials,
  and taste calls on HIS languages (e.g. the Dutch "u"-in-a-complaint-letter
  question — still open, non-blocking).
- **Do NOT ask "shall I do X?" for anything in the first list. Just do it and
  report.**

## 5. STANDING AUTHORIZATION

- **Admin credential:** `admin@example.com`, password in `~/.lingo_admin_pw`
  (chmod-600). Ramin explicitly authorized its use for building/operating the
  app (syncs, admin API, deploys). **Never write the password into memory,
  logs, scratch, or commits** — use
  `LINGO_ADMIN_EMAIL=admin@example.com LINGO_ADMIN_PASSWORD_FILE=~/.lingo_admin_pw`
  for `scripts/sync_dev_db.sh`, or `$(cat ~/.lingo_admin_pw)` inline.
- Deploy authority to 192.168.4.4 stands, provided the verification bar passed.

## 6. NEXT ACTIONS (in order)

1. **LIVE-PLAY the two new speaking features.** Both are code-complete and
   BUILD-green but nobody has played them. Per this project's own bar, that is
   not verification. Specifically: does a `mode=speaking` practice batch render;
   does the mic capture -> transcript -> grading path still work; does the
   per-word clarity highlighting appear (SERVER STT path only — the client WASM
   path returns no word confidences, so test with the client path disabled);
   does a conversation advance node-to-node and terminate. Do this BEFORE
   building anything else on top of them.
2. **B2 English units 01-03** → Codex, against the new B2 spine (`0258a3f`).
   Then X→en overlays. FULL review — a new CEFR tier is new territory, and B2's
   hedging/register/nuance content is exactly where a Sonnet/Codex author and a
   validator have the least traction. Expect review yield to CLIMB again.
3. **Grind the shallow paths toward B1 on Codex** (es/fr/it/ru/de/pl/ro/hi/ar
   are 3-32 units vs the launch pairs' ~90).
4. Ramin should install `/home/ramin/shared/lingo.apk` and play a lesson — the
   ONE verification nobody has done.

## 7. OPEN, NON-BLOCKING

- nl-en u15 complaint-LETTER glosses use formal "u" — the reviewer judged this
  correct Dutch business register; Ramin's taste call, no change made.
- en-hi and other courses: `de-en` overlay set now exists at B1 01-03 but the
  de-en course line in `content_manifest.txt` may need its B1 units wired when
  the lane grows.
- The practice engine cannot express writing_prompt/dialogue_response/
  speak_response as TEMPLATES (type enum limit) — a possible future backend task
  if practice variety still feels thin after the +249 templates reach the app.
