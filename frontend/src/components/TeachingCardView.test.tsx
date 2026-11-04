import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { TeachingCard } from "@lingo/shared/api/types";
import { languageDirection, sourceTextDirection } from "@lingo/shared/lib/scripts";
import { TeachingCardView } from "./TeachingCardView";
import { AnswerFeedbackExtras } from "./AnswerFeedbackExtras";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "en" } }),
}));
vi.mock("../api/tts", () => ({ speak: vi.fn().mockResolvedValue(true) }));

const pl = { text: "Gdzie jest bank?", language_code: "pl", direction: "ltr" as const };
const gloss = (code: string, text: string) => ({ text, language_code: code, direction: "ltr" as const });

function card(code: string): TeachingCard {
  return {
    kind: "grammar_note",
    text_blocks: [pl, gloss(code, "gloss")],
    note: "NOTE-" + code,
  };
}

describe("language direction helpers", () => {
  it("marks ar/fa/prs/he/ur rtl and everything else ltr", () => {
    for (const c of ["ar", "fa", "prs", "he", "ur", "ar-EG"]) expect(languageDirection(c)).toBe("rtl");
    for (const c of ["en", "pl", "hi", "de", ""]) expect(languageDirection(c)).toBe("ltr");
  });

  it("takes the direction from the non-target gloss block, auto when none", () => {
    expect(sourceTextDirection([pl, gloss("fa", "x")])).toBe("rtl");
    expect(sourceTextDirection([gloss("ar", "x")], "pl")).toBe("rtl");
    expect(sourceTextDirection([pl])).toBe("auto");
    expect(sourceTextDirection([], "pl")).toBe("auto");
    expect(sourceTextDirection(undefined)).toBe("auto");
  });
});

describe("TeachingCardView note direction", () => {
  it.each([
    ["ar", "rtl"],
    ["fa", "rtl"],
    ["prs", "rtl"],
    ["he", "rtl"],
    ["ur", "rtl"],
    ["en", "ltr"],
    ["de", "ltr"],
  ])("note for %s gloss gets dir=%s", (code, dir) => {
    render(<TeachingCardView card={card(code)} />);
    expect(screen.getByText("NOTE-" + code).closest("p")).toHaveAttribute("dir", dir);
  });
});

describe("AnswerFeedbackExtras why direction", () => {
  it("uses the gloss block language, not dir=auto", () => {
    const prompt = {
      text_blocks: [pl, gloss("fa", "x")],
      answer_language_code: "pl",
      explanation: "WHY",
    };
    render(
      <AnswerFeedbackExtras
        result={{ correct: false, result: "incorrect", correct_response: "bank" }}
        prompt={prompt}
      />,
    );
    expect(screen.getByText("WHY")).toHaveAttribute("dir", "rtl");
  });
});
