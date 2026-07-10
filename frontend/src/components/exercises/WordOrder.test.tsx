import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WordOrder } from "./WordOrder";
import type { Exercise } from "@lingo/shared/api/types";

// WordOrder (and SpeakButton inside TextBlockList) use useTranslation;
// a stable key-echoing t() is all the tests need.
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// Real authored content shape: nl.a1.unit01.lesson01.exercise06.
// listen_order_informal (docs/content/realizations/nl/
// a1_unit01_greetings.yaml) — word_bank is deliberately scrambled
// relative to the correct sentence "Ben jij nieuw hier", so a payload
// that merely echoed word_bank order would be caught below.
const exercise: Exercise = {
  id: "ex-order-informal",
  type: "word_order",
  order: 6,
  prompt: {
    text_blocks: [
      {
        text: "Put the words in order to ask informally, 'Are you new here?'",
        language_code: "en",
        direction: "ltr",
      },
    ],
    word_bank: ["nieuw", "jij", "hier", "Ben"],
    answer_language_code: "nl",
  },
};

describe("WordOrder answer payload", () => {
  it("submits the word_bank tokens as an ARRAY in click order (after corrections), never a joined string", () => {
    const onAnswer = vi.fn();
    render(<WordOrder exercise={exercise} onAnswer={onAnswer} disabled={false} />);

    const check = screen.getByRole("button", { name: "common.check" });
    expect(check).toBeDisabled(); // nothing chosen yet

    // Build "Ben jij nieuw hier" tile by tile, including one mis-click
    // that gets unpicked — the payload must reflect the FINAL assembled
    // order, exactly as the learner sees it.
    fireEvent.click(screen.getByRole("button", { name: "Ben" }));
    fireEvent.click(screen.getByRole("button", { name: "hier" })); // mis-click (bank)
    fireEvent.click(screen.getByRole("button", { name: "jij" }));
    fireEvent.click(screen.getByRole("button", { name: "hier" })); // unpick from answer row
    fireEvent.click(screen.getByRole("button", { name: "nieuw" }));
    fireEvent.click(screen.getByRole("button", { name: "hier" })); // re-pick, now last

    expect(check).toBeEnabled();
    fireEvent.click(check);

    expect(onAnswer).toHaveBeenCalledTimes(1);
    const payload = onAnswer.mock.calls[0][0];

    // Contract locked down here (see CLAUDE.md's word_order/listen_order
    // footgun, found live 2026-07-07): the frontend submits a LIST of
    // word_bank tokens in click order — the backend's
    // canonical_order_tokens() canonicalizes both list- and string-authored
    // accepted_answers against exactly this list shape. Submitting a
    // space-joined string (or anything else) here would silently re-break
    // grading for the list-authored exercises and every Endless
    // Practice-generated word_order item.
    expect(typeof payload).not.toBe("string");
    expect(Array.isArray(payload)).toBe(true);
    expect(payload).toEqual(["Ben", "jij", "nieuw", "hier"]);
    // Every submitted token must be a verbatim word_bank tile, not a
    // re-tokenized/joined transformation of them.
    for (const token of payload as string[]) {
      expect(exercise.prompt.word_bank).toContain(token);
    }
  });
});
