import {
  clearAuthTokens,
  del,
  get,
  getFile,
  getStoredRefreshToken,
  patch,
  post,
  postFeedback,
  postFeedbackFile,
  storeAuthTokens,
} from "./client";
import type {
  Achievement,
  AnswerMeta,
  AnswerResponse,
  AnswerResult,
  AuthResult,
  AuthUser,
  SocialCredential,
  SocialProvider,
  CheckpointResult,
  ContentIssue,
  ContentIssueCategory,
  ContentIssueReportResult,
  CourseDetail,
  CourseSummary,
  CoverageRow,
  FeedbackAttachmentUploadResult,
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
  PlacementAnswerIn,
  PlacementAnswerResult,
  PlacementRecommendation,
  PlacementSet,
  PracticeAnswerResult,
  PracticeBatchMode,
  PracticeBatchResult,
  Progress,
  PushSubscribeIn,
  PushSubscribedResult,
  PushVapidKey,
  QuestsResult,
  ReviewAnswerResult,
  ReviewDueResult,
  ReviewForecast,
  ReviewLeechesResult,
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

function socialBody(credential: SocialCredential) {
  return {
    provider: credential.provider,
    id_token: credential.idToken,
    nonce: credential.nonce,
    display_name: credential.displayName || undefined,
  };
}

export const AuthApi = {
  // register/login persist BOTH halves of the session (short-lived access
  // token + long-lived rotating refresh token) through the platform's
  // injected tokenStorage, so callers only need to handle the user object.
  register: async (email: string, password: string, display_name?: string) => {
    const result = await post<AuthResult>("/auth/register", {
      email,
      password,
      display_name,
      timezone: clientTimezone(),
    });
    storeAuthTokens(result.access_token, result.refresh_token);
    return result;
  },
  login: async (email: string, password: string) => {
    const result = await post<AuthResult>("/auth/login", {
      email,
      password,
      timezone: clientTimezone(),
    });
    storeAuthTokens(result.access_token, result.refresh_token);
    return result;
  },
  // POST /auth/social: sign in (or sign up) with a verified Google/Apple
  // ID token. Same session handling as login.
  social: async (credential: SocialCredential) => {
    const result = await post<AuthResult>("/auth/social", socialBody(credential));
    storeAuthTokens(result.access_token, result.refresh_token);
    return result;
  },
  // POST /auth/social/link: attach a Google/Apple sign-in to the signed-in
  // account. For a guest account this converts it in place, keeping its
  // progress. Returns the updated /auth/me shape.
  // Any account other than a guest must confirm its current password.
  linkSocial: (credential: SocialCredential, currentPassword?: string) =>
    post<AuthUser>("/auth/social/link", {
      ...socialBody(credential),
      current_password: currentPassword || undefined,
    }),
  // POST /auth/social/unlink: remove a linked sign-in. Never removes the
  // last way to sign in; an account with a password must confirm it.
  unlinkSocial: (provider: SocialProvider, currentPassword?: string) =>
    post<AuthUser>("/auth/social/unlink", {
      provider,
      current_password: currentPassword || undefined,
    }),
  // POST /auth/social/nonce: single-use nonce for the next Google/Apple
  // sign-in (see socialSignIn.ts).
  socialNonce: () => post<{ nonce: string; expires_in: number }>("/auth/social/nonce", {}),
  me: () => get<AuthUser>("/auth/me"),
  // Revokes the refresh token server-side (best-effort) and clears both
  // tokens locally. Local clearing happens FIRST, synchronously (before
  // the network call resolves): if the revoke request is slow and the
  // user logs in as someone else meanwhile, clearing afterwards would
  // wipe the NEW session's tokens instead. The captured token is still
  // the one that gets revoked. /auth/logout is unauthenticated
  // server-side and always 204s for a valid-shape request, so an already-
  // expired access token can't break it.
  logout: async () => {
    const refreshToken = getStoredRefreshToken();
    clearAuthTokens();
    if (refreshToken) {
      await post<void>("/auth/logout", { refresh_token: refreshToken });
    }
  },
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

// Typed answers send exactly { response } — input_mode is added ONLY for
// voice-produced answers.
export function answerBody(response: AnswerResponse, meta?: AnswerMeta) {
  return {
    response,
    ...(meta?.inputMode ? { input_mode: meta.inputMode } : {}),
    ...(meta?.selfGrade ? { self_grade: meta.selfGrade } : {}),
    ...(meta?.latencyMs !== undefined ? { latency_ms: Math.round(meta.latencyMs) } : {}),
  };
}

export const LessonApi = {
  get: (lessonId: string) => get<Lesson>(`/lessons/${lessonId}`),
  start: (lessonId: string) =>
    post<LessonStartResult>(`/lessons/${lessonId}/start`),
  answer: (exerciseId: string, response: AnswerResponse, meta?: AnswerMeta) =>
    post<AnswerResult>(`/exercises/${exerciseId}/answer`, answerBody(response, meta)),
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
  answerReview: (reviewItemId: string, response: AnswerResponse, meta?: AnswerMeta) =>
    post<ReviewAnswerResult>(`/reviews/${reviewItemId}/answer`, answerBody(response, meta)),
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
  forecast: () => get<ReviewForecast>("/me/reviews/forecast"),
  leeches: () => get<ReviewLeechesResult>("/me/reviews/leeches"),
  session: (courseId: string, size?: number) =>
    post<ReviewItemsResult>("/reviews/session", {
      course_id: courseId,
      ...(size ? { size } : {}),
    }),
  retry: (itemId: string) =>
    post<ReviewItemsResult>(`/reviews/items/${itemId}/retry`),
  // Review items are answered through the shared practice-item endpoint
  // (same server-held-answer/expiry/single-answer semantics).
  answer: (itemId: string, response: AnswerResponse, meta?: AnswerMeta) =>
    post<PracticeAnswerResult>(`/practice/items/${itemId}/answer`, answerBody(response, meta)),
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
  // File download (CSV spreadsheet, or Anki's 2-column tab-separated
  // text-import format) of the same tracked-vocabulary population as
  // list(). See docs/CONTRACT.md "Vocabulary export".
  exportFile: (courseId: string, format: "csv" | "anki" = "csv") =>
    getFile(
      `/courses/${encodeURIComponent(courseId)}/lexemes/export?format=${format}`,
    ),
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
  answer: (itemId: string, response: AnswerResponse, meta?: AnswerMeta) =>
    post<PracticeAnswerResult>(`/practice/items/${itemId}/answer`, answerBody(response, meta)),
};

// Placement test (docs/CONTRACT.md "Placement test (course-level)") —
// course-wide, side-effect-free in the MVP: /placement/answer grades one
// item live for immediate feedback + client-driven early-exit;
// /placement/result is the authoritative (server-re-graded) recommendation.
// Never call these for progress/XP purposes — use LessonApi/CheckpointApi
// for anything that should actually record an attempt.
export const PlacementApi = {
  start: (courseId: string) => get<PlacementSet>(`/courses/${courseId}/placement`),
  answer: (courseId: string, exerciseId: string, response: AnswerResponse) =>
    post<PlacementAnswerResult>(`/courses/${courseId}/placement/answer`, {
      exercise_id: exerciseId,
      response,
    }),
  result: (courseId: string, answers: PlacementAnswerIn[]) =>
    post<PlacementRecommendation>(`/courses/${courseId}/placement/result`, { answers }),
};

export const PracticeApi = {
  // `options.types` filters the batch to a subset of the six drillable
  // exercise types; `options.targetLexemeIds` seeds a drill of just those
  // lexemes (e.g. the weak outcomes surfaced by a failed checkpoint). Both
  // are optional — existing callers pass neither and behave unchanged.
  batch: (
    courseId: string,
    size?: number,
    mode?: PracticeBatchMode,
    options?: { types?: string[]; targetLexemeIds?: string[] },
  ) => {
    const body: Record<string, unknown> = {};
    if (size) body.size = size;
    if (mode && mode !== "mixed") body.mode = mode;
    if (options?.types?.length) body.types = options.types;
    if (options?.targetLexemeIds?.length) {
      body.target_lexeme_ids = options.targetLexemeIds;
    }
    return post<PracticeBatchResult>(
      `/practice/${courseId}/batch`,
      Object.keys(body).length > 0 ? body : undefined,
    );
  },
  answer: (itemId: string, response: AnswerResponse, meta?: AnswerMeta) =>
    post<PracticeAnswerResult>(`/practice/items/${itemId}/answer`, answerBody(response, meta)),
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
  // See docs/CONTRACT.md "Feedback attachments": image-only, max 5MB,
  // sniffed server-side -- the returned key is orphaned (never appears on
  // any report) unless a following submit() includes it in
  // attachment_keys within ~1hr.
  uploadAttachment: (file: Blob, filename: string) =>
    postFeedbackFile<FeedbackAttachmentUploadResult>("/feedback/attachments", file, filename),
};
