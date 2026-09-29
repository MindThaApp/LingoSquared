import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { TextBlock } from "@lingo/shared/api/types";
import { TextBlockView, shouldShowSpeaker } from "./TextBlock";
import { ExerciseRenderer } from "./exercises/ExerciseRenderer";
import { TargetLanguageContext } from "./targetLanguageContext";

let uiLang = "en";
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: uiLang } }),
}));
vi.mock("../api/tts", () => ({ speak: vi.fn() }));

const nl: TextBlock = { text: "Hallo", language_code: "nl", direction: "ltr" };
const en: TextBlock = { text: "Hello", language_code: "en", direction: "ltr" };

describe("TextBlock speaker visibility", () => {
  it("shouldShowSpeaker: target language wins over UI language", () => {
    expect(shouldShowSpeaker("en", "en", "en")).toBe(true);
    expect(shouldShowSpeaker("nl", "en", "en")).toBe(false);
    expect(shouldShowSpeaker("nl", "nl-NL", "en")).toBe(true);
  });

  it("shouldShowSpeaker: falls back to hiding UI-language blocks without a target", () => {
    expect(shouldShowSpeaker("en", null, "en")).toBe(false);
    expect(shouldShowSpeaker("nl", null, "en")).toBe(true);
  });

  it("shows the speaker for a UI-language block when it is the target language", () => {
    uiLang = "en";
    render(
      <TargetLanguageContext.Provider value="en">
        <TextBlockView block={en} />
      </TargetLanguageContext.Provider>,
    );
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("hides the speaker on non-target blocks", () => {
    uiLang = "en";
    render(
      <TargetLanguageContext.Provider value="en">
        <TextBlockView block={nl} />
      </TargetLanguageContext.Provider>,
    );
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("keeps the old behaviour without a provider", () => {
    uiLang = "en";
    const { unmount } = render(<TextBlockView block={en} />);
    expect(screen.queryByRole("button")).toBeNull();
    unmount();
    render(<TextBlockView block={nl} />);
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("reverse_translation: page target nl beats answer_language_code en (speaker on nl prompt, not en)", () => {
    uiLang = "en";
    const exercise = {
      id: "e1",
      type: "reverse_translation" as const,
      order: 0,
      prompt: { text_blocks: [nl, en], answer_language_code: "en" },
    };
    render(
      <TargetLanguageContext.Provider value="nl">
        <ExerciseRenderer exercise={exercise} onAnswer={() => {}} disabled={false} />
      </TargetLanguageContext.Provider>,
    );
    const rows = document.querySelectorAll(".text-block-row");
    expect(rows[0].querySelector("button")).not.toBeNull();
    expect(rows[1].querySelector("button")).toBeNull();
  });

  it("falls back to answer_language_code when no page provides a target", () => {
    uiLang = "en";
    const exercise = {
      id: "e2",
      type: "reverse_translation" as const,
      order: 0,
      prompt: { text_blocks: [nl, en], answer_language_code: "en" },
    };
    render(<ExerciseRenderer exercise={exercise} onAnswer={() => {}} disabled={false} />);
    const rows = document.querySelectorAll(".text-block-row");
    expect(rows[0].querySelector("button")).toBeNull();
    expect(rows[1].querySelector("button")).not.toBeNull();
  });
});
