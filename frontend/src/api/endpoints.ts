import { get, patch, post } from "./client";
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
  Language,
  LanguagePair,
  Lesson,
  LessonCompleteResult,
  LessonStartResult,
  LessonSummary,
  PracticeAnswerResult,
  PracticeBatchResult,
  Progress,
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
};

export const CatalogApi = {
  languages: () => get<Language[]>("/languages"),
  languagePairs: () => get<LanguagePair[]>("/language-pairs"),
  courses: (source: string, target: string) =>
    get<CourseSummary[]>(
      `/courses?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`,
    ),
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

export const AdminApi = {
  coverage: () => get<CoverageRow[]>("/admin/content/coverage"),
  issues: (status?: string) =>
    get<ContentIssue[]>(`/admin/content/issues${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  updateIssue: (issueId: string, body: { status?: string; triage_notes?: string }) =>
    patch<ContentIssue>(`/admin/content/issues/${issueId}`, body),
};
