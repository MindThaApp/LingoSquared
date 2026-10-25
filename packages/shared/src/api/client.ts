import type { ApiErrorBody } from "./types";

// Platform seam (added when this file moved from frontend/src/api/client.ts
// into @lingo/shared): this package has no access to import.meta.env or
// localStorage (neither exists in a React Native runtime), so every
// caller MUST call configureApi() once at startup before making any
// request. Each platform (web's frontend/src/main.tsx, and later
// mobile/'s entry point) supplies its own base URLs and token storage;
// the request logic below is otherwise byte-for-byte the same as the
// original web-only client.
export interface ApiTokenStorage {
  get(): string | null;
  set(token: string): void;
  // Refresh-token half of the session (added when the backend moved to
  // 30-minute access tokens + 60-day rotating refresh tokens -- see
  // docs/CONTRACT.md's Auth section). OPTIONAL: a platform implementation
  // that hasn't adopted refresh tokens yet (e.g. mobile/lib/tokenStorage.ts,
  // built separately) remains a valid ApiTokenStorage with zero changes --
  // refreshSession() below treats their absence as "this platform has no
  // refresh capability" and falls back to the old hard-logout-on-401
  // behavior rather than crashing.
  getRefresh?(): string | null;
  setRefresh?(token: string): void;
  // OPTIONAL "next refresh token" slot. Before each POST /auth/refresh the
  // client generates its proposed successor and persists it here FIRST, so
  // that if the page is closed or reloaded while the request is in flight
  // (the server rotated, the response was lost) the next attempt can resend
  // the identical request and the server answers it idempotently instead of
  // treating the old token as stolen. Platforms without it still work; they
  // just rely on the server's short grace window for that case.
  getPendingRefresh?(): string | null;
  setPendingRefresh?(token: string | null): void;
  // clear() must remove BOTH the access and refresh tokens (when the
  // platform supports refresh tokens at all), plus any pending one -- it
  // is the "session is dead" operation, not just an access-token reset.
  clear(): void;
}

export interface ApiConfig {
  baseUrl: string;
  // General feedback (POST /feedback) deliberately targets a SEPARATE,
  // independently-configurable base URL, not baseUrl. If this app is ever
  // run as many independent local installs (each with its own local
  // backend), feedback still needs to reach ONE centrally-reachable
  // collector Ramin actually checks -- pointing feedback at whatever
  // backend happens to be running locally would silently strand it there.
  // Callers that don't need this distinction (a single-shared-backend
  // deployment) should just pass the same value as baseUrl. See
  // docs/CONTRACT.md's "General app/page feedback" section.
  feedbackBaseUrl: string;
  tokenStorage: ApiTokenStorage;
}

let config: ApiConfig | null = null;

export function configureApi(newConfig: ApiConfig): void {
  config = newConfig;
}

function requireConfig(): ApiConfig {
  if (!config) {
    throw new Error(
      "configureApi() must be called before making any API request.",
    );
  }
  return config;
}

export class ApiError extends Error {
  code: string;
  status: number;
  details: Record<string, unknown>;
  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

// ---- Session-token helpers (used by AuthApi in endpoints.ts) ----------

export function storeAuthTokens(accessToken: string, refreshToken: string): void {
  const { tokenStorage } = requireConfig();
  tokenStorage.set(accessToken);
  // Truthiness + capability guard: against a not-yet-upgraded backend
  // (mixed-deploy window) login/register responses might have no
  // refresh_token field, and a platform without refresh support has no
  // setRefresh() at all -- either way, storing "undefined" as a literal
  // string would later be presented as a real token.
  if (refreshToken && tokenStorage.setRefresh) tokenStorage.setRefresh(refreshToken);
  // A brand-new session: any pending successor belonged to the old one.
  tokenStorage.setPendingRefresh?.(null);
}

export function getStoredRefreshToken(): string | null {
  return requireConfig().tokenStorage.getRefresh?.() ?? null;
}

export function clearAuthTokens(): void {
  requireConfig().tokenStorage.clear();
}

// ---- Silent refresh (POST /auth/refresh) ------------------------------
//
// Access tokens are deliberately short-lived (30 minutes -- see
// docs/CONTRACT.md's Auth section); session continuity comes from the
// long-lived rotating refresh token. Any authenticated request that gets
// a 401 attempts exactly one refresh + retry before giving up.
//
// Outcomes are three-valued, not boolean, because the failure modes must
// be handled differently:
//   - "invalid": the server definitively rejected the refresh token
//     (expired / revoked / reuse-detected), or this platform has no
//     refresh capability / no stored refresh token at all. The session is
//     genuinely dead -> clear it and fire the logout flow.
//   - "unavailable": the refresh COULDN'T be evaluated (network drop,
//     5xx, malformed body). The session may still be perfectly fine, so
//     the tokens must NOT be cleared -- for guest accounts a cleared
//     session is permanently unrecoverable (see AuthContext.tsx), so a
//     transient outage must never destroy one.
type RefreshOutcome = "refreshed" | "invalid" | "unavailable";

// Shared in-flight promise: when several requests 401 at the same moment
// (e.g. a page firing parallel queries just after the access token
// expired), only ONE /auth/refresh call goes out and every 401 awaits it.
// Without this, each concurrent 401 would spend the (single-use, rotating)
// refresh token independently -- the first would win and the rest would be
// treated as token REUSE by the server, which revokes the whole session.
//
// That only covers one page. Other tabs share the same stored tokens, so
// the refresh itself also runs under a cross-tab Web Lock where the
// platform has one: a tab that waited for the lock and finds the stored
// refresh token already changed simply adopts the other tab's result.
let refreshInFlight: Promise<RefreshOutcome> | null = null;

const REFRESH_LOCK_NAME = "lingo-auth-refresh";

// The refresh request runs while holding the cross-tab lock, so a stalled
// connection (captive portal, half-open TCP) must not hold it until the
// browser gives up minutes later and freeze refresh in every tab. On
// timeout the pending successor is kept, so the retry stays idempotent.
export const REFRESH_TIMEOUT_MS = 15_000;

function timeoutSignal(ms: number): { signal?: AbortSignal; cancel(): void } {
  if (typeof AbortController !== "function") return { cancel() {} };
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  return { signal: controller.signal, cancel: () => clearTimeout(timer) };
}

interface LockManagerLike {
  request<T>(name: string, callback: () => Promise<T>): Promise<T>;
}

function crossTabLock(): LockManagerLike | null {
  const nav = (globalThis as { navigator?: { locks?: LockManagerLike } }).navigator;
  return nav?.locks && typeof nav.locks.request === "function" ? nav.locks : null;
}

// 48 random bytes, base64url -- the same shape and strength as a
// server-issued refresh token. null when the platform has no CSPRNG, in
// which case no successor is proposed and the server picks one.
function generateRefreshToken(): string | null {
  try {
    const cryptoApi = (globalThis as { crypto?: Crypto }).crypto;
    if (!cryptoApi?.getRandomValues) return null;
    const bytes = cryptoApi.getRandomValues(new Uint8Array(48));
    let binary = "";
    for (const byte of bytes) binary += String.fromCharCode(byte);
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  } catch {
    return null;
  }
}

function refreshSession(): Promise<RefreshOutcome> {
  if (!refreshInFlight) {
    refreshInFlight = doRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

// Raw fetch on purpose, NOT apiFetch: apiFetch's own 401 handling would
// recurse straight back into this function.
async function doRefresh(): Promise<RefreshOutcome> {
  const { tokenStorage } = requireConfig();
  if (!tokenStorage.getRefresh || !tokenStorage.setRefresh) return "invalid";
  const seenRefreshToken = tokenStorage.getRefresh();
  if (!seenRefreshToken) return "invalid";
  const lock = crossTabLock();
  if (!lock) return refreshWith(seenRefreshToken);
  try {
    return await lock.request(REFRESH_LOCK_NAME, () => refreshWith(seenRefreshToken));
  } catch {
    return "unavailable";
  }
}

async function refreshWith(seenRefreshToken: string): Promise<RefreshOutcome> {
  const { baseUrl, tokenStorage } = requireConfig();
  const refreshToken = tokenStorage.getRefresh?.() ?? null;
  if (!refreshToken) return "invalid";
  // Another tab rotated the pair while this one waited for the lock: its
  // result is already in shared storage.
  if (refreshToken !== seenRefreshToken) return "refreshed";

  // Store before use: reuse a pending successor left by an earlier attempt
  // whose response never arrived (resending the identical request is what
  // lets the server answer it idempotently), otherwise create and persist
  // a new one BEFORE the request goes out.
  let nextRefreshToken = tokenStorage.getPendingRefresh?.() ?? null;
  if (nextRefreshToken === refreshToken) nextRefreshToken = null;
  if (!nextRefreshToken && tokenStorage.setPendingRefresh) {
    nextRefreshToken = generateRefreshToken();
    if (nextRefreshToken) tokenStorage.setPendingRefresh(nextRefreshToken);
  }
  if (!tokenStorage.setPendingRefresh) nextRefreshToken = null;

  let res: Response;
  const timeout = timeoutSignal(REFRESH_TIMEOUT_MS);
  try {
    res = await fetch(`${baseUrl}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(
        nextRefreshToken
          ? { refresh_token: refreshToken, next_refresh_token: nextRefreshToken }
          : { refresh_token: refreshToken },
      ),
      signal: timeout.signal,
    });
  } catch {
    // Network failure or timeout. Keep the pending successor: the request
    // may have reached the server.
    return "unavailable";
  } finally {
    timeout.cancel();
  }
  if (res.status === 401) {
    tokenStorage.setPendingRefresh?.(null);
    return "invalid";
  }
  // 422 means the stored proposal itself was unusable (e.g. a corrupted
  // value); drop it so the next attempt generates a fresh one.
  if (res.status === 422) tokenStorage.setPendingRefresh?.(null);
  if (!res.ok) return "unavailable";
  let body: { access_token?: string; refresh_token?: string };
  try {
    body = await res.json();
  } catch {
    return "unavailable";
  }
  if (!body.access_token || !body.refresh_token) return "unavailable";
  // Rotation: the server just revoked the token we presented and issued a
  // fresh pair -- store BOTH, or the next refresh would present a revoked
  // token and trip the server's reuse-detection (revokes everything). The
  // response is authoritative even when it differs from our proposal.
  tokenStorage.setRefresh?.(body.refresh_token);
  tokenStorage.set(body.access_token);
  tokenStorage.setPendingRefresh?.(null);
  return "refreshed";
}

// ---- Shared authenticated-request core --------------------------------
//
// EVERY authenticated request goes through this, whatever it returns
// (apiFetch's JSON, getFile's Blob, any future variant): a 401 means
// "the 30-minute access token expired", which is the NORMAL state for a
// returning user, so it must trigger refresh-and-retry -- never a
// straight logout. getFile used to own a hand-rolled copy of this block
// that skipped the refresh entirely, so "Export CSV" on a stale token
// threw the user to the login screen; for a guest account (generated
// password never shown -- see AuthContext.tsx) that is permanent,
// unrecoverable loss of all progress. Keep the retry policy here and
// here only, so the two paths can never drift apart again.
//
// `send` must build its headers (including Authorization) fresh on every
// call: the post-refresh retry has to pick up the NEW access token, not
// the expired one the first attempt used.
async function sendWithAuthRetry(
  send: () => Promise<Response>,
  isAuthEndpoint = false,
): Promise<Response> {
  let res = await send();
  if (res.status === 401 && !isAuthEndpoint) {
    const outcome = await refreshSession();
    if (outcome === "refreshed") {
      // Retry the original request exactly once with the new token.
      // options.body is always an already-serialized string (see post()/
      // patch() below), so re-sending it is safe.
      res = await send();
    }
    if (res.status === 401) {
      if (outcome !== "unavailable") {
        // Refresh definitively failed (or the retried request still
        // 401ed on a brand-new token): the session is genuinely dead.
        requireConfig().tokenStorage.clear();
        onUnauthorized?.();
      }
      // "unavailable" (network/5xx during refresh) deliberately skips the
      // clear/logout: this request fails, but the stored session survives
      // for a later retry once the backend is reachable again.
      throw new ApiError(401, "unauthorized", "Session expired");
    }
  }
  return res;
}

// Shared error-envelope decoding for the non-ok responses of the
// authenticated paths -- this app reshapes every HTTPException to
// {"error": {code, message, ...details}} in main.py.
async function throwApiError(res: Response): Promise<never> {
  let body: ApiErrorBody | null = null;
  try {
    body = await res.json();
  } catch {
    // non-JSON error body, fall through to generic message
  }
  const details: Record<string, unknown> = { ...(body?.error ?? {}) };
  delete details.code;
  delete details.message;
  throw new ApiError(
    res.status,
    body?.error?.code ?? "unknown_error",
    body?.error?.message ?? res.statusText,
    details,
  );
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const { baseUrl, tokenStorage } = requireConfig();

  const send = (): Promise<Response> => {
    const token = tokenStorage.get();
    const headers = new Headers(options.headers);
    headers.set("Content-Type", "application/json");
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return fetch(`${baseUrl}${path}`, { ...options, headers });
  };

  // Auth endpoints return 401 for ordinary "wrong password" cases, not an
  // expired session — only treat 401 as session expiry for authenticated
  // requests that had a token to begin with. /auth/refresh is listed
  // defensively (it's only ever called via doRefresh's raw fetch today);
  // /auth/logout is unauthenticated server-side and never 401s.
  const isAuthEndpoint =
    path.startsWith("/auth/login") ||
    path.startsWith("/auth/register") ||
    path.startsWith("/auth/refresh");

  const res = await sendWithAuthRetry(send, isAuthEndpoint);

  if (!res.ok) await throwApiError(res);

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function get<T>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "GET" });
}

// File-download variant of apiFetch: same base URL / bearer-token /
// 401-means-session-expired / error-envelope handling (all of it shared
// via sendWithAuthRetry + throwApiError, never re-implemented here), but
// returns the raw body as a Blob (plus the server's suggested filename
// from Content-Disposition) instead of parsing JSON -- apiFetch's
// unconditional res.json() would corrupt a CSV/TSV body. The only
// deliberate difference from apiFetch is the absent Content-Type header:
// this is a bodyless GET. Used by the vocabulary export.
export async function getFile(
  path: string,
): Promise<{ blob: Blob; filename: string | null }> {
  const { baseUrl, tokenStorage } = requireConfig();

  const send = (): Promise<Response> => {
    const token = tokenStorage.get();
    const headers = new Headers();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return fetch(`${baseUrl}${path}`, { method: "GET", headers });
  };

  const res = await sendWithAuthRetry(send);

  if (!res.ok) await throwApiError(res);

  const disposition = res.headers.get("content-disposition");
  const filename = disposition?.match(/filename="([^"]+)"/)?.[1] ?? null;
  return { blob: await res.blob(), filename };
}

// Additive: authenticated POST that returns the raw Response (any non-401
// status is returned as-is, not thrown) so callers can branch on
// content-type / body shape -- used by the web /tts client, whose success
// body is either audio bytes or a JSON fallback marker. Goes through
// sendWithAuthRetry so an expired access token refreshes + retries once.
export async function postRaw(path: string, body?: unknown): Promise<Response> {
  const { baseUrl, tokenStorage } = requireConfig();
  const send = (): Promise<Response> => {
    const token = tokenStorage.get();
    const headers = new Headers({ "Content-Type": "application/json" });
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return fetch(`${baseUrl}${path}`, {
      method: "POST",
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };
  return sendWithAuthRetry(send);
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

// POST /feedback is intentionally unauthenticated and lives on its own
// base URL (see feedbackBaseUrl above) -- deliberately NOT built on
// apiFetch, since apiFetch's 401-means-session-expired handling and
// single baseUrl don't apply here: a token from a different backend
// (the distributed-local-install case) may fail validation there, and
// that must resolve to an anonymous report, never a forced logout.
export async function postFeedback<T>(path: string, body: unknown): Promise<T> {
  const { feedbackBaseUrl, tokenStorage } = requireConfig();
  const token = tokenStorage.get();
  const headers = new Headers({ "Content-Type": "application/json" });
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${feedbackBaseUrl}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let body2: ApiErrorBody | null = null;
    try {
      body2 = await res.json();
    } catch {
      // non-JSON error body, fall through to generic message
    }
    throw new ApiError(
      res.status,
      body2?.error?.code ?? "unknown_error",
      body2?.error?.message ?? res.statusText,
    );
  }

  return res.json() as Promise<T>;
}

// Multipart variant of postFeedback -- POST /feedback/attachments takes a
// raw file (field name "file"), not JSON. Same base-URL/no-forced-logout
// rationale as postFeedback: it's unauthenticated and must never trigger
// the shared apiFetch's 401-means-session-expired handling. Deliberately
// does NOT set a Content-Type header -- the browser/fetch sets the
// multipart boundary itself when given a FormData body; setting it
// manually breaks the boundary.
export async function postFeedbackFile<T>(path: string, file: Blob, filename: string): Promise<T> {
  const { feedbackBaseUrl, tokenStorage } = requireConfig();
  const token = tokenStorage.get();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const form = new FormData();
  form.append("file", file, filename);

  const res = await fetch(`${feedbackBaseUrl}${path}`, {
    method: "POST",
    headers,
    body: form,
  });

  if (!res.ok) {
    let body2: ApiErrorBody | null = null;
    try {
      body2 = await res.json();
    } catch {
      // non-JSON error body, fall through to generic message
    }
    throw new ApiError(
      res.status,
      body2?.error?.code ?? "unknown_error",
      body2?.error?.message ?? res.statusText,
    );
  }

  return res.json() as Promise<T>;
}

export function put<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "PUT",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function patch<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "PATCH",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

// "del" rather than "delete" (a reserved word). The backend's DELETE
// endpoints return 204 No Content; apiFetch already resolves that to
// undefined, so callers should use del<void>.
export function del<T>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "DELETE" });
}
