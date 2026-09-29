import { describe, expect, it } from "vitest";
import {
  MAX_RECORDING_MS,
  NO_SPEECH_TIMEOUT_MS,
  SILENCE_STOP_MS,
  initialVoiceActivityState,
  rmsToLevel,
  stepVoiceActivity,
} from "./voiceActivity";

const LOUD = 0.1;
const QUIET = 0.001;

function run(samples: Array<[number, number]>) {
  let state = initialVoiceActivityState(0);
  let action = "none";
  for (const [nowMs, rms] of samples) {
    const r = stepVoiceActivity(state, { rms, nowMs });
    state = r.state;
    action = r.action;
    if (action !== "none") return { action, at: nowMs };
  }
  return { action, at: -1 };
}

describe("stepVoiceActivity", () => {
  it("stops after silence following speech", () => {
    const samples: Array<[number, number]> = [];
    for (let t = 0; t <= 1000; t += 100) samples.push([t, LOUD]);
    for (let t = 1100; t <= 4000; t += 100) samples.push([t, QUIET]);
    const r = run(samples);
    expect(r.action).toBe("stop");
    expect(r.at).toBe(1000 + SILENCE_STOP_MS);
  });

  it("does not stop on brief pauses shorter than the silence window", () => {
    const samples: Array<[number, number]> = [];
    for (let t = 0; t <= 4000; t += 100) {
      // 1.0 s pause between 0.5 s bursts of speech
      const inBurst = t % 1500 < 500;
      samples.push([t, inBurst ? LOUD : QUIET]);
    }
    expect(run(samples).action).toBe("none");
  });

  it("reports no_speech when nothing is heard for the timeout", () => {
    const samples: Array<[number, number]> = [];
    for (let t = 0; t <= 8000; t += 100) samples.push([t, QUIET]);
    const r = run(samples);
    expect(r.action).toBe("no_speech");
    expect(r.at).toBe(NO_SPEECH_TIMEOUT_MS);
  });

  it("does not time out silence before speech starts prematurely", () => {
    const r = run([[NO_SPEECH_TIMEOUT_MS - 100, QUIET]]);
    expect(r.action).toBe("none");
  });

  it("caps continuous speech at the max duration", () => {
    const samples: Array<[number, number]> = [];
    for (let t = 0; t <= 15000; t += 100) samples.push([t, LOUD]);
    const r = run(samples);
    expect(r.action).toBe("max");
    expect(r.at).toBe(MAX_RECORDING_MS);
  });
});

describe("rmsToLevel", () => {
  it("clamps to 0..1", () => {
    expect(rmsToLevel(-1)).toBe(0);
    expect(rmsToLevel(5)).toBe(1);
    expect(rmsToLevel(0.05)).toBeGreaterThan(0);
  });
});
