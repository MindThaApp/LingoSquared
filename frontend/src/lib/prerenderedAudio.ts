import { prerenderedAudioFile } from "@lingo/shared/audio/audioKey";

// Pre-rendered clips (scripts/render_audio.py) are addressed by a content hash that
// frontend and backend compute identically, so no manifest download is needed.
// Base URL: VITE_AUDIO_BASE_URL (e.g. "/media/audio" for the same-origin nginx
// location, which the service worker can cache), else the API's own
// /media/audio route. VITE_PRERENDERED_AUDIO=0 switches the tier off.
export function prerenderedAudioBase(apiBaseUrl: string): string | null {
  const env = import.meta.env;
  if (env.VITE_PRERENDERED_AUDIO === "0") return null;
  const explicit = env.VITE_AUDIO_BASE_URL as string | undefined;
  return (explicit ?? `${apiBaseUrl}/media/audio`).replace(/\/+$/, "");
}

/** Absolute/relative URL of the pre-rendered clip for already-sanitized `text`, or null. */
export function prerenderedAudioUrl(text: string, languageCode: string, apiBaseUrl: string): string | null {
  const base = prerenderedAudioBase(apiBaseUrl);
  if (!base) return null;
  const file = prerenderedAudioFile(text, languageCode);
  return file ? `${base}/${file}` : null;
}
