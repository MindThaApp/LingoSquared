import { test, expect, type APIRequestContext } from "@playwright/test";
import { freshEmail } from "./helpers";

/**
 * API-level smoke tests (no browser): FSRS review scheduling and password change.
 * Same base-URL convention as refresh-tokens.spec.ts (E2E_API_BASE_URL, set by scripts/e2e.sh).
 */
const API = (process.env.E2E_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
const PASSWORD = "e2e-smoke-pass-1";

interface AuthBody {
  access_token: string;
  refresh_token: string;
}

async function register(request: APIRequestContext, prefix: string): Promise<AuthBody & { email: string }> {
  const email = freshEmail(prefix);
  const res = await request.post(`${API}/auth/register`, { data: { email, password: PASSWORD, display_name: "Smoke" } });
  expect(res.status(), await res.text()).toBe(201);
  return { ...(await res.json()), email };
}

const bearer = (token: string) => ({ Authorization: `Bearer ${token}` });

async function withDb<T>(fn: (c: import("pg").Client) => Promise<T>): Promise<T> {
  const { default: pg } = await import("pg");
  const client = new pg.Client({ connectionString: process.env.E2E_DATABASE_URL ?? "postgresql://ls:e2e-local@db:5432/ls" });
  await client.connect();
  try {
    return await fn(client);
  } finally {
    await client.end();
  }
}

test("FSRS: a completed review sets stability and difficulty and schedules a future due date", async ({ request }) => {
  const user = await register(request, "e2e-fsrs");

  // Miss one seeded typed exercise: that creates the review item and reveals the right answer.
  const exerciseId = await withDb(async (c) => {
    const r = await c.query(
      `SELECT e.id FROM exercises e JOIN lessons l ON l.id = e.lesson_id JOIN units u ON u.id = l.unit_id
       JOIN courses co ON co.id = u.course_id
       WHERE co.title = 'Farsi Foundations' AND e.type = 'translation' AND jsonb_typeof(e.correct_response::jsonb) = 'string'
       ORDER BY e.id LIMIT 1`,
    );
    return r.rows[0]?.id as string;
  });
  expect(exerciseId, "seeded Farsi Foundations translation exercise").toBeTruthy();
  const miss = await request.post(`${API}/exercises/${exerciseId}/answer`, {
    headers: bearer(user.access_token),
    data: { response: "definitely-wrong" },
  });
  expect(miss.status(), await miss.text()).toBe(200);
  const missed = await miss.json();
  expect(missed.correct).toBe(false);

  const reviewId = await withDb(async (c) => {
    const r = await c.query(
      "SELECT id FROM review_items WHERE user_id = (SELECT id FROM users WHERE email = $1) AND exercise_id = $2",
      [user.email, exerciseId],
    );
    return r.rows[0]?.id as string;
  });
  expect(reviewId, "a miss creates a review item").toBeTruthy();
  await withDb((c) => c.query("UPDATE review_items SET due_at = now() - interval '1 hour' WHERE id = $1", [reviewId]));

  const before = Date.now();
  const done = await request.post(`${API}/reviews/${reviewId}/answer`, {
    headers: bearer(user.access_token),
    data: { response: missed.correct_response },
  });
  expect(done.status(), await done.text()).toBe(200);
  const body = await done.json();
  expect(body.correct).toBe(true);
  expect(new Date(body.next_due_at).getTime()).toBeGreaterThan(before);

  const row = await withDb(async (c) => (await c.query("SELECT stability, difficulty, due_at FROM review_items WHERE id = $1", [reviewId])).rows[0]);
  expect(row.stability).toBeGreaterThan(0);
  expect(row.difficulty).toBeGreaterThanOrEqual(1);
  expect(row.difficulty).toBeLessThanOrEqual(10);
  expect(new Date(row.due_at).getTime()).toBeGreaterThan(before);
  expect(new Date(row.due_at).getTime()).toBe(new Date(body.next_due_at).getTime());
});

test("password change: wrong/unchanged rejected, old password fails, new works, other sessions' refresh tokens revoked", async ({ request }) => {
  const a = await register(request, "e2e-pwapi");
  const NEW_PASSWORD = "e2e-smoke-new-pass-2";

  // A second session (another device).
  const loginB = await request.post(`${API}/auth/login`, { data: { email: a.email, password: PASSWORD } });
  expect(loginB.status(), await loginB.text()).toBe(200);
  const b: AuthBody = await loginB.json();

  const change = (current: string, next: string) =>
    request.post(`${API}/auth/password`, { headers: bearer(a.access_token), data: { current_password: current, new_password: next } });

  const wrong = await change("not-the-password", NEW_PASSWORD);
  expect(wrong.status()).toBe(403);
  expect((await wrong.json()).error?.code ?? (await wrong.text())).toContain("invalid_current_password");
  expect((await change(PASSWORD, PASSWORD)).status()).toBe(400);

  const ok = await change(PASSWORD, NEW_PASSWORD);
  expect(ok.status(), await ok.text()).toBe(200);
  const fresh: AuthBody = await ok.json();

  // Old password fails, new one works.
  const oldLogin = await request.post(`${API}/auth/login`, { data: { email: a.email, password: PASSWORD } });
  expect(oldLogin.status()).toBe(401);
  const newLogin = await request.post(`${API}/auth/login`, { data: { email: a.email, password: NEW_PASSWORD } });
  expect(newLogin.status()).toBe(200);

  // The session returned by the change keeps working (checked first: presenting a revoked token
  // trips reuse detection, which revokes the whole family).
  const kept = await request.post(`${API}/auth/refresh`, { data: { refresh_token: fresh.refresh_token } });
  expect(kept.status(), await kept.text()).toBe(200);
  // Every pre-change refresh token (this session's and the other device's) is revoked.
  for (const stale of [a.refresh_token, b.refresh_token]) {
    const r = await request.post(`${API}/auth/refresh`, { data: { refresh_token: stale } });
    expect(r.status()).toBe(401);
  }
  // Current behaviour: already-issued access tokens stay valid until they expire (stateless JWT).
  expect((await request.get(`${API}/auth/me`, { headers: bearer(b.access_token) })).status()).toBe(200);
});
