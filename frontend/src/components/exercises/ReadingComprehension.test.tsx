import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ReadingComprehension } from "./ReadingComprehension";
import type { Exercise } from "@lingo/shared/api/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// Real authored content: nl.a1.unit20.lesson05.exercise01.read_size
// (docs/content/realizations/nl/a1_unit20_clothing.yaml + its
// overlays/en-nl/a1_unit20.yaml entry: correct_option "M",
// distractors [S, L, XL], accepted_answers [{value: M, status: correct}]).
// Reading passage in the target language, English question, option-string
// answer — graded as a plain string by the backend's choice-type path.
const exercise: Exercise = {
  id: "ex-read-size",
  type: "reading_comprehension",
  order: 1,
  prompt: {
    text_blocks: [
      {
        text: "Kassabon — Winterjas: maat M, negentig euro. De jas past goed en is warm.",
        language_code: "nl",
        direction: "ltr",
      },
      {
        text: "What size is the coat?",
        language_code: "en",
        direction: "ltr",
      },
    ],
    options: ["M", "S", "L", "XL"],
    answer_language_code: "en",
  },
};

describe("ReadingComprehension answer payload", () => {
  it("submits the selected option string verbatim", () => {
    const onAnswer = vi.fn();
    render(<ReadingComprehension exercise={exercise} onAnswer={onAnswer} disabled={false} />);

    const check = screen.getByRole("button", { name: "common.check" });
    expect(check).toBeDisabled(); // nothing selected yet

    fireEvent.click(screen.getByRole("button", { name: "M" }));
    expect(check).toBeEnabled();
    fireEvent.click(check);

    expect(onAnswer).toHaveBeenCalledTimes(1);
    // The backend compares this against the authored option text
    // ("M") as a plain string — nothing but the verbatim option works.
    expect(onAnswer.mock.calls[0][0]).toBe("M");
  });
});
