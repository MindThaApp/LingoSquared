// Silent (typed) vs. out-loud (mic) answer mode for speak_response/
// speak_repeat exercises. Session/local preference only — deliberately NOT
// an account-wide server field (mirrors voicePreferences.ts's reasoning:
// mic availability/permission is a per-device fact, not a user preference
// worth syncing across devices). Default is "type" (today's existing
// behavior) so nothing changes for a learner who never opts in.
//
// Platform seam (added when this file moved from frontend/src/lib/
// answerInputMode.ts into @lingo/shared): this package has no access to
// `localStorage` (it doesn't exist in a React Native runtime), so the
// actual persistence is injected via configureAnswerInputModeStore(). Each
// platform supplies its own store (web: a thin localStorage wrapper set up
// in frontend/src/main.tsx; mobile: an AsyncStorage-backed equivalent,
// later). If nothing has been configured yet (e.g. a consumer that reads
// this before startup finishes), getAnswerInputMode() safely falls back to
// the same "type" default as before rather than throwing.
export type AnswerInputMode = "voice" | "type";

export interface AnswerInputModeStore {
  get(): string | null;
  set(mode: AnswerInputMode): void;
}

let store: AnswerInputModeStore | null = null;

export function configureAnswerInputModeStore(newStore: AnswerInputModeStore): void {
  store = newStore;
}

export function getAnswerInputMode(): AnswerInputMode {
  return store?.get() === "voice" ? "voice" : "type";
}

export function setAnswerInputMode(mode: AnswerInputMode): void {
  store?.set(mode);
}
