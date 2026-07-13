// Per-device Endless Practice mode preference (mixed / speaking /
// conversation). Stored client-side, same precedent as the per-language
// TTS voice/speed preferences and the STT mic/keyboard toggle
// (`answerInputMode.ts`): which drill style a learner wants is a
// per-device, per-session comfort call, not an account-wide fact.
import type { PracticeBatchMode } from "@lingo/shared/api/types";

const STORAGE_KEY = "practice-mode";

const VALID_MODES: PracticeBatchMode[] = ["mixed", "speaking", "conversation"];

export function getPracticeModePreference(): PracticeBatchMode {
  const raw = localStorage.getItem(STORAGE_KEY);
  return VALID_MODES.includes(raw as PracticeBatchMode)
    ? (raw as PracticeBatchMode)
    : "mixed";
}

export function setPracticeModePreference(mode: PracticeBatchMode): void {
  if (mode === "mixed") {
    // Keep localStorage tidy — no stored key means "use the default".
    localStorage.removeItem(STORAGE_KEY);
  } else {
    localStorage.setItem(STORAGE_KEY, mode);
  }
}
