import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DialogueResponse } from "./DialogueResponse";
import type { Exercise } from "@lingo/shared/api/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// VoiceCaptureControls (rendered only for speak_response) wraps
// MediaRecorder/Worker plumbing that doesn't exist in jsdom — replace it
// with a stub that lets the test inject a transcript the way the real
// mic flow does (onTranscript feeds the same controlled input value).
vi.mock("../VoiceCaptureControls", () => ({
  VoiceCaptureControls: ({ onTranscript }: { onTranscript: (text: string) => void }) => (
    <button
      type="button"
      onClick={() => onTranscript("Goed, dank je. En met jou?")}
    >
      stub-transcribe
    </button>
  ),
}));

// Real authored content: nl.a1.unit01.lesson02.exercise06.reply_informal
// (docs/content/realizations/nl/a1_unit01_greetings.yaml + its
// overlays/en-nl/a1_unit01.yaml entry) — dialogue bubble "Hoi! Hoe gaat
// het met je?", accepted_answers include "Goed, dank je. En met jou?".
// dialogue_response and speak_response are both in the backend's
// FREE_TEXT_EXERCISE_TYPES (app/review/grading.py): the payload must be
// a plain trimmed string, whether typed or transcribed.
const dialogueResponse: Exercise = {
  id: "ex-reply-informal",
  type: "dialogue_response",
  order: 6,
  prompt: {
    text_blocks: [
      { text: "Hoi! Hoe gaat het met je?", language_code: "nl", direction: "ltr" },
    ],
    answer_language_code: "nl",
  },
};

const speakResponse: Exercise = {
  ...dialogueResponse,
  id: "ex-reply-informal-spoken",
  type: "speak_response",
};

describe("DialogueResponse answer payload", () => {
  it("dialogue_response: submits the typed reply as a trimmed plain string, no mic controls", () => {
    const onAnswer = vi.fn();
    render(<DialogueResponse exercise={dialogueResponse} onAnswer={onAnswer} disabled={false} />);

    // The mic toggle is speak_response-only — its non-speaking sibling
    // must stay typed-only (see component comment).
    expect(screen.queryByText("stub-transcribe")).not.toBeInTheDocument();

    const respond = screen.getByRole("button", { name: "exercise.respond" });
    expect(respond).toBeDisabled(); // empty input

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "  Goed, dank je. En met jou? " },
    });
    expect(respond).toBeEnabled();
    fireEvent.click(respond);

    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer.mock.calls[0][0]).toBe("Goed, dank je. En met jou?");
  });

  it("speak_response: a transcript flows into the same trimmed-string payload as typing", () => {
    const onAnswer = vi.fn();
    render(<DialogueResponse exercise={speakResponse} onAnswer={onAnswer} disabled={false} />);

    // Mic controls ARE offered for the speaking variant...
    fireEvent.click(screen.getByText("stub-transcribe"));
    // ...and the transcript lands in the shared text input, so the learner
    // can see/correct it before submitting.
    expect(screen.getByRole("textbox")).toHaveValue("Goed, dank je. En met jou?");

    fireEvent.click(screen.getByRole("button", { name: "exercise.respond" }));

    expect(onAnswer).toHaveBeenCalledTimes(1);
    // STT transcripts grade through the exact same free-text string path
    // as typed answers (FREE_TEXT_EXERCISE_TYPES includes speak_response).
    expect(onAnswer.mock.calls[0][0]).toBe("Goed, dank je. En met jou?");
  });
});
