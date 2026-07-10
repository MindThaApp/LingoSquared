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

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const { baseUrl, tokenStorage } = requireConfig();
  const token = tokenStorage.get();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${baseUrl}${path}`, { ...options, headers });

  // Auth endpoints return 401 for ordinary "wrong password" cases, not an
  // expired session — only treat 401 as session expiry for authenticated
  // requests that had a token to begin with.
  const isAuthEndpoint = path.startsWith("/auth/login") || path.startsWith("/auth/register");
  if (res.status === 401 && !isAuthEndpoint) {
    onUnauthorized?.();
    throw new ApiError(401, "unauthorized", "Session expired");
  }

  if (!res.ok) {
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

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function get<T>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "GET" });
}

// File-download variant of apiFetch: same base URL / bearer-token /
// 401-means-session-expired / error-envelope handling, but returns the raw
// body as a Blob (plus the server's suggested filename from
// Content-Disposition) instead of parsing JSON -- apiFetch's unconditional
// res.json() would corrupt a CSV/TSV body. Used by the vocabulary export.
export async function getFile(
  path: string,
): Promise<{ blob: Blob; filename: string | null }> {
  const { baseUrl, tokenStorage } = requireConfig();
  const token = tokenStorage.get();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${baseUrl}${path}`, { method: "GET", headers });

  if (res.status === 401) {
    onUnauthorized?.();
    throw new ApiError(401, "unauthorized", "Session expired");
  }
  if (!res.ok) {
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

  const disposition = res.headers.get("content-disposition");
  const filename = disposition?.match(/filename="([^"]+)"/)?.[1] ?? null;
  return { blob: await res.blob(), filename };
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
