import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Translation } from "./Translation";
import type { Exercise } from "@lingo/shared/api/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// Real authored content: nl.a1.unit05.lesson01.exercise07.translate_parents
// (docs/content/realizations/nl/a1_unit05_family.yaml) — English prompt
// "parents", accepted answer "ouders". translation is in the backend's
// FREE_TEXT_EXERCISE_TYPES (app/review/grading.py), so the payload must
// be a plain string for grade_answer()'s normalization + distance-1 typo
// tolerance to apply at all.
const translation: Exercise = {
  id: "ex-translate-parents",
  type: "translation",
  order: 7,
  prompt: {
    text_blocks: [{ text: "parents", language_code: "en", direction: "ltr" }],
    answer_language_code: "nl",
  },
};

// Real authored content: nl.a1.unit01.lesson01.exercise08.listen_type_formal
// — the listen_type variant routed through this same component. The hidden
// phrase rides in audio_text/audio_language_code (overlay accepted_answers:
// "Bent u nieuw hier?" and variants); the answer payload contract is the
// same trimmed string.
const listenType: Exercise = {
  id: "ex-listen-type-formal",
  type: "listen_type",
  order: 8,
  prompt: {
    text_blocks: [
      {
        text: "Listen and type the full Dutch question.",
        language_code: "en",
        direction: "ltr",
      },
    ],
    audio_text: "Bent u nieuw hier?",
    audio_language_code: "nl",
    media_asset_key: "nl.a1.audio.bent_u_nieuw_hier.formal.01",
    answer_language_code: "nl",
  },
};

describe("Translation answer payload", () => {
  it("submits the typed answer as a trimmed plain string", () => {
    const onAnswer = vi.fn();
    render(<Translation exercise={translation} onAnswer={onAnswer} disabled={false} />);

    const check = screen.getByRole("button", { name: "common.check" });
    expect(check).toBeDisabled(); // empty input

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "  ouders " } });
    expect(check).toBeEnabled();
    fireEvent.click(check);

    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer.mock.calls[0][0]).toBe("ouders");
  });

  it("listen_type: offers the hidden-phrase audio and submits the same string shape", () => {
    const onAnswer = vi.fn();
    const { container } = render(
      <Translation exercise={listenType} onAnswer={onAnswer} disabled={false} />
    );

    // A listen_type with no way to hear the phrase is unanswerable —
    // scoped to the audio-prompt row because TextBlockList renders its
    // own per-block speak buttons too.
    expect(container.querySelector(".exercise-audio-prompt .speak-button")).not.toBeNull();

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "Bent u nieuw hier?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "common.check" }));

    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer.mock.calls[0][0]).toBe("Bent u nieuw hier?");
  });
});
