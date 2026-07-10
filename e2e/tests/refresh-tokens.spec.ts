import { test, expect, type APIRequestContext } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { freshEmail } from "./helpers";

/**
 * Refresh-token flow (backend commit 565f66c, 2026-07-10): short-lived
 * 30-min access token + long-lived rotating refresh token, with
 * reuse-detection that revokes ALL of a user's refresh tokens when a
 * rotated-out token is presented again.
 *
 * These tests exercise the backend API directly via Playwright's request
 * fixture, NOT the browser -- deliberately. The frontend auto-refresh
 * integration (retry-on-401 via the stored refresh token) had not landed
 * in `packages/shared/src/api/client.ts` when this spec was written
 * (verified: zero `refresh_token` references in packages/shared/src or
 * frontend/src), so the browser half is a skipped placeholder below.
 * Once it lands, replace the skip with a real browser test (see the
 * skipped test's comment for the suggested approach).
 *
 * API base URL: `E2E_API_BASE_URL` env var if set, else
 * `VITE_API_BASE_URL` from ../frontend/.env (the same backend the
 * e2e-managed frontend on :5175 talks to), else localhost:8000. Unlike
 * every other spec in this suite the browser never touches these
 * requests, so CORS_ORIGINS doesn't apply here.
 *
 * Rate-limit note (same caveat as e2e/README.md): this file registers 2
 * fresh accounts. On a stack with the default REGISTER_RATE_LIMIT (5/hr/
 * IP) that budget is shared with every other spec in the suite -- run
 * against an isolated stack with the limit raised (see .env.play /
 * .env.rtok pattern) if the whole suite runs together.
 */

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function apiBaseUrl(): string {
  if (process.env.E2E_API_BASE_URL) return process.env.E2E_API_BASE_URL.replace(/\/$/, "");
  try {
    const env = fs.readFileSync(path.resolve(__dirname, "../../frontend/.env"), "utf8");
    const m = env.match(/^VITE_API_BASE_URL=(.+)$/m);
    if (m) return m[1].trim().replace(/\/$/, "");
  } catch {
    // fall through to default
  }
  return "http://localhost:8000";
}

const API = apiBaseUrl();

interface AuthBody {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

async function registerUser(request: APIRequestContext): Promise<AuthBody & { email: string }> {
  const email = freshEmail("refresh-e2e");
  const res = await request.post(`${API}/auth/register`, {
    data: { email, password: "e2e-test-pass-1", display_name: "Refresh E2E" },
  });
  expect(res.status(), await res.text()).toBe(201);
  return { ...(await res.json()), email };
}

async function whoAmI(request: APIRequestContext, accessToken: string) {
  return request.get(`${API}/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

test.beforeAll(async ({ request }) => {
  // Fail fast with a real explanation instead of a wall of confusing 404s
  // when the target backend predates the refresh-token feature. The most
  // likely cause on a dev stack is NOT missing code but the documented
  // footgun: the compose bind mount syncs source live, but uvicorn has no
  // --reload, so a container started before commit 565f66c keeps serving
  // the old routes until `docker compose up -d --force-recreate api`
  // (plus `alembic upgrade head` for migration 0021).
  const res = await request.get(`${API}/openapi.json`);
  expect(res.ok(), `Backend at ${API} is not reachable`).toBe(true);
  const paths = Object.keys((await res.json()).paths ?? {});
  expect(
    paths,
    `Backend at ${API} does not serve /v1/auth/refresh -- it is running ` +
      `pre-refresh-token code. If this is a dev stack, force-recreate the ` +
      `api container and run alembic upgrade head (migration 0021).`,
  ).toContain("/v1/auth/refresh");
});

test("register returns access + refresh tokens and both are genuinely usable", async ({ request }) => {
  const auth = await registerUser(request);

  expect(auth.token_type).toBe("bearer");
  // 30-minute access tokens are the entire point of the feature -- a
  // regression back to 24h (86400) would silently defeat it.
  expect(auth.expires_in).toBe(1800);
  expect(auth.access_token).toBeTruthy();
  expect(auth.refresh_token).toBeTruthy();
  expect(auth.refresh_token).not.toBe(auth.access_token);

  // The access token actually authenticates (not just present in the body).
  const me = await whoAmI(request, auth.access_token);
  expect(me.status(), await me.text()).toBe(200);
  expect((await me.json()).email).toBe(auth.email);

  // The refresh token actually refreshes (full usability, not just shape).
  const refreshed = await request.post(`${API}/auth/refresh`, {
    data: { refresh_token: auth.refresh_token },
  });
  expect(refreshed.status(), await refreshed.text()).toBe(200);
});

test("refresh rotates the token pair; reuse of the rotated-out token is rejected and revokes everything", async ({ request }) => {
  const auth = await registerUser(request);

  // --- Rotation: a refresh yields a NEW working access token and a NEW
  // refresh token, both different from the originals.
  const refreshed = await request.post(`${API}/auth/refresh`, {
    data: { refresh_token: auth.refresh_token },
  });
  expect(refreshed.status(), await refreshed.text()).toBe(200);
  const next: AuthBody = await refreshed.json();
  expect(next.expires_in).toBe(1800);
  expect(next.access_token).not.toBe(auth.access_token);
  expect(next.refresh_token).not.toBe(auth.refresh_token);

  const me = await whoAmI(request, next.access_token);
  expect(me.status(), await me.text()).toBe(200);
  expect((await me.json()).email).toBe(auth.email);

  // --- Reuse detection: the ORIGINAL refresh token was rotated out above;
  // presenting it again must be rejected with the dedicated error code.
  const reused = await request.post(`${API}/auth/refresh`, {
    data: { refresh_token: auth.refresh_token },
  });
  expect(reused.status()).toBe(401);
  expect((await reused.json()).error.code).toBe("refresh_token_reused");

  // --- Reuse detection revokes ALL of the user's refresh tokens (a
  // replayed rotated-out token means it may have been stolen, so the
  // whole family is nuked): even the NEWEST refresh token, which was
  // perfectly valid a moment ago, must now be rejected too.
  const afterNuke = await request.post(`${API}/auth/refresh`, {
    data: { refresh_token: next.refresh_token },
  });
  expect(afterNuke.status()).toBe(401);
  expect((await afterNuke.json()).error.code).toBe("refresh_token_reused");

  // Access tokens are stateless JWTs -- reuse-detection revokes refresh
  // tokens only; the still-unexpired access token keeps working until its
  // 30 minutes run out. Assert that so a future change to this contract
  // is a conscious one, not an accident.
  const meAfterNuke = await whoAmI(request, next.access_token);
  expect(meAfterNuke.status()).toBe(200);
});

// Frontend auto-refresh on access-token expiry: NOT YET IMPLEMENTED in the
// web frontend as of 2026-07-10 -- `packages/shared/src/api/client.ts` has
// no refresh_token handling at all (it stores only access_token and
// hard-logs-out on 401). Once the auto-refresh integration lands, replace
// this skip with a browser test: register via the UI, overwrite the stored
// access token with a garbage/expired one (or use a backend hook to issue
// a short-exp token, if one gets added -- none exists today), trigger an
// authenticated fetch, and assert the app silently recovers (stays on the
// page, no redirect to /login) because the client refreshed and retried.
test.skip(
  "app silently refreshes an expired access token and the user stays logged in",
  async () => {
    /* pending frontend auto-refresh integration */
  },
);
