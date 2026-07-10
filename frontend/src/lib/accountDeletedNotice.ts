// One-time "your account was deleted" handoff from ProfilePage's delete
// flow to LoginPage. Route state can't carry this reliably: React Router
// v7 wraps navigate() in startTransition, so AuthContext's urgent
// setUser(null) re-render lands first — ProtectedRoute (still mounted on
// the profile route at that moment) emits its own stateless
// <Navigate to="/login" replace />, clobbering any state passed to the
// explicit navigate call (confirmed live, 2026-07-10). sessionStorage is
// immune to that render-ordering race, survives exactly until LoginPage
// consumes it, and is scoped to the tab.
const KEY = "account_deleted_notice";

export function setAccountDeletedNotice(): void {
  sessionStorage.setItem(KEY, "1");
}

export function peekAccountDeletedNotice(): boolean {
  return sessionStorage.getItem(KEY) === "1";
}

// Split from peek (rather than a single consuming read) so LoginPage can
// peek in a useState initializer and clear in an effect — a consuming
// read in the initializer would double-run under dev StrictMode and lose
// the flag before the render that matters.
export function clearAccountDeletedNotice(): void {
  sessionStorage.removeItem(KEY);
}
