// Per-user "Show pronunciation" choice (romanized text under target-language text).
// localStorage, scoped by user id, same per-device precedent as wordBankPreference.ts.
// Unset = the CEFR-level default: ON at A1, OFF from A2. No user id -> not persisted.
import type { CefrLevel } from "@lingo/shared/api/types";

const KEY_PREFIX = "translit-show:";

/** Target languages that have a pronunciation store. */
export const TRANSLIT_LANGUAGES: ReadonlySet<string> = new Set(["ru", "hi", "ar", "fa", "prs"]);
/** Languages whose store is machine-drafted and not yet native-reviewed (shown behind a "beta" marker). */
export const TRANSLIT_BETA_LANGUAGES: ReadonlySet<string> = new Set(["ar", "fa", "prs"]);

/** Build flag: show unreviewed drafts (default true for now). Set VITE_TRANSLIT_SHOW_UNREVIEWED=false to hide them. */
export function showUnreviewedTranslit(): boolean {
  const raw = (import.meta.env?.VITE_TRANSLIT_SHOW_UNREVIEWED as string | undefined) ?? "true";
  return raw.trim().toLowerCase() !== "false" && raw.trim() !== "0";
}

export function translitAvailableFor(lang: string | null | undefined): boolean {
  if (!lang) return false;
  const base = lang.split("-")[0];
  if (!TRANSLIT_LANGUAGES.has(base)) return false;
  return !TRANSLIT_BETA_LANGUAGES.has(base) || showUnreviewedTranslit();
}

export function defaultShowTranslit(level: CefrLevel | null | undefined): boolean {
  return level === "A1";
}

export function getTranslitPreference(userId: string | null | undefined): boolean | null {
  if (!userId) return null;
  try {
    const raw = localStorage.getItem(KEY_PREFIX + userId);
    return raw === "1" ? true : raw === "0" ? false : null;
  } catch {
    return null;
  }
}

export function setTranslitPreference(userId: string | null | undefined, show: boolean): void {
  if (!userId) return;
  try {
    localStorage.setItem(KEY_PREFIX + userId, show ? "1" : "0");
  } catch {
    // Storage unavailable (private mode / quota): the choice just won't persist.
  }
}

export function clearTranslitPreference(userId: string | null | undefined): void {
  if (!userId) return;
  try {
    localStorage.removeItem(KEY_PREFIX + userId);
  } catch {
    // ignore
  }
}

export function resolveShowTranslit(
  userId: string | null | undefined,
  level: CefrLevel | null | undefined,
): boolean {
  return getTranslitPreference(userId) ?? defaultShowTranslit(level);
}
