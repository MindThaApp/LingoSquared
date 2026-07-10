import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FillInBlank } from "./FillInBlank";
import type { Exercise } from "@lingo/shared/api/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// Real authored content: nl.a1.unit01.lesson04.exercise06.complete_country
// (docs/content/realizations/nl/a1_unit01_greetings.yaml + its
// overlays/en-nl/a1_unit01.yaml entry) — prompt "Ik kom ___ België.",
// accepted_answers [{value: uit}, {value: Uit}]. The payload is the typed
// blank as a trimmed plain string. Note the backend deliberately does NOT
// bucket fill_in_blank into FREE_TEXT_EXERCISE_TYPES by name alone (see
// the comment above that set in app/review/grading.py) — the string shape
// here is still the contract for string-authored answers like this one.
const exercise: Exercise = {
  id: "ex-complete-country",
  type: "fill_in_blank",
  order: 6,
  prompt: {
    text_blocks: [
      { text: "Ik kom ___ België.", language_code: "nl", direction: "ltr" },
    ],
    answer_language_code: "nl",
  },
};

describe("FillInBlank answer payload", () => {
  it("submits the typed blank as a trimmed plain string", () => {
    const onAnswer = vi.fn();
    render(<FillInBlank exercise={exercise} onAnswer={onAnswer} disabled={false} />);

    const check = screen.getByRole("button", { name: "common.check" });
    expect(check).toBeDisabled(); // empty input

    // Whitespace-only input must not enable submission either.
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "   " } });
    expect(check).toBeDisabled();

    fireEvent.change(screen.getByRole("textbox"), { target: { value: " uit " } });
    expect(check).toBeEnabled();
    fireEvent.click(check);

    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer.mock.calls[0][0]).toBe("uit");
  });
});
