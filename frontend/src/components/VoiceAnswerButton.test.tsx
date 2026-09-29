import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import type { Exercise } from "@lingo/shared/api/types";
import { TargetLanguageContext } from "./targetLanguageContext";
import { FillInBlank } from "./exercises/FillInBlank";
import { voiceAnswerEligible } from "../lib/voiceAnswer";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const mic = vi.hoisted(() => ({ supported: true, blocked: false }));
const speech = vi.hoisted(() => ({
  onTranscript: null as null | ((text: string) => void),
  beginRecording: vi.fn(),
}));

vi.mock("../lib/useMicRecorder", () => ({
  micRecordingSupported: () => mic.supported,
  micPermissionBlocked: () => mic.blocked,
  useMicRecorder: () => ({}),
}));
vi.mock("../lib/useSpeechAnswer", () => ({
  useSpeechAnswer: (_lang: string, onTranscript: (text: string) => void) => {
    speech.onTranscript = onTranscript;
    return {
      status: "idle",
      error: null,
      level: 0,
      words: null,
      beginRecording: speech.beginRecording,
      finishRecording: vi.fn(),
    };
  },
}));

const exercise: Exercise = {
  id: "ex-fib",
  type: "fill_in_blank",
  order: 1,
  prompt: {
    text_blocks: [{ text: "Ik ___ een appel.", language_code: "nl", direction: "ltr" }],
    answer_language_code: "nl",
  },
};

function renderFib(target: string | null = "nl") {
  const onAnswer = vi.fn();
  render(
    <TargetLanguageContext.Provider value={target}>
      <FillInBlank exercise={exercise} onAnswer={onAnswer} disabled={false} />
    </TargetLanguageContext.Provider>,
  );
  return onAnswer;
}

beforeEach(() => {
  mic.supported = true;
  mic.blocked = false;
  speech.onTranscript = null;
  speech.beginRecording.mockClear();
});

describe("voiceAnswerEligible", () => {
  it("requires the answer language to be the target language", () => {
    expect(voiceAnswerEligible("nl", "nl")).toBe(true);
    expect(voiceAnswerEligible("nl", null)).toBe(true);
    expect(voiceAnswerEligible("en", "nl")).toBe(false);
    expect(voiceAnswerEligible(undefined, "nl")).toBe(false);
  });
});

describe("VoiceAnswerButton", () => {
  it("is hidden when mic recording is unsupported", () => {
    mic.supported = false;
    renderFib();
    expect(screen.queryByRole("button", { name: "voice_answer.inline_start" })).toBeNull();
    expect(screen.getByRole("textbox")).toBeEnabled();
  });

  it("is hidden after mic permission was denied", () => {
    mic.blocked = true;
    renderFib();
    expect(screen.queryByRole("button", { name: "voice_answer.inline_start" })).toBeNull();
  });

  it("is hidden when the answer is not in the target language", () => {
    renderFib("en");
    expect(screen.queryByRole("button", { name: "voice_answer.inline_start" })).toBeNull();
  });

  it("starts recording on press", () => {
    renderFib();
    fireEvent.click(screen.getByRole("button", { name: "voice_answer.inline_start" }));
    expect(speech.beginRecording).toHaveBeenCalledTimes(1);
  });

  it("fills the input with the transcript without submitting; sends input_mode spoken on Check", () => {
    const onAnswer = renderFib();
    fireEvent.click(screen.getByRole("button", { name: "voice_answer.inline_start" }));
    act(() => speech.onTranscript!("eet"));
    expect(screen.getByRole("textbox")).toHaveValue("eet");
    expect(onAnswer).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "common.check" }));
    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer).toHaveBeenCalledWith("eet", { inputMode: "spoken" });
  });

  it("typed answers carry no meta argument at all", () => {
    const onAnswer = renderFib();
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "eet" } });
    fireEvent.click(screen.getByRole("button", { name: "common.check" }));
    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer.mock.calls[0]).toEqual(["eet"]);
  });
});
