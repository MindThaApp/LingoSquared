// Types mirror /Users/raminazizi/dev/LingoSquared/docs/CONTRACT.md exactly.
// Keep this file in sync with the contract; do not invent fields it doesn't define.

// NOTE: "devanagari" and "arabic_msa" are frontend-only extensions beyond
// CONTRACT.md's documented `script` enum (latin/cyrillic/han/arabic) —
// devanagari was already added this way for hi; arabic_msa follows the
// same precedent, added 2026-07-12 to fix an untypeable-Arabic blocker.
// "arabic" (Perso-Arabic: fa/prs) and "arabic_msa" (true MSA Arabic: ar)
// are deliberately DISTINCT codes, not a rename of "arabic" — they use
// genuinely different codepoints (Perso-Arabic keheh ک/farsi-yeh ی vs.
// Arabic kaf ك/yeh ي) and a rename would have required auditing every
// fa/prs consumer for zero benefit. See lib/scripts.ts for the two
// keyboard layouts and docs/CONTRACT.md's `script` field, which the live
// API still returns as "arabic" for `ar` today (this frontend-only code
// is a LOCAL LANGUAGE_SCRIPT lookup keyed by language code, not derived
// from the API's `Language.script` field, so this is safe).
export type ScriptCode = "latin" | "cyrillic" | "han" | "arabic" | "arabic_msa" | "devanagari";
export type Direction = "ltr" | "rtl";

export interface Language {
  code: string;
  name: string;
  native_name: string;
  script: ScriptCode;
  direction: Direction;
}

export interface LanguagePair {
  source_language: string;
  target_language: string;
  course_count: number;
}

export type CefrLevel = "A1" | "A2" | "B1" | "B2" | "C1" | "C2";

export interface CourseSummary {
  id: string;
  source_language: string;
  target_language: string;
  title: string;
  level: CefrLevel;
  unit_count: number;
}

export interface CourseDetail extends CourseSummary {
  description: string;
}

export type UnitSection = "reading_writing" | "speaking";

export interface UnitSummary {
  id: string;
  title: string;
  order: number;
  lesson_count: number;
  completed_lesson_count: number;
  section: UnitSection;
  locked: boolean;
  checkpoint_passed: boolean;
  /** Stable authoring key, e.g. "en.a1.unit06.family" — null for units
   * imported before content_key tracking existed. Used to derive a
   * per-unit topical icon (see lib/unitIcons.ts); not otherwise
   * meaningful to the frontend. */
  content_key: string | null;
}

export interface LessonSummary {
  id: string;
  title: string;
  order: number;
  exercise_count: number;
}

export type ExerciseType =
  | "multiple_choice"
  | "translation"
  | "reverse_translation"
  | "fill_in_blank"
  | "word_order"
  | "matching_pairs"
  | "listening_placeholder"
  | "speaking_placeholder"
  | "dialogue_response"
  | "grammar_check"
  | "flashcard"
  | "reading_comprehension"
  | "writing_prompt"
  | "listen_select"
  | "listen_type"
  | "dictation"
  | "speak_response"
  | "listen_order"
  | "dialogue_comprehension"
  | "speak_repeat";

export interface TextBlock {
  text: string;
  language_code: string;
  direction: Direction;
  speaker?: string;
}

export interface ExercisePrompt {
  text_blocks: TextBlock[];
  options?: string[];
  word_bank?: string[];
  pairs?: { left: string; right: string }[];
  audio_text?: string;
  audio_language_code?: string;
  answer_language_code?: string;
  media_asset_key?: string;
  [key: string]: unknown;
}

export interface Exercise {
  id: string;
  type: ExerciseType;
  order: number;
  prompt: ExercisePrompt;
}

export type TeachingCardKind =
  | "vocabulary"
  | "phrase"
  | "grammar_note"
  | "dialogue"
  | "pronunciation_note"
  | "cultural_note"
  | "reading";

// 2026-07-07 vocabulary-example addition (docs/CONTRACT.md): an example
// sentence showing the card's word in real context — target-language
// sentence first, then an optional source-language gloss block.
export interface TeachingExample {
  text_blocks: TextBlock[];
}

export interface TeachingCard {
  kind: TeachingCardKind;
  title?: string;
  text_blocks: TextBlock[];
  note?: string;
  examples?: TeachingExample[] | null;
  // Reading-track tap-to-gloss (docs/READING_TRACK_SPEC.md §4–5). Present
  // only on `reading` cards whose overlay authors a per-word gloss map:
  // exact-surface-token -> in-context English gloss. Absent on all other
  // cards (and on the 320 existing reading cards), which render unchanged.
  glosses?: Record<string, string>;
}

export interface Lesson {
  id: string;
  unit_id: string;
  title: string;
  teaching: TeachingCard[];
  exercises: Exercise[];
}

export interface MatchingPairAnswer {
  left: string;
  right: string;
}

export type AnswerResponse = string | string[] | Record<string, string> | MatchingPairAnswer[];

// Phase C (docs/CONTRACT.md): "almost" means a free-text answer was within
// typo tolerance and was ACCEPTED (correct == true, XP awarded) but wasn't
// an exact match - the frontend must surface this distinctly rather than
// rendering a plain "Correct!" that hides the spelling slip. Choice-type
// exercises never produce "almost", only free-text ones.
export type GradingStatus = "correct" | "almost" | "incorrect";

export interface AnswerResult {
  correct: boolean;
  result: GradingStatus;
  correct_response: unknown;
  xp_awarded: number;
  feedback?: string;
}

export interface LessonStartResult {
  started_at: string;
}

export interface LessonCompleteResult {
  completed_at: string;
  xp_awarded: number;
  accuracy: number;
}

export interface ReviewItem {
  id: string;
  exercise_id: string;
  due_at: string;
  mastery: number;
  exercise: Pick<Exercise, "id" | "type" | "prompt">;
}

export interface ReviewsPage {
  items: ReviewItem[];
  next_cursor: string | null;
}

export interface ReviewAnswerResult extends AnswerResult {
  next_due_at: string;
}

export interface LessonProgress {
  lesson_id: string;
  started_at: string | null;
  completed_at: string | null;
  accuracy: number | null;
  xp_earned: number | null;
}

export interface Progress {
  lessons_started: number;
  lessons_completed: number;
  lesson_progress: LessonProgress[];
  skill_progress: { course_id: string; completed_lessons: number; mastery: number }[];
  vocabulary_progress: { content_item_id: string; mastery: number }[];
  grammar_progress: { content_item_id: string; mastery: number }[];
}

export interface Streak {
  streak_days: number;
  last_activity_date: string | null;
  streak_freezes_available: number;
  freeze_used_today: boolean;
  /** Server-computed "streak-preserving activity has happened today", in the
   *  account's own timezone day boundary — use this, never re-derive it from
   *  last_activity_date against the device clock (see docs/CONTRACT.md). */
  active_today: boolean;
}

// "conversation" is a practice-feed-only, multi-turn item (mode=conversation):
// its prompt carries a node graph, not an ExercisePrompt, and it is rendered by
// ConversationRunner, NOT by ExerciseRenderer. It is deliberately kept OUT of
// ExerciseType so the exhaustive exercise-type registration check keeps working.
export type PracticeItemType = ExerciseType | "conversation";

export interface PracticeItem {
  id: string;
  type: PracticeItemType;
  prompt: ExercisePrompt;
}

// Review, checkpoint and lesson runners share PracticeItem but can never
// receive a conversation item (only the practice feed's mode=conversation
// emits them). This narrows for those callers and fails loudly rather than
// silently rendering a broken card if that assumption is ever violated.
export function asExerciseType(type: PracticeItemType): ExerciseType {
  if (type === "conversation") {
    throw new Error("conversation items are only renderable by ConversationRunner");
  }
  return type;
}

// Server default is "mixed"; "speaking" and "conversation" are additive
// filters (see docs/CONTRACT.md, POST /practice/{course_id}/batch).
export type PracticeBatchMode = "mixed" | "speaking" | "conversation";

export interface PracticeBatchResult {
  locked: boolean;
  items: PracticeItem[];
}

export interface PracticeAnswerResult {
  correct: boolean;
  result: GradingStatus;
  correct_response: unknown;
  xp_awarded: number;
}

export interface ReviewDueCourse {
  course_id: string;
  due_count: number;
}

export interface ReviewDueResult {
  due_count: number;
  by_course: ReviewDueCourse[];
}

export interface ReviewItemsResult {
  items: PracticeItem[];
}

export type LexemeSort =
  | "due_soonest"
  | "mastery_asc"
  | "mastery_desc"
  | "alphabetical"
  | "recently_introduced";

export interface Lexeme {
  token: string;
  english_gloss: string;
  part_of_speech: string;
  mastery: number;
  interval_days: number;
  repetitions: number;
  due_at: string;
  introduced_at: string;
  suspended: boolean;
  last_reviewed_at: string | null;
}

export interface LexemeListResult {
  items: Lexeme[];
  total_count: number;
  limit: number;
  offset: number;
}

export interface LexemeMasteryBands {
  new: number;
  learning: number;
  strong: number;
}

export interface LexemeSummary {
  total_tracked: number;
  mastery_bands: LexemeMasteryBands;
  due_today: number;
  suspended: number;
}

export interface MistakeLexeme {
  token: string;
  english_gloss: string;
  part_of_speech: string;
  mastery: number;
  repetitions: number;
  recent_accuracy: number;
  wrong_attempt_count: number;
  total_attempt_count: number;
}

export interface MistakeLexemeListResult {
  items: MistakeLexeme[];
  total_count: number;
  limit: number;
  offset: number;
}

export interface CheckpointResult {
  status: "in_progress" | "complete";
  answered_items: number;
  total_items: number;
  passed: boolean | null;
  score: number | null;
  weak_outcomes: string[];
  checkpoint_passed: boolean;
}

export interface Xp {
  total_xp: number;
  daily_goal: number;
  // XP earned within the user's own local day (server-computed from the
  // persisted per-answer rows in the user's timezone) — the value the
  // daily_goal progress indicator measures against.
  xp_today: number;
}

export interface Achievement {
  id: string;
  code: string;
  title: string;
  description: string;
  earned: boolean;
}

// Server-authoritative daily nudge quests (Phase E3) — progress is
// computed live against existing state on every GET, and XP is only
// ever awarded once per quest per day server-side, so polling this
// endpoint (e.g. on every Home load) is always safe and never
// double-pays.
export interface Quest {
  code: string;
  title: string;
  description: string;
  xp_reward: number;
  completed: boolean;
  progress: number;
  target: number;
}

export interface QuestsResult {
  quests: Quest[];
}

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  // Optional (not `boolean`) because a session stored in localStorage before
  // this field shipped won't have it -- treat anything other than `true` as
  // non-admin. UX gating only: the backend's admin_user dependency is the
  // actual security boundary for every /admin/* route.
  is_admin?: boolean;
  created_at?: string;
}

export interface AuthResult {
  access_token: string;
  // Opaque, DB-backed, 60-day, rotates on every /auth/refresh use — see
  // docs/CONTRACT.md's Auth section.
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
}

export interface ApiErrorBody {
  error: { code: string; message: string; [key: string]: unknown };
}

export type TtsFallbackReason = "unsupported_language" | "quota_exceeded" | "provider_error";

export interface TtsFallback {
  use_browser_tts: true;
  reason: TtsFallbackReason;
}

export type ContentIssueCategory =
  | "wrong_answer_key"
  | "mistranslation"
  | "untaught_vocabulary"
  | "audio_issue"
  | "unclear_instruction"
  | "app_bug"
  | "general_feedback"
  | "other";

export interface ContentIssueReportResult {
  id: string;
  status: string;
}

export interface ContentIssue {
  id: string;
  // At most one of exercise_id/practice_item_id is set: exercise_id for
  // compiled lesson content, practice_item_id for review/checkpoint/
  // Endless Practice generated items (backed by PracticeItem, not
  // Exercise). A page-level report (POST /feedback) has neither set and
  // page_path set instead.
  exercise_id: string | null;
  practice_item_id: string | null;
  page_path: string | null;
  category: ContentIssueCategory;
  description: string | null;
  // The learner's actual submitted answer, captured at report time.
  // Arbitrary shape by exercise type (same caveats as correct_response
  // everywhere else) -- render via formatCorrectResponse(), never
  // String().
  learner_response: unknown;
  status: string;
  triage_notes: string | null;
  duplicate_of_id: string | null;
  created_at: string;
  triaged_at: string | null;
  resolved_at: string | null;
  // Triage enrichment, computed by GET /admin/content/issues only (all
  // four are null on PATCH responses and on page-level feedback rows) --
  // see docs/CONTRACT.md "Issue-triage enrichment", 2026-07-10.
  exercise_prompt: ExercisePrompt | null;
  exercise_correct_response: unknown;
  practice_item_prompt: ExercisePrompt | null;
  // Open reports pointing at the same exercise_id (whole table, not just
  // the returned page) -- duplicate spotting. Null unless exercise-backed.
  open_report_count: number | null;
}

export interface FeedbackReportIn {
  category: ContentIssueCategory;
  description?: string;
  page_path: string;
  // Free-form diagnostic blob. The backend (GeneralFeedbackIn in
  // backend/app/schemas/api.py) accepts any JSON object here, bounded to
  // 5000 serialized characters -- callers must truncate large values
  // (stack traces etc.) themselves or the whole report 422s. Used by the
  // automatic crash reporter (frontend/src/lib/crashReporter.ts).
  client_context?: Record<string, unknown>;
  // Opaque keys from POST /feedback/attachments, max 3 -- see
  // docs/CONTRACT.md "Feedback attachments". Unknown/expired keys are
  // silently dropped server-side; the report never fails over a bad key.
  attachment_keys?: string[];
}

// POST /feedback/attachments response -- see docs/CONTRACT.md "Feedback
// attachments". The key is opaque and orphans after ~1hr if never
// claimed by a POST /feedback.
export interface FeedbackAttachmentUploadResult {
  attachment_key: string;
  expires_in_seconds: number;
}

// Web push (Phase E4) — see docs/CONTRACT.md "Web push notifications".
export interface PushVapidKey {
  // Raw base64url VAPID public key, null whenever configured is false.
  public_key: string | null;
  configured: boolean;
}

export interface PushSubscribeIn {
  // The browser PushSubscription's own fields, exactly as
  // subscription.toJSON() produces them.
  endpoint: string;
  keys: { p256dh: string; auth: string };
}

export interface PushSubscribedResult {
  subscribed: boolean;
}

export interface CoverageRow {
  source_language: string;
  target_language: string;
  course_count: number;
  total_unit_count: number;
  total_lesson_count: number;
  open_issue_count: number;
}
