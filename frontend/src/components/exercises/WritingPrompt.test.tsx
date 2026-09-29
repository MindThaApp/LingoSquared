import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WritingPrompt } from "./WritingPrompt";
import type { Exercise } from "@lingo/shared/api/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// Real authored content: nl.a1.unit01.lesson02.exercise08.
// write_formal_exchange (overlays/en-nl/a1_unit01.yaml) — instruction
// "Write a formal Dutch question asking how someone is, followed by a
// suitable formal reply", accepted_answers include "Hoe gaat het met u?
// Goed, dank u.". writing_prompt is in FREE_TEXT_EXERCISE_TYPES
// (app/review/grading.py): payload is the textarea content as a trimmed
// plain string.
const exercise: Exercise = {
  id: "ex-write-formal-exchange",
  type: "writing_prompt",
  order: 8,
  prompt: {
    text_blocks: [
      {
        text: "Write a formal Dutch question asking how someone is, followed by a suitable formal reply.",
        language_code: "en",
        direction: "ltr",
      },
    ],
    answer_language_code: "nl",
  },
};

describe("WritingPrompt answer payload", () => {
  it("submits the multi-sentence textarea content as a trimmed plain string", () => {
    const onAnswer = vi.fn();
    render(<WritingPrompt exercise={exercise} onAnswer={onAnswer} disabled={false} />);

    const submit = screen.getByRole("button", { name: "common.submit" });
    expect(submit).toBeDisabled(); // empty textarea

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: " Hoe gaat het met u? Goed, dank u. " },
    });
    expect(submit).toBeEnabled();
    fireEvent.click(submit);

    expect(onAnswer).toHaveBeenCalledTimes(1);
    // Internal punctuation/spacing must survive verbatim (only the outer
    // trim is the component's job — normalization is grade_answer()'s).
    expect(onAnswer.mock.calls[0][0]).toBe("Hoe gaat het met u? Goed, dank u.");
  });

  it("Enter inserts a newline (does not submit); Cmd/Ctrl+Enter submits", () => {
    const onAnswer = vi.fn();
    render(<WritingPrompt exercise={exercise} onAnswer={onAnswer} disabled={false} />);
    const box = screen.getByRole("textbox");
    fireEvent.change(box, { target: { value: "Goed, dank u." } });

    fireEvent.keyDown(box, { key: "Enter" });
    expect(onAnswer).not.toHaveBeenCalled();

    fireEvent.keyDown(box, { key: "Enter", ctrlKey: true });
    expect(onAnswer).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(box, { key: "Enter", metaKey: true });
    expect(onAnswer).toHaveBeenCalledTimes(2);
    expect(onAnswer.mock.calls[1][0]).toBe("Goed, dank u.");
    expect(screen.getByText("exercise.writing_submit_hint")).toBeInTheDocument();
  });
});
