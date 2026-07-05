// Per-language, per-device browser-voice preference. Stored client-side
// (not on the user's account) since available voices depend entirely on
// the device/OS/browser — a voice picked on one machine may not exist on
// another, so a server-synced preference would silently fail elsewhere.
const STORAGE_PREFIX = "voice-pref-";

export function getVoicePreference(languageCode: string): string | null {
  return localStorage.getItem(STORAGE_PREFIX + languageCode);
}

export function setVoicePreference(languageCode: string, voiceURI: string | null): void {
  const key = STORAGE_PREFIX + languageCode;
  if (voiceURI) {
    localStorage.setItem(key, voiceURI);
  } else {
    localStorage.removeItem(key);
  }
}
