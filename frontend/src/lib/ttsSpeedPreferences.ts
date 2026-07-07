// Per-language, per-device TTS speech-speed preference. Stored client-side
// (not on the user's account), same precedent as the per-language browser
// voice preference (`voicePreferences.ts`) and the STT mic/keyboard toggle
// (`answerInputMode.ts`): /tts never caches synthesized audio across
// users/requests, so there's no shared-cache-correctness reason to push
// this server-side, and "what speed sounds natural" is a per-learner
// judgment call anyway, not an account-wide fact.
const STORAGE_PREFIX = "tts-speed-";

// Exposed UI range — narrower than the providers' own bounds (Google
// accepts [0.25, 2.0], the /tts route validates the same). 0.75-1.25 is
// the sensible range for a language learner: much slower feels unnatural
// and teaches a false rhythm, much faster defeats comprehension, which is
// the whole reason this feature exists (Dutch TTS reported "too fast" at
// the default 1.0).
export const MIN_SPEED = 0.75;
export const MAX_SPEED = 1.25;
export const DEFAULT_SPEED = 1.0;

function clamp(value: number): number {
  return Math.min(MAX_SPEED, Math.max(MIN_SPEED, value));
}

export function getSpeedPreference(languageCode: string): number {
  const raw = localStorage.getItem(STORAGE_PREFIX + languageCode);
  if (!raw) return DEFAULT_SPEED;
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return DEFAULT_SPEED;
  return clamp(parsed);
}

export function setSpeedPreference(languageCode: string, speed: number): void {
  const key = STORAGE_PREFIX + languageCode;
  if (speed === DEFAULT_SPEED) {
    // Keep localStorage tidy — no stored key means "use the default",
    // same convention as voicePreferences.ts using null to mean unset.
    localStorage.removeItem(key);
  } else {
    localStorage.setItem(key, String(clamp(speed)));
  }
}
