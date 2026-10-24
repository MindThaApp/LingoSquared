// Scrubbing for anything that leaves the browser through Sentry. Kept free
// of the SDK so it can be unit-tested (and reused) on its own.
export const REDACTED = "[Filtered]";

const SENSITIVE_KEY_PARTS = [
  "authorization",
  "cookie",
  "password",
  "passwd",
  "secret",
  "token",
  "api_key",
  "apikey",
  "email",
  "credential",
  "jwt",
  // Learner free text: typed/spoken answers, feedback descriptions.
  "answer",
  "response_text",
  "transcript",
  "description",
  "free_text",
  "freetext",
  "user_input",
];

const EMAIL_RE = /[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+/g;
const JWT_RE = /\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*/g;
const BEARER_RE = /\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}/gi;
const KV_SECRET_RE = /\b(password|passwd|token|secret|access_token|refresh_token|api_key)(=|:\s*)[^\s&,;"']+/gi;
const UUID_RE = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi;

function isSensitiveKey(key: string): boolean {
  const k = key.toLowerCase();
  return SENSITIVE_KEY_PARTS.some((part) => k.includes(part));
}

export function scrubString(value: string): string {
  return value
    .replace(JWT_RE, REDACTED)
    .replace(BEARER_RE, (_m, scheme: string) => `${scheme} ${REDACTED}`)
    .replace(KV_SECRET_RE, (_m, k: string, sep: string) => `${k}${sep}${REDACTED}`)
    .replace(EMAIL_RE, "[email]");
}

export function scrubValue(value: unknown, depth = 0): unknown {
  if (depth > 12) return REDACTED;
  if (typeof value === "string") return scrubString(value);
  if (Array.isArray(value)) return value.map((v) => scrubValue(v, depth + 1));
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
      out[k] = isSensitiveKey(k) ? REDACTED : scrubValue(v, depth + 1);
    }
    return out;
  }
  return value;
}

// Volatile bits (ids, counts) must not split one bug into many issues.
export function normalizeForFingerprint(message: string): string {
  return message.replace(UUID_RE, "UUID").replace(/\d+/g, "N").slice(0, 200);
}

interface ScrubbableEvent {
  request?: Record<string, unknown> & { headers?: Record<string, unknown>; url?: string };
  user?: Record<string, unknown>;
  exception?: { values?: Array<{ type?: string; value?: string }> };
  transaction?: string;
  fingerprint?: string[];
  [key: string]: unknown;
}

export function scrubEvent<T extends object>(event: T): T & { fingerprint?: string[] } {
  const e = event as unknown as ScrubbableEvent;
  if (e.request) {
    delete e.request.data;
    delete e.request.cookies;
    delete e.request.query_string;
    if (e.request.headers) {
      e.request.headers = Object.fromEntries(
        Object.entries(e.request.headers).map(([k, v]) => [
          k,
          isSensitiveKey(k) ? REDACTED : scrubValue(v),
        ]),
      );
    }
    if (typeof e.request.url === "string") {
      e.request.url = scrubString(e.request.url.split("?")[0].split("#")[0]);
    }
  }
  if (e.user) e.user = e.user.id !== undefined ? { id: e.user.id } : {};
  for (const section of ["extra", "contexts", "breadcrumbs", "exception", "message", "tags"]) {
    if (section in e) e[section] = scrubValue(e[section]);
  }
  const values = e.exception?.values;
  if (values?.length && !e.fingerprint) {
    const last = values[values.length - 1];
    e.fingerprint = [last.type ?? "Error", normalizeForFingerprint(last.value ?? "")];
  }
  return event;
}
