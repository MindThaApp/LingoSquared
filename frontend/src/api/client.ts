import type { ApiErrorBody } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// General feedback (POST /feedback) deliberately targets a SEPARATE,
// independently-configurable base URL, not BASE_URL. If this app is ever
// run as many independent local installs (each with its own local
// backend), feedback still needs to reach ONE centrally-reachable
// collector Ramin actually checks -- pointing feedback at whatever
// backend happens to be running locally would silently strand it there.
// Falls back to BASE_URL, which is correct for the single-shared-backend
// deployment shapes (home server, hosted domain) where there's only ever
// one backend anyway. See docs/CONTRACT.md's "General app/page feedback"
// section.
const FEEDBACK_BASE_URL = import.meta.env.VITE_FEEDBACK_API_URL ?? BASE_URL;

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

function getToken(): string | null {
  return localStorage.getItem("access_token");
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

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

export function post<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

// POST /feedback is intentionally unauthenticated and lives on its own
// base URL (see FEEDBACK_BASE_URL above) -- deliberately NOT built on
// apiFetch, since apiFetch's 401-means-session-expired handling and
// single BASE_URL don't apply here: a token from a different backend
// (the distributed-local-install case) may fail validation there, and
// that must resolve to an anonymous report, never a forced logout.
export async function postFeedback<T>(path: string, body: unknown): Promise<T> {
  const token = getToken();
  const headers = new Headers({ "Content-Type": "application/json" });
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${FEEDBACK_BASE_URL}${path}`, {
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
