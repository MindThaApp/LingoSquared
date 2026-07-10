import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Flashcard } from "./Flashcard";
import type { Exercise } from "@lingo/shared/api/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// Real seeded content shape (backend/app/content/seed.py): front
// text_blocks carry the target-language word, back_text_blocks the gloss
// — e.g. {text_blocks: [سلام (prs)], back_text_blocks: [hello (en)]}.
// The payload contract is the STRICTEST in the whole exercise set:
// grade() in app/api/router.py 422s ("invalid_flashcard_response") on
// anything that is not exactly the string "known" or "unknown".
const exercise: Exercise = {
  id: "ex-flashcard-salam",
  type: "flashcard",
  order: 3,
  prompt: {
    text_blocks: [{ text: "سلام", language_code: "prs", direction: "rtl" }],
    back_text_blocks: [{ text: "hello", language_code: "en", direction: "ltr" }],
  },
};

describe("Flashcard answer payload", () => {
  it("hides the back until flipped, then submits exactly 'known' for Got it", () => {
    const onAnswer = vi.fn();
    render(<Flashcard exercise={exercise} onAnswer={onAnswer} disabled={false} />);

    // Back face must not be visible before the flip — otherwise the
    // self-report is meaningless.
    expect(screen.queryByText("hello")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "exercise.show_answer" }));
    expect(screen.getByText("hello")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "exercise.got_it" }));

    expect(onAnswer).toHaveBeenCalledTimes(1);
    // Anything but the literal string "known"/"unknown" is a 422 on the
    // backend (invalid_flashcard_response) — this is a hard contract.
    expect(onAnswer.mock.calls[0][0]).toBe("known");
  });

  it("submits exactly 'unknown' for Didn't know", () => {
    const onAnswer = vi.fn();
    render(<Flashcard exercise={exercise} onAnswer={onAnswer} disabled={false} />);

    fireEvent.click(screen.getByRole("button", { name: "exercise.show_answer" }));
    fireEvent.click(screen.getByRole("button", { name: "exercise.didnt_know" }));

    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer.mock.calls[0][0]).toBe("unknown");
  });
});
