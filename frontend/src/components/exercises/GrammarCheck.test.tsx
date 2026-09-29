import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { GrammarCheck } from "./GrammarCheck";
import type { Exercise } from "@lingo/shared/api/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// GrammarCheck has TWO genuinely different authored modes (see the
// component's own header comment) and both ship in real content:
//
// 1. Closed-choice: prs.a1.unit01.lesson01.exercise07.rtl_direction
//    (overlays/en-prs/a1_unit01.yaml: options ["yes", "no"],
//    accepted_answers [{value: "yes", status: correct}]) — renders
//    selectable options, submits the option string.
// 2. Open free-text: fr.a1.unit01.lesson01.exercise03.choose_polite_pronoun
//    (overlays/en-fr/a1_unit01.yaml: accepted_answers ["vous"]) — renders
//    a text input, submits the trimmed typed string. grammar_check is in
//    the backend's FREE_TEXT_EXERCISE_TYPES (app/review/grading.py), so
//    this mode's payload must be a plain string for typo tolerance to
//    apply.
const optionsMode: Exercise = {
  id: "ex-rtl-direction",
  type: "grammar_check",
  order: 7,
  prompt: {
    text_blocks: [
      {
        text: "Does Dari run from right to left?",
        language_code: "en",
        direction: "ltr",
      },
    ],
    options: ["yes", "no"],
    answer_language_code: "en",
  },
};

const freeTextMode: Exercise = {
  id: "ex-choose-polite-pronoun",
  type: "grammar_check",
  order: 3,
  prompt: {
    text_blocks: [
      {
        text: "Comment allez-___ ?",
        language_code: "fr",
        direction: "ltr",
      },
    ],
    answer_language_code: "fr",
  },
};

describe("GrammarCheck answer payload", () => {
  it("options mode: renders the authored options and submits the selected option string", () => {
    const onAnswer = vi.fn();
    render(<GrammarCheck exercise={optionsMode} onAnswer={onAnswer} disabled={false} />);

    // Historical bug guard (see component comment): this component used to
    // ignore `options` entirely and always render a free-text input,
    // leaving closed yes/no questions with no visible choices. The options
    // must actually be on screen, and no text input should be.
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();

    const check = screen.getByRole("button", { name: "common.check" });
    expect(check).toBeDisabled();

    fireEvent.click(screen.getByRole("radio", { name: "yes" }));
    expect(check).toBeEnabled();
    fireEvent.click(check);

    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer.mock.calls[0][0]).toBe("yes");
  });

  it("free-text mode: submits the typed answer as a trimmed plain string", () => {
    const onAnswer = vi.fn();
    render(<GrammarCheck exercise={freeTextMode} onAnswer={onAnswer} disabled={false} />);

    const check = screen.getByRole("button", { name: "common.check" });
    expect(check).toBeDisabled(); // empty input

    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "  vous " } });

    expect(check).toBeEnabled();
    fireEvent.click(check);

    expect(onAnswer).toHaveBeenCalledTimes(1);
    const payload = onAnswer.mock.calls[0][0];
    // Must be a plain trimmed string — grade_answer() normalizes and
    // compares free text; a non-string payload would bypass typo
    // tolerance entirely.
    expect(payload).toBe("vous");
  });
});
