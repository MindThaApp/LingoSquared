import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SpeakRepeat } from "./SpeakRepeat";
import type { Exercise } from "@lingo/shared/api/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// VoiceCaptureControls wraps MediaRecorder/Worker plumbing jsdom doesn't
// have — stub it with a transcript-injecting button, same as the real
// mic flow's onTranscript wiring.
vi.mock("../VoiceCaptureControls", () => ({
  VoiceCaptureControls: ({ onTranscript }: { onTranscript: (text: string) => void }) => (
    <button type="button" onClick={() => onTranscript("Vous êtes. Un atelier.")}>
      stub-transcribe
    </button>
  ),
}));

// Real authored content: fr.a1.unit01.lesson03's speak_repeat liaison
// drill (cited in SpeakRepeat.tsx's own header comment as
// exercise07_read_liaison, accepted answer "Vous êtes. Un atelier.").
// speak_repeat has genuine accepted_answers and is in the backend's
// FREE_TEXT_EXERCISE_TYPES (app/review/grading.py) — docs/CONTRACT.md
// once wrongly claimed it "has no checkable answer" (fixed 2026-07-06);
// this test pins the real contract: a plain trimmed string.
const exercise: Exercise = {
  id: "ex-read-liaison",
  type: "speak_repeat",
  order: 7,
  prompt: {
    text_blocks: [
      { text: "Vous êtes. Un atelier.", language_code: "fr", direction: "ltr" },
    ],
    answer_language_code: "fr",
  },
};

describe("SpeakRepeat answer payload", () => {
  it("submits the transcript as a trimmed plain string via the shared input", () => {
    const onAnswer = vi.fn();
    render(<SpeakRepeat exercise={exercise} onAnswer={onAnswer} disabled={false} />);

    const check = screen.getByRole("button", { name: "common.check" });
    expect(check).toBeDisabled(); // nothing transcribed or typed yet

    fireEvent.click(screen.getByText("stub-transcribe"));
    // Transcript lands in the visible input so the learner can correct it.
    expect(screen.getByRole("textbox")).toHaveValue("Vous êtes. Un atelier.");

    expect(check).toBeEnabled();
    fireEvent.click(check);

    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer.mock.calls[0][0]).toBe("Vous êtes. Un atelier.");
  });

  it("typed fallback submits the same string shape", () => {
    const onAnswer = vi.fn();
    render(<SpeakRepeat exercise={exercise} onAnswer={onAnswer} disabled={false} />);

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: " Vous êtes. Un atelier. " },
    });
    fireEvent.click(screen.getByRole("button", { name: "common.check" }));

    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer.mock.calls[0][0]).toBe("Vous êtes. Un atelier.");
  });
});
