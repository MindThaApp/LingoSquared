import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MatchingPairs } from "./MatchingPairs";
import type { Exercise } from "@lingo/shared/api/types";

// Components under this tree pull in useTranslation (via SpeakButton);
// tests don't need a real i18n instance, just a stable t().
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// Real authored content shape: nl.a1.unit01.lesson01.exercise04.match_register
// (docs/content/realizations/nl/a1_unit01_greetings.yaml). Its overlay's
// accepted_answers is an ARRAY of {left, right} pair objects:
//   - value: [{left: "jij / je", right: informeel},
//             {left: u, right: "formeel of beleefd"}]
// That array-of-objects shape is the contract this component must submit.
const exercise: Exercise = {
  id: "ex-match-register",
  type: "matching_pairs",
  order: 4,
  prompt: {
    text_blocks: [
      {
        text: "Match each Dutch form with its register.",
        language_code: "en",
        direction: "ltr",
      },
    ],
    pairs: [
      { left: "jij / je", right: "informeel" },
      { left: "u", right: "formeel of beleefd" },
    ],
    answer_language_code: "nl",
  },
};

describe("MatchingPairs answer payload", () => {
  it("submits an array of {left, right} objects in the exercise's own pair order, never a flat record", () => {
    const onAnswer = vi.fn();
    render(<MatchingPairs exercise={exercise} onAnswer={onAnswer} disabled={false} />);

    const check = screen.getByRole("button", { name: "common.check" });
    expect(check).toBeDisabled(); // nothing matched yet

    // Deliberately match the SECOND pair first: the submitted payload must
    // still come out in the exercise's authored pair order, not click order.
    fireEvent.click(screen.getByRole("button", { name: "u" }));
    fireEvent.click(screen.getByRole("button", { name: "formeel of beleefd" }));
    fireEvent.click(screen.getByRole("button", { name: "jij / je" }));
    fireEvent.click(screen.getByRole("button", { name: "informeel" }));

    expect(check).toBeEnabled();
    fireEvent.click(check);

    expect(onAnswer).toHaveBeenCalledTimes(1);
    const payload = onAnswer.mock.calls[0][0];

    // This is the exact historical bug (found live 2026-07-05, see
    // CLAUDE.md footguns): the component used to submit its internal flat
    // Record<left, right> ({"jij / je": "informeel", u: "..."}), which
    // never compared equal to the authored array-of-objects
    // accepted_answers — every matching_pairs exercise in every language
    // graded incorrect regardless of what the learner picked. A flat
    // record fails this assertion; only the authored array shape passes.
    expect(Array.isArray(payload)).toBe(true);
    expect(payload).toEqual([
      { left: "jij / je", right: "informeel" },
      { left: "u", right: "formeel of beleefd" },
    ]);
  });
});
