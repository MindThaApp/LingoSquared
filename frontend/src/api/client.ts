import type { ApiErrorBody } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

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

export function patch<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "PATCH",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}
