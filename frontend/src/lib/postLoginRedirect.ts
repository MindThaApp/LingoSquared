// Post-login redirect target. The route guard passes the originally requested
// location in router state `from`; LoginPage navigates there after success.
// Only same-app absolute paths are honored (open-redirect guard).
export function safeRedirectPath(from: unknown, fallback = "/"): string {
  if (typeof from !== "string") return fallback;
  if (!from.startsWith("/") || from.startsWith("//") || from.startsWith("/\\")) return fallback;
  if (/[\u0000-\u001f\\]/.test(from)) return fallback;
  if (from === "/login" || from.startsWith("/login?") || from.startsWith("/login#")) return fallback;
  return from;
}

export function redirectFromState(state: unknown): string {
  const from = (state as { from?: unknown } | null)?.from;
  return safeRedirectPath(from);
}
