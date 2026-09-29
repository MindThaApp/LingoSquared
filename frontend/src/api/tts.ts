import type { TtsFallback } from "@lingo/shared/api/types";
import { getVoicePreference } from "../lib/voicePreferences";
import { getSpeedPreference } from "../lib/ttsSpeedPreferences";
import { postRaw } from "@lingo/shared/api/client";
import { audioCache, audioCacheKey } from "../lib/audioCache";
import { sanitizeForSpeech } from "../lib/sanitizeForSpeech";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// One player at a time: any new speech first stops the previous element
// and cancels browser speech. `release` revokes a NON-cached URL (recorded
// clips); cached cloud-TTS URLs are owned by audioCache and never revoked here.
let current: { audio: HTMLAudioElement; release?: () => void } | null = null;

function stopCurrentPlayback(): void {
  if (current) {
    try {
      current.audio.pause();
      current.audio.currentTime = 0;
    } catch {
      // best-effort
    }
    current.release?.();
    current = null;
  }
  if (typeof window !== "undefined" && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}

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
  // SpeechSynthesisUtterance.rate's native range is much wider (0.1-10)
  // than the per-language speed preference we expose (0.75-1.25), so no
  // clamping needed here — getSpeedPreference() already clamps.
  utterance.rate = getSpeedPreference(languageCode);

  const preferredVoiceURI = getVoicePreference(languageCode);
  if (preferredVoiceURI) {
    const match = window.speechSynthesis
      .getVoices()
      .find((voice) => voice.voiceURI === preferredVoiceURI);
    if (match) utterance.voice = match;
  }

  stopCurrentPlayback();
  window.speechSynthesis.speak(utterance);
  return true;
}

// Phase D4 priority chain: recorded human audio beats any TTS when it
// exists. Tries the static asset first; any failure (404 - most keys
// have no recording yet, this is expected not exceptional - or a
// network error) falls through to the normal TTS chain unchanged.
//
// Recorded clips are a flat, fixed-speed MP3 — there's no synthesis step
// to parameterize server-side. The per-language speed preference is
// still applied here, client-side, via HTMLMediaElement.playbackRate (a
// real browser feature, not a hack — it resamples on the fly with pitch
// preservation on by default in every evergreen browser), so recorded
// audio respects the same preference as the two TTS tiers, just through
// a different mechanism. See docs/CONTRACT.md's Text-to-speech section.
// Session-scoped negative cache: asset keys known to be missing (404) are not
// re-requested on every press. Only definitive 404/410 are cached, never
// transient network/5xx errors.
const missingMediaKeys = new Set<string>();

async function playRecordedAsset(mediaAssetKey: string, languageCode: string): Promise<boolean> {
  if (missingMediaKeys.has(mediaAssetKey)) return false;
  try {
    const response = await fetch(`${BASE_URL}/media/${encodeURIComponent(mediaAssetKey)}`);
    if (!response.ok) {
      if (response.status === 404 || response.status === 410) missingMediaKeys.add(mediaAssetKey);
      return false;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.playbackRate = getSpeedPreference(languageCode);
    let released = false;
    const release = () => {
      if (!released) {
        released = true;
        URL.revokeObjectURL(url);
      }
    };
    audio.addEventListener("ended", release);
    stopCurrentPlayback();
    current = { audio, release };
    try {
      await audio.play();
    } catch (err) {
      release();
      if (current?.audio === audio) current = null;
      throw err;
    }
    return true;
  } catch {
    return false;
  }
}

// Speech-boundary sanitizing happens here and only here: the sanitized text
// is what gets synthesized AND what keys the audio cache. Empty after
// sanitizing -> nothing speakable -> honest `false` (no fallback to the raw
// text, which would read out the stripped label/gloss).
export async function speak(
  text: string,
  languageCode: string,
  mediaAssetKey?: string,
): Promise<boolean> {
  if (mediaAssetKey && (await playRecordedAsset(mediaAssetKey, languageCode))) {
    return true;
  }
  const spoken = sanitizeForSpeech(text);
  if (!spoken) return false;
  return speakViaTtsAndBrowser(spoken, languageCode);
}

async function playCloudUrl(url: string): Promise<boolean> {
  const audio = new Audio(url);
  stopCurrentPlayback();
  current = { audio };
  // Must await, not fire-and-forget: iOS Safari's play() requires
  // transient user-activation that can expire before this network
  // round-trip finishes on a slow connection, rejecting with
  // NotAllowedError. Unawaited, that rejection was silently dropped
  // and speak() reported success with no sound -- exactly the
  // "silently dead" outcome this whole fallback chain exists to avoid.
  try {
    await audio.play();
    return true;
  } catch {
    if (current?.audio === audio) current = null;
    return false;
  }
}

async function speakViaTtsAndBrowser(text: string, languageCode: string): Promise<boolean> {
  const speakingRate = getSpeedPreference(languageCode);
  const key = audioCacheKey(text, languageCode, speakingRate);

  const cached = audioCache.get(key);
  if (cached !== undefined) {
    if (await playCloudUrl(cached)) return true;
    return speakInBrowser(text, languageCode);
  }

  // Through the shared client so an expired access token gets the normal
  // refresh-and-retry instead of silently degrading to the browser voice.
  let response: Response;
  try {
    response = await postRaw("/tts", {
      text,
      language_code: languageCode,
      speaking_rate: speakingRate,
    });
  } catch {
    return speakInBrowser(text, languageCode);
  }

  if (!response.ok) {
    return speakInBrowser(text, languageCode);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("audio")) {
    // The provider already baked speakingRate into this audio — no
    // client-side playbackRate here, or the rate would apply twice.
    let url: string;
    try {
      const blob = await response.blob();
      url = URL.createObjectURL(blob);
    } catch {
      return speakInBrowser(text, languageCode);
    }
    audioCache.set(key, url);
    if (await playCloudUrl(url)) return true;
    return speakInBrowser(text, languageCode);
  }

  // application/json — { use_browser_tts: true, reason: ... }
  let body: TtsFallback;
  try {
    body = await response.json();
  } catch {
    return speakInBrowser(text, languageCode);
  }
  if (body?.use_browser_tts) {
    return speakInBrowser(text, languageCode);
  }
  return false;
}
