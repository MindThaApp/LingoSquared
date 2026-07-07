// Types mirror /Users/raminazizi/dev/LingoSquared/docs/CONTRACT.md exactly.
// Keep this file in sync with the contract; do not invent fields it doesn't define.

export type ScriptCode = "latin" | "cyrillic" | "han" | "arabic";
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

export interface AnswerResult {
  correct: boolean;
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
}

export interface PracticeItem {
  id: string;
  type: ExerciseType;
  prompt: ExercisePrompt;
}

export interface PracticeBatchResult {
  locked: boolean;
  items: PracticeItem[];
}

export interface PracticeAnswerResult {
  correct: boolean;
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
}

export interface Achievement {
  id: string;
  code: string;
  title: string;
  description: string;
  earned: boolean;
}

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  created_at?: string;
}

export interface AuthResult {
  access_token: string;
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
  | "other";

export interface ContentIssueReportResult {
  id: string;
  status: string;
}

export interface ContentIssue {
  id: string;
  // Exactly one of these is set: exercise_id for compiled lesson content,
  // practice_item_id for review/checkpoint/Endless Practice generated
  // items (backed by PracticeItem, not Exercise).
  exercise_id: string | null;
  practice_item_id: string | null;
  category: ContentIssueCategory;
  description: string | null;
  status: string;
  created_at: string;
  triaged_at: string | null;
  resolved_at: string | null;
}

export interface CoverageRow {
  source_language: string;
  target_language: string;
  course_count: number;
  total_unit_count: number;
  total_lesson_count: number;
  open_issue_count: number;
}
