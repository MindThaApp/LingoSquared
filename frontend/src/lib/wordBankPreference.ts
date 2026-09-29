// Per-user "Type instead" / "Use word bank" choice for beginner answer modes.
// localStorage, scoped by user id so two accounts on one device don't share
// it (same per-device precedent as practiceModePreference.ts). Unset = the
// CEFR-level default. No user id -> nothing is persisted (session only).
import type { CefrLevel } from "@lingo/shared/api/types";

export type AnswerMode = "bank" | "type";

const KEY_PREFIX = "word-bank-mode:";

export function defaultAnswerMode(level: CefrLevel | null | undefined): AnswerMode {
  return level === "A1" || level === "A2" ? "bank" : "type";
}

export function getWordBankPreference(userId: string | null | undefined): AnswerMode | null {
  if (!userId) return null;
  try {
    const raw = localStorage.getItem(KEY_PREFIX + userId);
    return raw === "bank" || raw === "type" ? raw : null;
  } catch {
    return null;
  }
}

export function setWordBankPreference(userId: string | null | undefined, mode: AnswerMode): void {
  if (!userId) return;
  try {
    localStorage.setItem(KEY_PREFIX + userId, mode);
  } catch {
    // Storage unavailable (private mode / quota): the choice just won't persist.
  }
}
