// Learner setting for crash reports: "never" | "ask" | "always" (default
// "ask"). Per-device in localStorage -- the backend has no per-user
// preference store, and this follows the same precedent as the TTS speed
// and voice preferences (see ttsSpeedPreferences.ts).
export type CrashConsent = "never" | "ask" | "always";

export const CRASH_CONSENT_KEY = "crash-report-consent";
export const CRASH_CONSENT_VALUES: readonly CrashConsent[] = ["never", "ask", "always"];

export function getCrashConsent(): CrashConsent {
  try {
    const raw = localStorage.getItem(CRASH_CONSENT_KEY);
    if (raw === "never" || raw === "ask" || raw === "always") return raw;
  } catch {
    // Storage unavailable (private mode): fall through to the default.
  }
  return "ask";
}

export function setCrashConsent(value: CrashConsent): void {
  try {
    if (value === "ask") localStorage.removeItem(CRASH_CONSENT_KEY);
    else localStorage.setItem(CRASH_CONSENT_KEY, value);
  } catch {
    // Not worth surfacing; the choice just won't persist.
  }
}
