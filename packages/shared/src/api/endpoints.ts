import { del, get, patch, post, postFeedback } from "./client";
import type {
  Achievement,
  AnswerResponse,
  AnswerResult,
  AuthResult,
  AuthUser,
  CheckpointResult,
  ContentIssue,
  ContentIssueCategory,
  ContentIssueReportResult,
  CourseDetail,
  CourseSummary,
  CoverageRow,
  FeedbackReportIn,
  Language,
  LanguagePair,
  Lesson,
  LessonCompleteResult,
  LessonStartResult,
  LessonSummary,
  LexemeListResult,
  LexemeSort,
  LexemeSummary,
  MistakeLexemeListResult,
  PracticeAnswerResult,
  PracticeBatchResult,
  Progress,
  PushSubscribeIn,
  PushSubscribedResult,
  PushVapidKey,
  QuestsResult,
  ReviewAnswerResult,
  ReviewDueResult,
  ReviewItemsResult,
  ReviewsPage,
  Streak,
  UnitSummary,
  Xp,
} from "./types";

function clientTimezone(): string | undefined {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return undefined;
  }
}

export const AuthApi = {
  register: (email: string, password: string, display_name?: string) =>
    post<AuthResult>("/auth/register", {
      email,
      password,
      display_name,
      timezone: clientTimezone(),
    }),
  login: (email: string, password: string) =>
    post<AuthResult>("/auth/login", { email, password, timezone: clientTimezone() }),
  me: () => get<AuthUser>("/auth/me"),
  // GET /me/export — the authenticated account's complete data export
  // (GDPR-style portability, the counterpart to deleteAccount below —
  // export before deleting). One JSON document; full shape in
  // docs/CONTRACT.md. Typed loosely on purpose: callers download/save it
  // verbatim rather than render individual fields.
  exportData: () => get<Record<string, unknown>>("/me/export"),
  // DELETE /me — permanently deletes the authenticated account and all
  // of its data server-side (204 on success). Irreversible; the caller
  // is responsible for the confirmation UX and for clearing the local
  // session afterwards.
  deleteAccount: () => del<void>("/me"),
};

export const CatalogApi = {
  languages: () => get<Language[]>("/languages"),
  languagePairs: () => get<LanguagePair[]>("/language-pairs"),
  courses: (source: string, target: string) =>
    get<CourseSummary[]>(
      `/courses?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`,
    ),
  allCourses: () => get<CourseSummary[]>("/courses"),
  course: (courseId: string) => get<CourseDetail>(`/courses/${courseId}`),
  units: (courseId: string) =>
    get<UnitSummary[]>(`/courses/${courseId}/units`),
  lessons: (unitId: string) =>
    get<LessonSummary[]>(`/units/${unitId}/lessons`),
};

export const LessonApi = {
  get: (lessonId: string) => get<Lesson>(`/lessons/${lessonId}`),
  start: (lessonId: string) =>
    post<LessonStartResult>(`/lessons/${lessonId}/start`),
  answer: (exerciseId: string, response: AnswerResponse) =>
    post<AnswerResult>(`/exercises/${exerciseId}/answer`, { response }),
  complete: (lessonId: string) =>
    post<LessonCompleteResult>(`/lessons/${lessonId}/complete`),
  reportIssue: (
    exerciseId: string,
    category: ContentIssueCategory,
    description?: string,
    learner_response?: AnswerResponse,
  ) =>
    post<ContentIssueReportResult>(`/exercises/${exerciseId}/report`, {
      category,
      description,
      learner_response,
    }),
};

export const ProgressApi = {
  progress: () => get<Progress>("/me/progress"),
  reviews: (cursor?: string) =>
    get<ReviewsPage>(`/me/reviews${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`),
  answerReview: (reviewItemId: string, response: AnswerResponse) =>
    post<ReviewAnswerResult>(`/reviews/${reviewItemId}/answer`, { response }),
  streak: () => get<Streak>("/me/streak"),
  xp: () => get<Xp>("/me/xp"),
  achievements: () => get<Achievement[]>("/me/achievements"),
  // Progress/target are computed live server-side on every call; XP is
  // awarded at most once per quest per day (server-enforced), so this
  // is always safe to poll/refetch.
  quests: () => get<QuestsResult>("/me/quests"),
};

// Lexeme-level SRS review flow (Phase A) — distinct from ProgressApi's
// legacy exercise-keyed reviews above, which stay in place only for any
// pre-existing legacy review rows.
export const ReviewApi = {
  due: () => get<ReviewDueResult>("/me/reviews/due"),
  session: (courseId: string, size?: number) =>
    post<ReviewItemsResult>("/reviews/session", {
      course_id: courseId,
      ...(size ? { size } : {}),
    }),
  retry: (itemId: string) =>
    post<ReviewItemsResult>(`/reviews/items/${itemId}/retry`),
  // Review items are answered through the shared practice-item endpoint
  // (same server-held-answer/expiry/single-answer semantics).
  answer: (itemId: string, response: AnswerResponse) =>
    post<PracticeAnswerResult>(`/practice/items/${itemId}/answer`, { response }),
  // Review items are PracticeItem rows, not Exercise rows - reported
  // through the shared practice-item report endpoint, not
  // /exercises/{id}/report (which 404s for a PracticeItem id).
  reportIssue: (
    itemId: string,
    category: ContentIssueCategory,
    description?: string,
    learnerResponse?: AnswerResponse,
  ) =>
    post<ContentIssueReportResult>(`/practice/items/${itemId}/report`, {
      category,
      description,
      learner_response: learnerResponse,
    }),
};

// Vocabulary browser + mistakes hub -- read-only views over the same
// per-lexeme SRS state the review/practice engines already maintain.
export const LexemeApi = {
  list: (
    courseId: string,
    opts?: {
      sort?: LexemeSort;
      partOfSpeech?: string;
      search?: string;
      limit?: number;
      offset?: number;
    },
  ) => {
    const params = new URLSearchParams({ course_id: courseId });
    if (opts?.sort) params.set("sort", opts.sort);
    if (opts?.partOfSpeech) params.set("part_of_speech", opts.partOfSpeech);
    if (opts?.search) params.set("search", opts.search);
    if (opts?.limit !== undefined) params.set("limit", String(opts.limit));
    if (opts?.offset !== undefined) params.set("offset", String(opts.offset));
    return get<LexemeListResult>(`/me/lexemes?${params.toString()}`);
  },
  summary: (courseId: string) =>
    get<LexemeSummary>(`/me/lexemes/summary?course_id=${encodeURIComponent(courseId)}`),
  mistakes: (courseId: string, opts?: { limit?: number; offset?: number }) => {
    const params = new URLSearchParams({ course_id: courseId });
    if (opts?.limit !== undefined) params.set("limit", String(opts.limit));
    if (opts?.offset !== undefined) params.set("offset", String(opts.offset));
    return get<MistakeLexemeListResult>(`/me/mistakes?${params.toString()}`);
  },
};

export const CheckpointApi = {
  start: (unitId: string, size?: number) =>
    post<ReviewItemsResult>(
      `/units/${unitId}/checkpoint`,
      size ? { size } : undefined,
    ),
  result: (unitId: string) =>
    get<CheckpointResult>(`/units/${unitId}/checkpoint/result`),
  // Checkpoint items are answered through the same shared practice-item
  // endpoint as review/practice items.
  answer: (itemId: string, response: AnswerResponse) =>
    post<PracticeAnswerResult>(`/practice/items/${itemId}/answer`, { response }),
};

export const PracticeApi = {
  batch: (courseId: string, size?: number) =>
    post<PracticeBatchResult>(
      `/practice/${courseId}/batch`,
      size ? { size } : undefined,
    ),
  answer: (itemId: string, response: AnswerResponse) =>
    post<PracticeAnswerResult>(`/practice/items/${itemId}/answer`, { response }),
  // Endless Practice items are PracticeItem rows, not Exercise rows -
  // reported through the shared practice-item report endpoint.
  reportIssue: (
    itemId: string,
    category: ContentIssueCategory,
    description?: string,
    learnerResponse?: AnswerResponse,
  ) =>
    post<ContentIssueReportResult>(`/practice/items/${itemId}/report`, {
      category,
      description,
      learner_response: learnerResponse,
    }),
};

// Web push (Phase E4) — see docs/CONTRACT.md "Web push notifications".
// vapidPublicKey is the unauthenticated capability probe: configured:false
// means the server has no VAPID keys and ALL push UI must stay hidden
// (graceful no-op, never a broken button).
export const PushApi = {
  vapidPublicKey: () => get<PushVapidKey>("/push/vapid-public-key"),
  subscribe: (subscription: PushSubscribeIn) =>
    post<PushSubscribedResult>("/push/subscribe", subscription),
  // Idempotent server-side; safe to call with an endpoint the server has
  // never seen (e.g. cleaning up after a failed subscribe).
  unsubscribe: (endpoint: string) =>
    post<PushSubscribedResult>("/push/unsubscribe", { endpoint }),
};

export const AdminApi = {
  coverage: () => get<CoverageRow[]>("/admin/content/coverage"),
  issues: (status?: string) =>
    get<ContentIssue[]>(`/admin/content/issues${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  updateIssue: (
    issueId: string,
    body: { status?: string; triage_notes?: string; duplicate_of_id?: string },
  ) =>
    patch<ContentIssue>(`/admin/content/issues/${issueId}`, body),
};

// Unauthenticated, works on any page (including logged-out screens) and
// deliberately targets its own configurable base URL -- see
// postFeedback()/FEEDBACK_BASE_URL in client.ts.
export const FeedbackApi = {
  submit: (body: FeedbackReportIn) => postFeedback<ContentIssueReportResult>("/feedback", body),
};
