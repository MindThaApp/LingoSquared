import type { Page, Request, Route } from "@playwright/test";

/**
 * Fully route-mocked backend for self-contained specs (no Docker, no seeded
 * DB, no registration rate limit). Every request the SPA sends to a
 * different origin than the page itself (i.e. the API at VITE_API_BASE_URL,
 * whatever host/port that resolves to) is intercepted by ONE page.route and
 * dispatched to the handlers registered with `api.on(...)`. Anything
 * unhandled is answered with a 404 in the app's own error envelope
 * (`{"error": {code, message}}`) and recorded in `api.unmocked`, so a spec
 * can print / assert on what it forgot to mock.
 *
 * Shapes below mirror packages/shared/src/api/types.ts (which mirrors
 * docs/CONTRACT.md) -- keep them in sync when the contract changes.
 */

export interface MockRequest {
  method: string;
  path: string;
  query: URLSearchParams;
  params: Record<string, string>;
  body: unknown;
  request: Request;
}

export interface MockReply {
  status: number;
  body?: unknown;
}

type Handler = (req: MockRequest) => unknown;

interface Registered {
  method: string;
  pattern: RegExp;
  keys: string[];
  handler: Handler;
}

/** Wrap a non-200 (or empty-body) response; a plain return value is sent as 200 JSON. */
export function reply(status: number, body?: unknown): MockReply & { __reply: true } {
  return { status, body, __reply: true };
}

function isReply(v: unknown): v is MockReply & { __reply: true } {
  return typeof v === "object" && v !== null && (v as { __reply?: unknown }).__reply === true;
}

function compile(path: string): { pattern: RegExp; keys: string[] } {
  const keys: string[] = [];
  const source = path
    .split("/")
    .map((seg) => {
      if (seg.startsWith(":")) {
        keys.push(seg.slice(1));
        return "([^/]+)";
      }
      return seg.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    })
    .join("/");
  return { pattern: new RegExp(`^${source}$`), keys };
}

export class MockApi {
  private handlers: Registered[] = [];
  /** Every intercepted API call, in order. */
  readonly calls: { method: string; path: string; body: unknown }[] = [];
  /** API calls no handler matched ("METHOD /path?query"). */
  readonly unmocked: string[] = [];
  /** Bodies POSTed to /feedback (the app's automatic crash reporter). */
  readonly crashReports: unknown[] = [];

  /** Later registrations win over earlier ones for the same method+path. */
  on(method: string, path: string, handler: Handler): this {
    const { pattern, keys } = compile(path);
    this.handlers.unshift({ method: method.toUpperCase(), pattern, keys, handler });
    return this;
  }

  /** `appBaseURL` is the SPA's own origin (the `baseURL` fixture); everything else is API. */
  async install(page: Page, appBaseURL: string): Promise<void> {
    const appOrigin = new URL(appBaseURL).origin;
    await page.route(
      (url) => url.origin !== appOrigin && /^https?:$/.test(url.protocol),
      (route) => this.dispatch(route),
    );
  }

  private async dispatch(route: Route): Promise<void> {
    const request = route.request();
    const type = request.resourceType();
    if (type !== "fetch" && type !== "xhr") {
      // Not an API call (e.g. a third-party asset): never let it hit the network.
      await route.abort();
      return;
    }
    const method = request.method().toUpperCase();
    const url = new URL(request.url());
    if (method === "OPTIONS") {
      await route.fulfill({ status: 204, headers: corsHeaders() });
      return;
    }
    let body: unknown = undefined;
    const raw = request.postData();
    if (raw) {
      try {
        body = JSON.parse(raw);
      } catch {
        body = raw;
      }
    }
    this.calls.push({ method, path: url.pathname, body });
    if (method === "POST" && url.pathname === "/feedback") this.crashReports.push(body);

    for (const h of this.handlers) {
      if (h.method !== method) continue;
      const m = h.pattern.exec(url.pathname);
      if (!m) continue;
      const params: Record<string, string> = {};
      h.keys.forEach((k, i) => (params[k] = decodeURIComponent(m[i + 1])));
      const out = h.handler({ method, path: url.pathname, query: url.searchParams, params, body, request });
      const status = isReply(out) ? out.status : 200;
      const payload = isReply(out) ? out.body : out;
      await route.fulfill({
        status,
        headers: { ...corsHeaders(), "content-type": "application/json" },
        body: payload === undefined ? "" : JSON.stringify(payload),
      });
      return;
    }

    const key = `${method} ${url.pathname}${url.search}`;
    this.unmocked.push(key);
    console.log(`[mock-api] UNMOCKED ${key}`);
    await route.fulfill({
      status: 404,
      headers: { ...corsHeaders(), "content-type": "application/json" },
      body: JSON.stringify({ error: { code: "not_mocked", message: `e2e mock: no handler for ${key}` } }),
    });
  }
}

function corsHeaders(): Record<string, string> {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-headers": "*",
    "access-control-allow-methods": "GET,POST,PATCH,DELETE,OPTIONS",
  };
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

export const USER = {
  id: "00000000-0000-4000-8000-00000000e2e0",
  email: "e2e-mock@example.com",
  display_name: "Mocky",
  is_admin: false,
  created_at: "2026-09-01T00:00:00Z",
};

export const COURSE = {
  id: "course-nl-a1",
  source_language: "en",
  target_language: "nl",
  title: "Dutch Foundations",
  level: "A1" as const,
  unit_count: 3,
};

export interface UnitFixture {
  id: string;
  title: string;
  order: number;
  lesson_count: number;
  completed_lesson_count: number;
  section: "reading_writing" | "speaking";
  locked: boolean;
  checkpoint_passed: boolean;
  content_key: string | null;
  track?: "core" | "situation";
}

export function unit(overrides: Partial<UnitFixture> & Pick<UnitFixture, "id" | "title" | "order">): UnitFixture {
  return {
    lesson_count: 1,
    completed_lesson_count: 0,
    section: "reading_writing",
    locked: false,
    checkpoint_passed: false,
    content_key: null,
    ...overrides,
  };
}

export interface LessonFixture {
  id: string;
  unit_id: string;
  title: string;
  teaching: unknown[];
  exercises: {
    id: string;
    type: string;
    order: number;
    prompt: Record<string, unknown> & { text_blocks: { text: string; language_code: string; direction: "ltr" | "rtl" }[] };
  }[];
}

export function enBlock(text: string) {
  return { text, language_code: "en", direction: "ltr" as const };
}

/**
 * Registers baseline handlers for every endpoint the shell, Home, the
 * course map, the unit page, the lesson runner and the completion page
 * call, with a brand-new-ish user (no reviews due, nothing in progress).
 * Specs then override individual endpoints with `api.on(...)`.
 */
export function baseline(api: MockApi, opts: { units: UnitFixture[]; lessons?: LessonFixture[] }): MockApi {
  const lessons = opts.lessons ?? [];
  api
    .on("GET", "/auth/me", () => USER)
    .on("POST", "/auth/logout", () => reply(204))
    .on("GET", "/languages", () => [
      { code: "en", name: "English", native_name: "English", script: "latin", direction: "ltr" },
      { code: "nl", name: "Dutch", native_name: "Nederlands", script: "latin", direction: "ltr" },
    ])
    .on("GET", "/language-pairs", () => [{ source_language: "en", target_language: "nl", course_count: 1 }])
    .on("GET", "/courses", () => [COURSE])
    .on("GET", "/courses/:id", ({ params }) =>
      params.id === COURSE.id
        ? { ...COURSE, unit_count: opts.units.length, description: "Everyday Dutch from zero." }
        : reply(404, { error: { code: "not_found", message: "Course not found" } }),
    )
    .on("GET", "/courses/:id/units", () => opts.units)
    .on("GET", "/units/:id/lessons", ({ params }) =>
      lessons
        .filter((l) => l.unit_id === params.id)
        .map((l, i) => ({ id: l.id, title: l.title, order: i + 1, exercise_count: l.exercises.length })),
    )
    .on("GET", "/lessons/:id", ({ params }) => {
      const l = lessons.find((x) => x.id === params.id);
      return l ?? reply(404, { error: { code: "not_found", message: "Lesson not found" } });
    })
    .on("POST", "/lessons/:id/start", () => ({ started_at: "2026-09-29T10:00:00Z" }))
    .on("POST", "/lessons/:id/complete", () => ({
      completed_at: "2026-09-29T10:05:00Z",
      xp_awarded: 10,
      accuracy: 1,
    }))
    .on("GET", "/me/progress", () => ({
      lessons_started: 0,
      lessons_completed: 0,
      lesson_progress: [],
      skill_progress: [{ course_id: COURSE.id, completed_lessons: 0, mastery: 0 }],
      vocabulary_progress: [],
      grammar_progress: [],
    }))
    .on("GET", "/me/streak", () => ({
      streak_days: 0,
      last_activity_date: null,
      streak_freezes_available: 0,
      freeze_used_today: false,
      active_today: false,
    }))
    .on("GET", "/me/xp", () => ({ total_xp: 0, daily_goal: 20, xp_today: 0 }))
    .on("GET", "/me/achievements", () => [])
    .on("GET", "/me/quests", () => ({ quests: [] }))
    .on("GET", "/me/reviews/due", () => ({ due_count: 0, by_course: [] }))
    .on("GET", "/push/vapid-public-key", () => ({ public_key: null, configured: false }))
    .on("POST", "/feedback", () => ({ id: "fb-1", status: "open" }));
  return api;
}

/**
 * Seeds a logged-in session before any app script runs: the SPA reads
 * `access_token` / `refresh_token` from localStorage (frontend/src/main.tsx
 * tokenStorage) and then verifies it with GET /auth/me (mocked above).
 * `extra` lets a spec seed other per-device preferences (e.g. the active
 * course or the self-reported level used for the "Recommended" badge).
 * Only written when absent, so the app's own writes survive in-test
 * navigations.
 */
export async function seedSession(page: Page, extra: Record<string, string> = {}): Promise<void> {
  const entries = {
    access_token: "e2e-access-token",
    refresh_token: "e2e-refresh-token",
    user: JSON.stringify(USER),
    ...extra,
  };
  await page.addInitScript((kv: Record<string, string>) => {
    for (const [k, v] of Object.entries(kv)) {
      if (window.localStorage.getItem(k) === null) window.localStorage.setItem(k, v);
    }
  }, entries);
}

/** Sets up mocks + session in one go and returns the MockApi for overrides. */
export async function mockedApp(
  page: Page,
  appBaseURL: string | undefined,
  opts: { units: UnitFixture[]; lessons?: LessonFixture[]; storage?: Record<string, string> },
): Promise<MockApi> {
  const api = baseline(new MockApi(), opts);
  await api.install(page, appBaseURL ?? "http://localhost:5175");
  await seedSession(page, opts.storage);
  return api;
}

/** localStorage key the app uses for the learner's active course (lib/activeCourse.ts). */
export const ACTIVE_COURSE_KEY = `lingo.activeCourse.${USER.id}`;

/**
 * Course map -> unit -> lesson through the real UI, so the runner receives
 * `location.state.courseId` exactly as in production (the runner resolves
 * the course's CEFR level -- which gates the A1/A2 word bank -- from it; a
 * deep link to /lessons/:id has no courseId and would silently fall back to
 * typed input).
 */
export async function openLessonViaCourseMap(page: Page, unitTitle: string, lessonTitle: string): Promise<void> {
  await page.goto(`/courses/${COURSE.id}`);
  await page.getByRole("button", { name: unitTitle, exact: true }).click();
  await page.waitForURL(/\/units\/[^/]+$/);
  await page.getByRole("link", { name: new RegExp(lessonTitle) }).click();
  await page.waitForURL(/\/lessons\/[^/]+$/);
}
