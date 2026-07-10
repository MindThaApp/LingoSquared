import { test, expect, type APIRequestContext } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { freshEmail, registerAndLand } from "./helpers";

/**
 * Refresh-token flow (backend commit 565f66c, 2026-07-10): short-lived
 * 30-min access token + long-lived rotating refresh token, with
 * reuse-detection that revokes ALL of a user's refresh tokens when a
 * rotated-out token is presented again.
 *
 * The first two tests exercise the backend API directly via Playwright's
 * request fixture, NOT the browser -- deliberately, to isolate rotation/
 * reuse-detection semantics from any frontend behavior. The last test
 * below DOES drive a real browser: the frontend auto-refresh integration
 * (retry-on-401 via the stored refresh token, `packages/shared/src/api/
 * client.ts`'s `apiFetch`/`refreshSession`) landed 2026-07-10, so it's a
 * real test now, not a skipped placeholder.
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

// Frontend auto-refresh on access-token expiry (drives a real browser, not
// the request fixture -- the whole point is exercising AuthContext's mount
// effect -> AuthApi.me() -> apiFetch's 401 -> silent refresh + retry path
// exactly as a real user would hit it after 30 minutes idle).
//
// Rather than waiting out the real 30-minute access-token lifetime (or
// standing up a separate short-expiry backend stack just for this one
// test -- overkill for a suite that otherwise runs against whatever
// backend is already up), this test forges the "expired access token"
// condition directly: register normally (real access + refresh tokens,
// both genuinely valid), then overwrite ONLY the stored access token with
// a garbage value via localStorage, leaving the real refresh token
// in place. From the client's point of view this is indistinguishable
// from a genuinely expired access token -- the next authenticated request
// 401s, and apiFetch/refreshSession must silently recover using the
// still-valid refresh token.
test("app silently refreshes an expired access token and the user stays logged in", async ({ page }) => {
  const email = freshEmail("refresh-e2e-browser");
  await registerAndLand(page, email);

  const refreshTokenBefore = await page.evaluate(() => localStorage.getItem("refresh_token"));
  expect(refreshTokenBefore, "register must store a refresh token via the tokenStorage seam").toBeTruthy();

  // Forge access-token expiry; the real refresh token is left untouched.
  await page.evaluate(() => {
    localStorage.setItem("access_token", "garbage.expired.token");
  });

  // Reload re-runs AuthContext's mount effect, which calls AuthApi.me()
  // with the now-garbage access token -> 401 -> apiFetch's silent
  // refresh-and-retry. If that path is broken, ProtectedRoute redirects
  // to /login instead of staying on "/".
  await page.reload();
  await page.waitForURL("/", { timeout: 10000 });
  // A real authenticated page element, not just the URL -- confirms the
  // app is actually rendered as logged-in, not mid-redirect.
  await page.getByRole("link", { name: "Learn" }).first().waitFor({ state: "visible" });

  // The token pair must have been rotated in storage: a fresh access
  // token (not the garbage value) and a fresh, different refresh token
  // (server-side rotation-on-use, mirrored client-side).
  const accessTokenAfter = await page.evaluate(() => localStorage.getItem("access_token"));
  const refreshTokenAfter = await page.evaluate(() => localStorage.getItem("refresh_token"));
  expect(accessTokenAfter).toBeTruthy();
  expect(accessTokenAfter).not.toBe("garbage.expired.token");
  expect(refreshTokenAfter).toBeTruthy();
  expect(refreshTokenAfter).not.toBe(refreshTokenBefore);

  // The pre-refresh refresh token was rotated out server-side; presenting
  // it again must now be rejected as reuse -- confirms the client didn't
  // just fabricate local values but genuinely completed a real rotation
  // against the backend.
  const reused = await page.request.post(`${API}/auth/refresh`, {
    data: { refresh_token: refreshTokenBefore },
  });
  expect(reused.status()).toBe(401);
});

// Logout (ProfilePage's "Log out" button -> AuthContext.logout() ->
// AuthApi.logout()) must revoke the refresh token server-side, not just
// clear it locally -- otherwise a stolen/leaked refresh token captured
// before logout would keep working indefinitely.
test("logging out via the UI revokes the refresh token server-side", async ({ page }) => {
  const email = freshEmail("refresh-e2e-logout");
  await registerAndLand(page, email);

  await page.getByRole("link", { name: "Profile" }).first().click();
  await page.waitForURL(/\/profile$/);

  // Read the refresh token as late as possible, immediately before
  // clicking Log out -- NOT right after registration. AuthApi.logout()
  // revokes whatever refresh token is CURRENTLY stored, and background
  // authenticated requests (streak/xp/quests polling on HomePage, etc.)
  // can legitimately have already rotated the original one via the
  // silent-refresh path by the time the user reaches this page (this
  // stack's ACCESS_TOKEN_EXPIRE_SECONDS=8 makes that easy to hit) --
  // asserting against a stale, already-superseded token would be
  // asserting the wrong thing, not exercising a real bug.
  const refreshToken = await page.evaluate(() => localStorage.getItem("refresh_token"));
  expect(refreshToken).toBeTruthy();

  // AuthContext.logout() clears local state and redirects synchronously,
  // firing the actual revoking POST /auth/logout in the background (see
  // AuthApi.logout()'s own comment: local-first, so a slow/failed revoke
  // call never leaves the user stuck unable to log out on this device).
  // Wait for that specific network response directly, not the URL change
  // -- otherwise this assertion races ahead of the real server-side
  // revoke and can observe it as "not yet happened" even though it's
  // correctly in flight.
  const logoutResponse = page.waitForResponse(
    (res) => res.request().method() === "POST" && res.url().endsWith("/auth/logout"),
  );
  await page.getByRole("button", { name: "Log out" }).click();
  await page.waitForURL(/\/login$/);
  const res = await logoutResponse;
  expect(res.status()).toBe(204);

  // Local storage must be fully cleared.
  const accessAfter = await page.evaluate(() => localStorage.getItem("access_token"));
  const refreshAfter = await page.evaluate(() => localStorage.getItem("refresh_token"));
  expect(accessAfter).toBeNull();
  expect(refreshAfter).toBeNull();

  // The refresh token that was actually current at logout time must now
  // be rejected -- proves the server-side revoke genuinely happened, not
  // just a local clear.
  const reuse = await page.request.post(`${API}/auth/refresh`, {
    data: { refresh_token: refreshToken },
  });
  expect(reuse.status()).toBe(401);
});
