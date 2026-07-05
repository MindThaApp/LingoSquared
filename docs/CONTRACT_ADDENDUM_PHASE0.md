# Lingo² Shared Contract — Phase 0 Addendum

Status: proposed for merge into `docs/CONTRACT.md` after Ramin/Claude review.

This addendum extends the existing contract. Existing behavior remains authoritative unless this addendum explicitly replaces it.

## Locked product scope

Lingo² supports exactly 18 directed learning paths:

- `en ↔ nl`
- `en ↔ fr`
- `en ↔ de`
- `en ↔ it`
- `en ↔ es`
- `en ↔ ru`
- `en ↔ zh`
- `en ↔ fa`
- `en ↔ prs`

Every learning path has English on exactly one side. Non-English-to-non-English paths are out of scope.

The delivery sequence is:

1. A1 across all 18 learning paths.
2. A2 across all 18 learning paths, sequenced by observed usage.
3. B1/B2 in later demand-driven waves.
4. No C1/C2 completeness promise.

The existing CEFR enum may retain `C1` and `C2` for backward compatibility and future use. Their presence in the enum is not a delivery commitment.

## Learning path versus Course

A `learning_path` is the stable directed relationship between a source language and target language, for example `en-fa` or `fa-en`.

A `Course` remains a level-specific body of lessons within a learning path. Under the existing model, A1 and A2 are separate Course records.

Examples:

```json
{
  "learning_path": {
    "id": "uuid",
    "key": "en-fa",
    "source_language": "en",
    "target_language": "fa"
  },
  "courses": [
    { "id": "uuid", "level": "A1", "title": "Farsi A1" },
    { "id": "uuid", "level": "A2", "title": "Farsi A2" }
  ]
}
```

There are exactly 18 learning paths, but completing A1 and A2 across them produces at least 36 level-specific Course records.

Learning path invariants:

- `source_language != target_language`.
- Exactly one side is `en`.
- Both language codes must exist in the fixed supported-language set.
- `(source_language, target_language)` is unique.
- Direction is significant: `en-fa` and `fa-en` are different learning paths.
- Existing Course rows may have a nullable `learning_path_id` until backfilled.
- Legacy Course APIs continue to work during the transition.

## Four-layer content architecture

Published course content is assembled from four layers:

1. Universal competency spine.
2. Target-language realization.
3. Source-language localization and contrastive overlay.
4. Immutable content release.

### Universal competency spine

The universal spine defines communicative outcomes only.

It does not define a mandatory lesson order, grammar order, dialogue template, vocabulary list, or cultural scenario.

Each spine outcome has:

- A stable key such as `universal.a1.plans.make_simple_plans`.
- A CEFR level.
- A language-independent `can_do` statement.
- Capability prerequisites.
- Required modalities.
- Minimum assessment requirements.

Prerequisites express capability dependencies, not a universal sequence. A realization may reorder, split, combine, repeat, or reweight outcomes and may scaffold prerequisites concurrently.

### Target-language realization

A target-language realization owns:

- Unit and lesson ordering.
- Language-specific grammar progression.
- Vocabulary and phrase selection.
- Scenario design.
- Names and relationships.
- Register and politeness.
- Cultural notes.
- Script and phonology instruction.
- Target-language dialogues and stories.
- Target-language audio.
- Common learner errors.
- Mapping from realization objectives to zero or one universal spine outcomes.

Realizations are authored target-language-first. They must not be created by translating another realization sentence by sentence.

For a realization module or objective:

```json
{
  "content_key": "fa.a1.module0.script.connected_letters.01",
  "spine_outcome_id": null,
  "module_kind": "script_ramp",
  "weight": 1.0
}
```

A null `spine_outcome_id` is valid for language-specific Module 0 content, including:

- Chinese tones, pinyin, syllable structure, characters, and input methods.
- Russian Cyrillic decoding and sound-symbol correspondence.
- Farsi/Dari RTL behavior, connected letter forms, orthographic conventions, and short-vowel omission.
- Any language-specific phonology or orthography ramp.

A realization may map multiple objectives to one spine outcome or one integrated objective to multiple spine outcomes through mapping records.

### Dialogue originality invariant

For the same universal spine outcome, structurally identical dialogues across target-language realizations are a validation failure.

The validator must compare more than literal text. It must consider:

- Number and ordering of turns.
- Speaker roles.
- Speech-act sequence.
- Information slots.
- Branch structure.
- Correct-response position.
- Scenario metadata.

Translations with changed names are still structurally identical.

Each target-language realization must supply a culturally and linguistically natural scenario rather than a translated universal dialogue.

### Source-language overlay

A source-language overlay owns direction-specific:

- Instructions and explanations.
- Contrastive grammar notes.
- Translation guidance.
- Accepted response variants.
- Normalization exceptions.
- Likely learner errors.
- Hints.
- Exercise distractor overrides.

Distractor overrides are addressed by stable exercise content key:

```json
{
  "exercise_content_key": "en.a1.food.ordering.listen_select.004",
  "distractor_overrides": {
    "remove": ["literal-but-impossible-option"],
    "add": ["source-language-specific-confusion"],
    "replace": [
      {
        "from": "generic-distractor",
        "to": "direction-specific-distractor"
      }
    ],
    "order": [
      "correct-option",
      "direction-specific-distractor",
      "remaining-option"
    ]
  }
}
```

Overlay invariants:

- Reversing an exercise does not create a valid opposite-direction exercise automatically.
- Distractors must be independently checked for ambiguity in every direction.
- Overlay changes may not alter the stable semantic identity of a target-language objective.
- Farsi and Dari overlays and realizations remain distinct and are never auto-merged.

## Exercise type enum additions

The shared exercise type enum becomes:

- `multiple_choice`
- `translation`
- `reverse_translation`
- `fill_in_blank`
- `word_order`
- `matching_pairs`
- `listening_placeholder`
- `speaking_placeholder`
- `dialogue_response`
- `grammar_check`
- `flashcard`
- `reading_comprehension`
- `writing_prompt`
- `listen_select`
- `listen_type`
- `listen_order`
- `dialogue_comprehension`
- `speak_repeat`
- `speak_response`

The existing placeholder values are permanent legacy values:

- `listening_placeholder`
- `speaking_placeholder`

They must never be renamed, repurposed, or interpreted as working listening/speaking exercises. Existing placeholder rows continue to render as unavailable legacy content until replaced through a new content release.

New production content uses the explicit listening and speaking types.

### Listening exercise semantics

`listen_select`:

- Audio is the primary prompt.
- Transcript is hidden until after submission.
- Response identifies one or more options.

`listen_type`:

- Audio is the primary prompt.
- Transcript is hidden until after submission.
- Response is typed text graded through an `answer_spec`.

`listen_order`:

- Audio is the primary prompt.
- Response is an ordered token list.
- Transcript is hidden until after submission.

`dialogue_comprehension`:

- Prompt references a dialogue, story, or selected dialogue nodes.
- May combine audio and text depending on the authored objective.
- Response is a constrained comprehension answer.

### Speaking exercise semantics

`speak_repeat`:

- Learner records a supplied word, phrase, or sentence.
- Initial assessment may use speech recognition to test whether expected words were recognized.
- The system must not claim phoneme-level pronunciation precision unless the configured assessor actually supports it.

`speak_response`:

- Learner records a response to a constrained prompt or dialogue turn.
- The authored `answer_spec` defines expected concepts, words, or response families.
- Open conversation is not implied.

Speaking exercises may provide a skip/fallback path where microphone or recognition support is unavailable. The fallback must be recorded and must not be misrepresented as a successful speaking assessment.

## Per-objective unlocking

The existing whole-course rule that locks all speaking units until 100% of reading/writing units are complete is deprecated.

New releases use objective-level prerequisites.

Unlock state is determined from:

- Required learning objectives.
- Required mastery thresholds.
- Explicit prerequisite content keys where necessary.
- Release-specific rules.

Reading, listening, speaking, and writing may be interleaved from the beginning of a course.

Migration invariants:

- Existing completions remain complete.
- A migration must not relock content already completed by a user.
- Legacy releases may retain the old gate until the user is deliberately migrated.
- The frontend must use server-returned unlock state and must not infer it independently.

## New and extended data entities

The following names describe the authoritative logical schema. Exact SQLAlchemy class names may use singular CamelCase equivalents.

### `learning_paths`

Represents one stable directed hub path.

Fields:

- `id`: UUID/string primary key.
- `key`: unique stable key such as `en-fa`.
- `source_language`: language-code foreign key.
- `target_language`: language-code foreign key.
- `title`: optional display title.
- `active`: boolean, default true.
- `created_at`.
- `updated_at`.

Constraints:

- Unique `(source_language, target_language)`.
- Source and target differ.
- Exactly one side is English.

Courses gain a nullable `learning_path_id` foreign key for additive compatibility.

### `learning_objectives`

Represents universal or realization-specific capabilities.

Fields:

- `id`: UUID/string primary key.
- `key`: globally unique stable key.
- `scope`: `universal` or `realization`.
- `language_code`: nullable for universal objectives; required for realization objectives.
- `cefr_level`.
- `title`.
- `can_do`.
- `spine_objective_id`: nullable self-reference or reference to a universal objective.
- `module_kind`: nullable; examples include `script_ramp`, `phonology_ramp`, `input_ramp`, and `orthography_ramp`.
- `modalities`: JSON array.
- `assessment_requirements`: JSON array.
- `metadata`: JSON object.
- `created_at`.
- `updated_at`.

Supporting mapping tables may include:

- `learning_objective_prerequisites`
- `lesson_objectives`
- `exercise_objectives`

A prerequisite mapping includes a required mastery threshold and is interpreted as a capability dependency rather than a universal content order.

### `content_releases`

Represents an immutable assembled publication.

Fields:

- `id`: UUID/string primary key.
- `learning_path_id`.
- `course_id`: nullable during pre-publication assembly.
- `version`: stable release version.
- `cefr_level`.
- `schema_version`.
- `status`: `draft`, `review`, `published`, `retired`.
- `manifest`: JSON object.
- `content_checksum`.
- `created_at`.
- `published_at`: nullable.
- `retired_at`: nullable.

Constraints:

- Unique `(learning_path_id, cefr_level, version)`.
- Published releases are immutable.
- A retired release remains readable for pinned users and historical attempts.

### `content_keys`

Maps stable authored identities to release-specific entities.

Fields:

- `id`: UUID/string primary key.
- `key`: globally unique stable authored key.
- `entity_type`: such as `course`, `unit`, `lesson`, `exercise`, `dialogue`, `dialogue_node`, or `content_item`.
- `entity_id`: release-specific UUID/string.
- `content_release_id`.
- `supersedes_content_key_id`: nullable.
- `created_at`.

A content key must never be reassigned to semantically unrelated material.

### `media_assets`

Represents immutable generated or recorded media.

Fields:

- `id`: UUID/string primary key.
- `checksum`: unique content checksum used by the asset API.
- `content_release_id`: nullable for reusable assets.
- `language_code`.
- `kind`: `audio`, `image`, or another explicitly supported media type.
- `purpose`: such as `graded_listening`, `dialogue`, `teaching`, or `pronunciation_model`.
- `mime_type`.
- `storage_path`.
- `byte_size`.
- `duration_ms`: nullable.
- `provider`: such as `self_hosted_tts`, `elevenlabs`, or `recorded`.
- `voice_key`: nullable.
- `generation_metadata`: JSON object.
- `license_metadata`: JSON object.
- `created_at`.

Assets are content-addressed and immutable. Corrected audio receives a new checksum.

### `dialogues`

Represents a target-language-first dialogue or story.

Fields:

- `id`: UUID/string primary key.
- `content_release_id`.
- `content_key_id`.
- `language_code`.
- `title`.
- `scenario`: JSON object.
- `register`.
- `cultural_context`: JSON object.
- `structure_fingerprint`.
- `metadata`: JSON object.
- `created_at`.

### `dialogue_nodes`

Represents one dialogue utterance, narration step, or learner decision.

Fields:

- `id`: UUID/string primary key.
- `dialogue_id`.
- `node_key`: unique within the dialogue.
- `kind`: `utterance`, `narration`, `learner_turn`, `comprehension`, or `ending`.
- `speaker_key`: nullable.
- `text_blocks`: JSON array.
- `media_asset_id`: nullable.
- `order_hint`: nullable.
- `metadata`: JSON object.

### `dialogue_edges`

Represents allowed transitions.

Fields:

- `id`: UUID/string primary key.
- `dialogue_id`.
- `source_node_id`.
- `target_node_id`.
- `response_key`: nullable.
- `condition`: JSON object.
- `feedback`: JSON object.
- `order`.
- `metadata`: JSON object.

A dialogue may be linear or branching. Branching does not require a general game engine.

### `content_review`

Records AI cross-review evidence.

Fields:

- `id`: UUID/string primary key.
- `content_release_id`.
- `content_key_id`: nullable when the review covers a complete release.
- `review_stage`.
- `reviewer_system`: for example `codex` or `claude`.
- `reviewer_model`.
- `fresh_context`: boolean.
- `status`: `pending`, `passed`, `failed`, or `needs_revision`.
- `findings`: JSON array.
- `notes`: text.
- `created_at`.
- `completed_at`: nullable.

A published release must have the required review stages recorded as passed. Professional native-speaker review is not a publication gate.

### `answer_specs`

Extends deterministic and constrained grading.

Fields:

- `id`: UUID/string primary key.
- `exercise_id`: unique foreign key.
- `accepted_variants`: JSON array.
- `normalization`: JSON object.
- `rejected_near_matches`: JSON array.
- `rubric`: JSON object.
- `explanation`: text.
- `error_feedback`: JSON object.
- `created_at`.
- `updated_at`.

Example:

```json
{
  "accepted_variants": [
    { "value": "I am well, thank you.", "status": "correct" },
    { "value": "I'm well, thank you.", "status": "correct" },
    {
      "value": "I am good, thank you.",
      "status": "acceptable_with_note",
      "note": "Natural in some varieties; the lesson target is 'well'."
    }
  ],
  "normalization": {
    "unicode": "NFC",
    "trim": true,
    "collapse_whitespace": true,
    "case_sensitive": false,
    "punctuation": "terminal_optional",
    "diacritics": "required"
  },
  "rejected_near_matches": [],
  "rubric": {
    "mode": "deterministic_variants"
  }
}
```

Normalization is language- and exercise-specific. It must not globally remove distinctions that carry meaning.

### `content_issue_reports`

Records learner reports about specific exercises or content.

Fields:

- `id`: UUID/string primary key.
- `reporter_user_id`.
- `exercise_id`.
- `content_release_id`.
- `content_key_id`: nullable for legacy exercises.
- `attempt_id`: nullable.
- `category`: `answer_should_be_accepted`, `wrong_translation`, `ambiguous_prompt`, `bad_distractor`, `audio_problem`, `script_problem`, `cultural_problem`, `technical_problem`, or `other`.
- `description`: optional learner text.
- `learner_response`: optional JSON snapshot.
- `client_context`: JSON object.
- `status`: `open`, `triaged`, `accepted`, `rejected`, `fixed`, or `duplicate`.
- `triage_notes`: nullable text.
- `duplicate_of_id`: nullable self-reference.
- `created_at`.
- `triaged_at`: nullable.
- `resolved_at`: nullable.

Issue reports are append-only from the learner’s perspective. Administrative status updates are audited.

### `exercise_attempts`

Exercise attempts remain an append-only learning-event record.

Required or newly standardized fields:

- `id`.
- `user_id`.
- `exercise_id`.
- `content_release_id`: nullable for legacy attempts.
- `lesson_session_id`: nullable.
- `client_operation_id`: nullable for legacy attempts, unique per user when present.
- `device_id`: nullable.
- `response`: JSON.
- `correct`.
- `outcome`: `correct`, `acceptable_with_note`, `incorrect`, `skipped`, or `unassessed`.
- `xp_awarded`.
- `feedback_snapshot`: JSON object.
- `objective_snapshot`: JSON array.
- `occurred_at`.
- `received_at`.
- `created_at`.

Attempts must not be updated or deleted as part of content import, reseeding, or release replacement.

If account deletion is later required, deletion or anonymization must use a dedicated user-data policy rather than content cascades.

### Supporting learner-state entities

The implementation may add:

- `user_learning_path_state`
- `user_objective_mastery`
- `push_subscriptions`
- `notification_preferences`
- `sync_operations`

`user_learning_path_state` pins a user to an active content release until a controlled migration occurs.

`user_objective_mastery` layers objective-level adaptation over the existing SM-2 review scheduler.

## Answer response extension

`POST /exercises/{exercise_id}/answer` remains backward compatible and gains additive fields:

```json
{
  "correct": true,
  "outcome": "correct",
  "correct_response": "accepted canonical response",
  "accepted_responses": [
    "accepted canonical response",
    "accepted alternative"
  ],
  "xp_awarded": 10,
  "feedback": "string",
  "explanation": "string",
  "objective_updates": [
    {
      "objective_id": "uuid",
      "objective_key": "fa.a1.greetings.open_close_exchange",
      "mastery": 0.42,
      "next_due_at": "2026-07-03T12:00:00Z"
    }
  ]
}
```

Existing clients may ignore the new fields.

The backend remains authoritative for online grading. Offline clients may use bundled answer specifications for immediate feedback, but canonical XP, streak, mastery, and scheduling are reconciled by `/sync/batch`.

## Content issue API

### Report an issue

`POST /exercises/{exercise_id}/issues`

Authentication required.

Request:

```json
{
  "attempt_id": "uuid or null",
  "category": "answer_should_be_accepted",
  "description": "My answer has the same meaning.",
  "learner_response": "the submitted response",
  "client_context": {
    "content_release_id": "uuid",
    "app_version": "string",
    "offline": false,
    "locale": "fa"
  }
}
```

Response:

```json
{
  "id": "uuid",
  "status": "open",
  "created_at": "2026-07-02T12:00:00Z"
}
```

The endpoint must not expose correct answers beyond what the learner has already received through grading.

### Triage queue

`GET /admin/content/issues?status=open&category=&language=&cursor=&limit=`

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "exercise_id": "uuid",
      "content_key": "fa.a1.greetings.exercise.004",
      "content_release_id": "uuid",
      "category": "answer_should_be_accepted",
      "description": "My answer has the same meaning.",
      "learner_response": "string or structured JSON",
      "status": "open",
      "created_at": "2026-07-02T12:00:00Z"
    }
  ],
  "next_cursor": "opaque cursor or null"
}
```

`PATCH /admin/content/issues/{issue_id}`

Request:

```json
{
  "status": "accepted",
  "triage_notes": "Add as an accepted variant in the next content release.",
  "duplicate_of_id": null
}
```

Response returns the updated issue record.

Fixing an issue produces a new content release. Published content is not edited in place.

## Audio and TTS policy

### Graded content audio

Graded listening audio is a pre-generated immutable media asset.

It must not depend on a live `/tts` request during a lesson.

Required properties:

- Stable media checksum.
- Language code.
- Voice identifier.
- Provider.
- Generation metadata.
- Review status.
- Duration and MIME type.
- Content-release association.
- Availability in offline bundles.

### Provider priority

The primary content-audio generation route is a self-hosted TTS provider running on the Debian server.

The implementation must use a provider abstraction that can support Piper-, XTTS-, or equivalent self-hosted engines without coupling authored content to one engine.

Provider selection is per language and voice:

1. Approved self-hosted voice/model.
2. Optional ElevenLabs voice for a supported language.
3. Human-recorded asset where available.
4. Generation failure requiring content triage.

ElevenLabs does not support `fa` or `prs` for this project and must never be called for those language codes.

A self-hosted model must be evaluated for actual language support before being approved. “Self-hosted” alone does not imply acceptable pronunciation or dialect.

Generated content audio must pass:

- Non-empty and decodable audio validation.
- Expected-duration sanity checks.
- Text/audio language matching where technically available.
- AI cross-review of intelligibility.
- Manual playback spot checks during content review.
- Correct voice and dialect metadata.
- No clipping or excessive silence.

Model files, generated audio, and voice samples must comply with their licenses. Voice cloning requires documented permission for the source voice.

### Runtime `/tts`

`POST /tts` remains for teaching assistance and non-graded playback.

Request:

```json
{
  "text": "سلام",
  "language_code": "fa"
}
```

The backend provider order is:

1. Configured and healthy self-hosted TTS for the language.
2. ElevenLabs only when the language is supported and quota permits.
3. Browser-TTS fallback response.

Binary response:

- `audio/mpeg`, `audio/wav`, or another documented audio MIME type.

Fallback response:

```json
{
  "use_browser_tts": true,
  "reason": "unsupported_language"
}
```

Allowed fallback reasons:

- `unsupported_language`
- `quota_exceeded`
- `provider_error`
- `provider_unavailable`

Runtime TTS output must never be substituted for a missing graded-listening asset.

## Immutable content API

The PWA consumes immutable release artifacts separately from personalized state.

### Release manifest

`GET /content/releases/{release_id}/manifest`

Response:

```json
{
  "id": "uuid",
  "learning_path_id": "uuid",
  "learning_path_key": "en-fa",
  "course_id": "uuid",
  "cefr_level": "A1",
  "version": "2026.1.0",
  "schema_version": "1",
  "content_checksum": "sha256-hex",
  "published_at": "2026-07-02T12:00:00Z",
  "bundles": [
    {
      "id": "unit-01",
      "kind": "unit",
      "title": "string",
      "checksum": "sha256-hex",
      "byte_size": 123456,
      "required_asset_checksums": [
        "sha256-hex"
      ]
    }
  ]
}
```

Headers:

- `ETag` derived from the manifest checksum.
- `Cache-Control: public, max-age=31536000, immutable` for checksum/version-addressed published manifests.
- Conditional requests must support `If-None-Match`.

Draft and review manifests are admin-only and must not be publicly cacheable.

### Release bundle

`GET /content/releases/{release_id}/bundles/{bundle_id}`

Successful response:

- Content type documented by the manifest, normally a versioned JSON media type or compressed archive.
- Body contains immutable lessons, teaching content, exercises, dialogue data, objective mappings, offline grading specifications, and asset references.
- `ETag` equals the bundle checksum.
- `Cache-Control: public, max-age=31536000, immutable`.

The bundle must not contain:

- User progress.
- Push data.
- Access tokens.
- Other personalized state.
- Secrets or provider credentials.

Offline answer specifications are inspectable by the client. They are not a security boundary. The server still computes canonical rewards and progress during synchronization.

### Content asset

`GET /content/assets/{checksum}`

Response:

- Raw immutable asset bytes.
- Correct `Content-Type`.
- `Content-Length` where known.
- `ETag` derived from the checksum.
- `Cache-Control: public, max-age=31536000, immutable`.
- Byte-range support for audio where practical.

A checksum mismatch is a server error and the asset must not be served as valid content.

## Personalized path-state API

`GET /me/path-state/{learning_path_id}`

Authentication required.

Response:

```json
{
  "learning_path_id": "uuid",
  "learning_path_key": "en-fa",
  "active_release_id": "uuid",
  "active_course_id": "uuid",
  "cefr_level": "A1",
  "current_content_key": "fa.a1.unit.03.lesson.02",
  "unlocked_content_keys": [
    "fa.a1.unit.03.lesson.02",
    "fa.a1.unit.03.listening.01"
  ],
  "objective_mastery": [
    {
      "objective_id": "uuid",
      "objective_key": "fa.a1.greetings.open_close_exchange",
      "mastery": 0.64,
      "due_at": "2026-07-03T12:00:00Z"
    }
  ],
  "last_sync_cursor": "opaque cursor",
  "updated_at": "2026-07-02T12:00:00Z"
}
```

The server is authoritative for release pinning and unlock state.

## Offline synchronization API

`POST /sync/batch`

Authentication required.

Request:

```json
{
  "device_id": "client-generated stable UUID",
  "base_cursor": "opaque cursor or null",
  "operations": [
    {
      "id": "client-generated operation UUID",
      "sequence": 42,
      "occurred_at": "2026-07-02T11:58:00Z",
      "type": "exercise_attempt",
      "content_release_id": "uuid",
      "payload": {
        "exercise_id": "uuid",
        "exercise_content_key": "fa.a1.greetings.exercise.004",
        "lesson_session_id": "uuid",
        "response": "سلام",
        "offline_outcome": "correct"
      }
    }
  ]
}
```

Initially supported operation types:

- `lesson_started`
- `exercise_attempt`
- `lesson_completed`
- `dialogue_progress`
- `issue_report`

Response:

```json
{
  "accepted": [
    {
      "id": "operation UUID",
      "status": "applied",
      "canonical_result": {
        "xp_awarded": 10,
        "outcome": "correct"
      }
    }
  ],
  "duplicates": [
    {
      "id": "previously applied operation UUID",
      "status": "duplicate",
      "canonical_result": {
        "xp_awarded": 10,
        "outcome": "correct"
      }
    }
  ],
  "rejected": [
    {
      "id": "operation UUID",
      "status": "rejected",
      "error": {
        "code": "unknown_content_release",
        "message": "The referenced content release is unavailable."
      }
    }
  ],
  "canonical_state": {
    "total_xp": 120,
    "streak_days": 3,
    "objective_updates": [],
    "path_state_updated_at": "2026-07-02T12:00:00Z"
  },
  "next_cursor": "opaque cursor"
}
```

Idempotency rules:

- Operation IDs are client-generated UUIDs.
- `(user_id, operation_id)` is unique.
- Replaying an accepted operation returns `duplicate` with the original canonical result.
- An operation may never award XP twice.
- Batch processing is atomic per operation, not necessarily atomic for the complete batch.
- The server records canonical `received_at` separately from client `occurred_at`.
- Client timestamps do not independently determine streaks or rewards.
- Exercise attempts are append-only.
- Lesson completion is idempotent.
- Objective mastery and SM-2 scheduling are computed server-side.
- Offline results are provisional until synchronized.
- A user may synchronize work from a pinned retired release.
- Unknown, malformed, or unauthorized operations are rejected individually.
- The client must retain rejected operations until the user resolves or deliberately discards them.
- Background Sync is optional; clients must also retry on launch, foregrounding, and restored connectivity.

## Web Push API

Push requires HTTPS and a registered service worker outside localhost development.

A user may have multiple push subscriptions.

### Create or replace a subscription

`POST /me/push-subscriptions`

Request:

```json
{
  "endpoint": "https://push-service.example/subscription-id",
  "expiration_time": null,
  "keys": {
    "p256dh": "base64url public key",
    "auth": "base64url auth secret"
  },
  "device": {
    "id": "client-generated UUID",
    "label": "Ramin's phone",
    "user_agent": "string"
  }
}
```

Response:

```json
{
  "id": "uuid",
  "device_id": "client-generated UUID",
  "enabled": true,
  "created_at": "2026-07-02T12:00:00Z"
}
```

The endpoint is unique. Resubmitting the same endpoint updates its user/device association safely rather than creating duplicates.

Push endpoints and encryption keys are sensitive data.

The backend removes or disables subscriptions after terminal push-provider responses such as `404` or `410`.

### Delete a subscription

`DELETE /me/push-subscriptions/{subscription_id}`

Response:

```json
{
  "deleted": true
}
```

Deleting a subscription that is already absent may return the same successful response for idempotency.

## Notification preferences API

`GET /me/notification-preferences`

Response:

```json
{
  "enabled": true,
  "timezone": "Europe/London",
  "reminder_time": "19:00",
  "days_of_week": [1, 2, 3, 4, 5, 6, 7],
  "types": {
    "daily_reminder": true,
    "streak_risk": true,
    "reviews_due": false,
    "content_updates": false
  },
  "updated_at": "2026-07-02T12:00:00Z"
}
```

`PUT /me/notification-preferences`

Request:

```json
{
  "enabled": true,
  "timezone": "Europe/London",
  "reminder_time": "19:00",
  "days_of_week": [1, 2, 3, 4, 5],
  "types": {
    "daily_reminder": true,
    "streak_risk": true,
    "reviews_due": false,
    "content_updates": false
  }
}
```

Response returns the complete saved preference object.

Rules:

- Timezone must be a recognized IANA timezone.
- `days_of_week` uses ISO numbering: Monday `1` through Sunday `7`.
- Push permission is controlled by the browser; saving preferences does not imply browser permission.
- Notifications must not be sent when preferences are disabled.
- Notification text must use the learner’s source/UI language where available.

## PWA caching and deployment requirements

The eventual deployed PWA and API should be served through HTTPS on one origin:

```text
https://lingo.example/
https://lingo.example/api/
```

The service worker caches:

- Versioned application-shell assets.
- Immutable release manifests.
- Downloaded course bundles.
- Checksum-addressed media.

IndexedDB stores:

- Parsed structured content.
- Download metadata.
- Personalized state snapshots.
- Unsynchronized operation outbox.
- Synchronization acknowledgements.

Personalized authenticated responses must not be stored in a shared public cache.

Application-shell version, offline-database schema version, API contract version, and content-release version are independent.

A service-worker update must not delete:

- Downloaded content still used by a pinned release.
- Unsynchronized operations.
- Pending recordings.
- Synchronization acknowledgements.

Runtime TTS and remote speaking assessment are unavailable offline. Required graded-listening audio must be present in the downloaded bundle. Speaking recordings may be queued only after explicit microphone and retention consent.

## Additive migration and live-data policy

All migrations from the current live schema must follow these rules:

1. Initial schema changes are additive.
2. New foreign keys on existing tables are nullable until safely backfilled.
3. New non-null columns require safe server defaults or a staged migration.
4. Existing exercise UUIDs are never deleted, reassigned, or reused.
5. Stable content keys are never reassigned to unrelated content.
6. Published content releases are immutable.
7. Corrections create a new release.
8. Retired releases remain readable for pinned users and historical attempts.
9. Existing users remain pinned to their current release until a controlled migration.
10. Controlled migration must preserve completed lessons and earned progress.
11. New prerequisite rules must not relock already completed content.
12. Exercise attempts are append-only and must not be cascade-deleted by content operations.
13. Review history and issue reports survive release retirement.
14. Legacy placeholder exercise values remain valid.
15. Enum expansion is forward-only.
16. Seed and import operations are idempotent and non-destructive by default.
17. An ordinary seed run may create missing reference data and missing seed courses, but may not delete or replace an existing course.
18. Destructive replacement requires a separate explicit administrative command and is not part of deployment.
19. Tests must run against an isolated test database.
20. Downgrade functions must not imply that production downgrade is safe when it would remove user or historical data.

The existing delete-and-recreate behavior in `import_content()` is incompatible with this policy and must be removed from the ordinary seed path before the next production seed.

## AI cross-review protocol

Professional native-speaker review is not a publication gate. Quality control uses automated validation and independent AI cross-review by Codex and Claude.

The accepted quality-risk tradeoff does not remove the requirement to record review evidence.

### Separation of roles

For each review round:

- One system authors or revises the content.
- The other system reviews it in fresh context.
- The reviewer must receive the curriculum objective, target-language content, overlay, and validation rules.
- The reviewer must not receive hidden chain-of-thought or an author-produced justification intended to persuade it.
- A failed review returns structured findings and blocks publication until addressed.
- The original author may not mark its own disputed finding resolved without a new independent pass.

### Fresh-context round-trip back-translation

For every target-language teaching item, assessed sentence, dialogue turn, and accepted answer:

1. The reviewer receives the target-language text without its authored source translation.
2. The reviewer produces a literal back-translation.
3. The reviewer produces a natural back-translation.
4. The automated review compares both against the authored meaning.
5. Material differences in meaning, register, subject, tense/aspect, number, negation, politeness, or implication are findings.
6. The reviewer then sees the authored translation and classifies the difference.
7. Approved differences are recorded explicitly rather than silently ignored.

Back-translation is a diagnostic process, not proof of correctness.

### Adversarial learner pass

The independent reviewer attempts each exercise as several plausible learners:

- A literal translator.
- A learner using a natural synonym.
- A learner omitting optional punctuation.
- A learner using an alternate contraction or word order.
- A learner making a source-language interference error.
- A learner selecting each distractor for a plausible reason.

The pass must:

- Populate accepted-answer variants.
- Identify acceptable-with-note responses.
- Identify invalid near matches.
- Flag ambiguous prompts.
- Flag multiple correct options.
- Flag distractors that are impossible, offensive, misleading, or accidentally correct.
- Check that the exercise tests taught content.
- Check that feedback explains the actual distinction.
- Check both learning directions independently.

### Deterministic validators

Publication requires deterministic validation of at least:

- YAML/JSON schema.
- Stable-key uniqueness.
- Supported language codes.
- Source/target direction.
- CEFR values.
- Objective references.
- Capability-prerequisite references.
- Module 0 null-spine mappings.
- Lesson and exercise ordering within a realization.
- No correct-answer leakage in online graded payloads.
- Required audio assets.
- Asset checksums.
- Dialogue graph reachability.
- Dialogue node and edge integrity.
- Dialogue structural originality across target languages.
- Accepted-answer presence.
- Duplicate or conflicting accepted answers.
- Distractor uniqueness.
- Distractor override references.
- Every assessed concept being taught or explicitly prerequisite.
- Modality coverage.
- RTL/LTR metadata.
- Unicode normalization.
- Script codepoint policy.
- Farsi/Dari separation.
- Placeholder types absent from newly published production lessons.

### Script codepoint purity

Each realization defines an explicit allowed/flagged codepoint policy.

Validators must detect visually similar but semantically or orthographically inconsistent characters.

At minimum, Farsi/Dari validation must distinguish:

- Arabic Yeh `ي` (`U+064A`) from Persian Yeh `ی` (`U+06CC`).
- Arabic Kaf `ك` (`U+0643`) from Persian Keheh `ک` (`U+06A9`).
- Arabic and Persian digit sets where the realization policy distinguishes them.
- Zero-width non-joiner usage.
- Unexpected Latin confusables.
- Mixed normalization forms.

The exact allowed form is configured per language and orthographic policy. The validator must not blindly normalize a flagged character into an approved one without reporting it.

Chinese validation must include:

- Simplified-character policy.
- Unexpected traditional-only characters unless explicitly annotated.
- Pinyin tone-mark or tone-number consistency.
- Full-width/half-width punctuation policy.

Russian validation must include:

- Cyrillic/Latin confusables.
- Unexpected mixed-script tokens.
- `ё` policy where relevant.

### Farsi/Dari cross-diff

Every Farsi and Dari release pair undergoes a cross-diff.

The cross-diff must flag:

- Exact duplicated sentences.
- Exact duplicated dialogues.
- Shared explanations.
- Shared cultural notes.
- Vocabulary marked as equivalent without separate review.
- Register or pronunciation notes copied unchanged.
- Audio or voice assets reused across `fa` and `prs`.
- Orthographic differences hidden by normalization.

Flags are not automatic rejection for genuinely shared forms such as common greetings or cognates. Every flagged reuse requires an explicit recorded disposition.

Farsi and Dari must never be auto-synchronized after approval.

## Phase sequencing

Phase 0:

- Universal A1 competency spine.
- This contract addendum.
- Additive schema and migration artifacts.
- Non-destructive seed/import policy.
- Content validation foundation.
- PWA content/release API design.

Phase 1:

- `en ↔ fa` A1 production proof.
- Objective-level unlocking.
- Multi-answer grading.
- Pre-generated graded listening.
- Dialogue/story foundation.
- Per-exercise issue reporting and triage schema/API.
- Offline bundle proof.

Phase 2:

- `en ↔ prs` A1.
- Production factory.
- Factory UI is deliberately limited to:
  - Coverage dashboard.
  - Validation display.
  - RTL preview.
  - Content-issue triage queue.
- No in-app lesson editor in this phase.
- YAML/Git remains the canonical authoring workflow.

Phase 3:

- Latin-script A1 paths, produced in controlled parallel waves.

Phase 4:

- `en ↔ ru` A1 and Cyrillic-specific validation/tooling.

Phase 5:

- `en ↔ zh` A1 and Chinese-specific script/input/tooling.

Phase 6:

- A2 breadth across all 18 learning paths.
- Production order is prioritized by observed usage while retaining the commitment to complete all 18 A2 paths.

B1/B2 follow in later demand-driven waves.
