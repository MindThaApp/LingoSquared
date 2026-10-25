import { getFeedbackCues } from "./feedbackPreferences";

export type CueKind = "correct" | "incorrect";

const TONES: Record<CueKind, Array<[number, number]>> = {
  // [frequency Hz, duration s]
  correct: [[660, 0.08], [880, 0.12]],
  incorrect: [[220, 0.18]],
};
const VIBRATION: Record<CueKind, number | number[]> = {
  correct: 30,
  incorrect: [60, 40, 60],
};

let ctx: AudioContext | null = null;

function beep(kind: CueKind): void {
  const Ctor: typeof AudioContext | undefined =
    typeof window === "undefined"
      ? undefined
      : window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return;
  ctx ??= new Ctor();
  if (ctx.state === "suspended") void ctx.resume();
  let at = ctx.currentTime;
  for (const [freq, dur] of TONES[kind]) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.value = freq;
    osc.type = "sine";
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(0.15, at + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + dur);
    osc.connect(gain).connect(ctx.destination);
    osc.start(at);
    osc.stop(at + dur + 0.02);
    at += dur;
  }
}

/** Plays the correct/wrong cue unless the learner muted cues. Never throws. */
export function playAnswerCue(kind: CueKind): void {
  if (!getFeedbackCues()) return;
  try {
    if (typeof navigator !== "undefined" && typeof navigator.vibrate === "function") {
      navigator.vibrate(VIBRATION[kind]);
    }
  } catch {
    // ignore
  }
  try {
    beep(kind);
  } catch {
    // ignore
  }
}
