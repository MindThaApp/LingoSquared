import { afterEach, describe, expect, it, vi } from "vitest";
import { playAnswerCue } from "./answerCue";
import { setFeedbackCues } from "./feedbackPreferences";

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe("playAnswerCue", () => {
  it("vibrates when cues are on", () => {
    const vibrate = vi.fn();
    Object.defineProperty(navigator, "vibrate", { value: vibrate, configurable: true });
    playAnswerCue("incorrect");
    expect(vibrate).toHaveBeenCalledWith([60, 40, 60]);
  });

  it("does nothing when muted", () => {
    const vibrate = vi.fn();
    Object.defineProperty(navigator, "vibrate", { value: vibrate, configurable: true });
    setFeedbackCues(false);
    playAnswerCue("correct");
    expect(vibrate).not.toHaveBeenCalled();
  });

  it("never throws without vibrate / WebAudio support", () => {
    Object.defineProperty(navigator, "vibrate", { value: undefined, configurable: true });
    expect(() => playAnswerCue("correct")).not.toThrow();
  });
});
