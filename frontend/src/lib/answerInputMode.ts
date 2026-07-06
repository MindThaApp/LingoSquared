// Silent (typed) vs. out-loud (mic) answer mode for speak_response/
// speak_repeat exercises. Session/local preference only — deliberately NOT
// an account-wide server field (mirrors voicePreferences.ts's reasoning:
// mic availability/permission is a per-device fact, not a user preference
// worth syncing across devices). Default is "type" (today's existing
// behavior) so nothing changes for a learner who never opts in.
const STORAGE_KEY = "answer-input-mode";

export type AnswerInputMode = "voice" | "type";

export function getAnswerInputMode(): AnswerInputMode {
  return localStorage.getItem(STORAGE_KEY) === "voice" ? "voice" : "type";
}

export function setAnswerInputMode(mode: AnswerInputMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    // Private-browsing/quota errors: not worth surfacing, just don't persist.
  }
}
