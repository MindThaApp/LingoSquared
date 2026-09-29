// Pure voice-activity state machine for mic auto-stop. No timers, no Web
// Audio — the caller feeds it one RMS sample at a time (with a timestamp) and
// acts on the returned action. Kept pure so the timing rules are unit-tested.

// RMS (0..1, time-domain float samples) at or above this counts as speech.
export const SPEECH_RMS_THRESHOLD = 0.02;
// Silence after speech has started that ends the recording.
export const SILENCE_STOP_MS = 1200;
// Hard cap on a single recording.
export const MAX_RECORDING_MS = 12000;
// Give up if nothing speech-like is heard within this long.
export const NO_SPEECH_TIMEOUT_MS = 6000;

export interface VoiceActivityState {
  startedAtMs: number;
  speechStarted: boolean;
  lastVoiceAtMs: number | null;
}

export type VoiceActivityAction = "none" | "stop" | "no_speech" | "max";

export function initialVoiceActivityState(nowMs: number): VoiceActivityState {
  return { startedAtMs: nowMs, speechStarted: false, lastVoiceAtMs: null };
}

export function stepVoiceActivity(
  state: VoiceActivityState,
  sample: { rms: number; nowMs: number },
): { state: VoiceActivityState; action: VoiceActivityAction } {
  const { rms, nowMs } = sample;
  let next = state;
  if (rms >= SPEECH_RMS_THRESHOLD) {
    next = { ...state, speechStarted: true, lastVoiceAtMs: nowMs };
  }
  const elapsed = nowMs - next.startedAtMs;
  if (elapsed >= MAX_RECORDING_MS) return { state: next, action: "max" };
  if (!next.speechStarted) {
    return { state: next, action: elapsed >= NO_SPEECH_TIMEOUT_MS ? "no_speech" : "none" };
  }
  if (next.lastVoiceAtMs !== null && nowMs - next.lastVoiceAtMs >= SILENCE_STOP_MS) {
    return { state: next, action: "stop" };
  }
  return { state: next, action: "none" };
}

// Map RMS to a 0..1 meter level (speech RMS is typically 0.02-0.2), quantized
// to 5% steps so React re-renders only on visible change.
export function rmsToLevel(rms: number): number {
  const scaled = Math.min(1, Math.max(0, rms) * 6);
  return Math.round(scaled * 20) / 20;
}
