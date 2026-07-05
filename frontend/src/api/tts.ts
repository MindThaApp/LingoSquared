import type { TtsFallback } from "./types";
import { getVoicePreference } from "../lib/voicePreferences";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Web Speech API lang tags are best-effort per language. Dari has no
// standard BCP-47 tag with reliable browser voice support; fa-AF is the
// closest approximation but many browsers will silently fall back to
// whatever Farsi/default voice is installed, or produce no sound at all
// if the OS has no matching voice — this is a real limitation, not a bug.
export const BROWSER_TTS_LANG: Record<string, string> = {
  en: "en-US",
  nl: "nl-NL",
  fr: "fr-FR",
  de: "de-DE",
  it: "it-IT",
  es: "es-ES",
  ru: "ru-RU",
  zh: "zh-CN",
  fa: "fa-IR",
  prs: "fa-AF",
};

function hasBrowserVoiceFor(languageCode: string): boolean {
  if (!("speechSynthesis" in window)) return false;
  const tag = BROWSER_TTS_LANG[languageCode] ?? languageCode;
  const primarySubtag = tag.split("-")[0].toLowerCase();
  return window.speechSynthesis
    .getVoices()
    .some((voice) => voice.lang.toLowerCase().startsWith(primarySubtag));
}

// Returns false when there is genuinely no voice available for this
// language on this device — the caller can use that to show real feedback
// instead of a silent no-op (a real, confirmed gap for Farsi/Dari on many
// browsers/OSes, not a bug in this code).
function speakInBrowser(text: string, languageCode: string): boolean {
  if (!hasBrowserVoiceFor(languageCode)) return false;

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = BROWSER_TTS_LANG[languageCode] ?? languageCode;

  const preferredVoiceURI = getVoicePreference(languageCode);
  if (preferredVoiceURI) {
    const match = window.speechSynthesis
      .getVoices()
      .find((voice) => voice.voiceURI === preferredVoiceURI);
    if (match) utterance.voice = match;
  }

  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
  return true;
}

// Phase D4 priority chain: recorded human audio beats any TTS when it
// exists. Tries the static asset first; any failure (404 - most keys
// have no recording yet, this is expected not exceptional - or a
// network error) falls through to the normal TTS chain unchanged.
async function playRecordedAsset(mediaAssetKey: string): Promise<boolean> {
  try {
    const response = await fetch(`${BASE_URL}/media/${encodeURIComponent(mediaAssetKey)}`);
    if (!response.ok) return false;
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.addEventListener("ended", () => URL.revokeObjectURL(url));
    await audio.play();
    return true;
  } catch {
    return false;
  }
}

export async function speak(
  text: string,
  languageCode: string,
  mediaAssetKey?: string,
): Promise<boolean> {
  if (mediaAssetKey && (await playRecordedAsset(mediaAssetKey))) {
    return true;
  }
  return speakViaTtsAndBrowser(text, languageCode);
}

async function speakViaTtsAndBrowser(text: string, languageCode: string): Promise<boolean> {
  const token = localStorage.getItem("access_token");
  const headers = new Headers({ "Content-Type": "application/json" });
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/tts`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text, language_code: languageCode }),
    });
  } catch {
    return speakInBrowser(text, languageCode);
  }

  if (!response.ok) {
    return speakInBrowser(text, languageCode);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("audio")) {
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.addEventListener("ended", () => URL.revokeObjectURL(url));
    void audio.play();
    return true;
  }

  // application/json — { use_browser_tts: true, reason: ... }
  const body: TtsFallback = await response.json();
  if (body.use_browser_tts) {
    return speakInBrowser(text, languageCode);
  }
  return false;
}
