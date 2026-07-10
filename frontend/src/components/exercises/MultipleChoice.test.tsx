import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MultipleChoice } from "./MultipleChoice";
import type { Exercise } from "@lingo/shared/api/types";

// SpeakButton (rendered for listen-type prompts) pulls in useTranslation;
// tests only need a stable key-echoing t().
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// Real authored content: nl.a1.unit01.lesson01.exercise01.choose_informal
// (docs/content/realizations/nl/a1_unit01_greetings.yaml + its
// overlays/en-nl/a1_unit01.yaml entry: correct_option "jij / je",
// distractors [u, "jij / u", "je / u"]). The payload contract is the
// selected option STRING, verbatim — grade()'s choice-type path
// (CHOICE_EXERCISE_TYPES in app/review/grading.py) compares it as plain
// normalized text against accepted_answers' string values.
const multipleChoice: Exercise = {
  id: "ex-choose-informal",
  type: "multiple_choice",
  order: 1,
  prompt: {
    text_blocks: [
      {
        text: "Which option contains the two informal singular forms of 'you'?",
        language_code: "en",
        direction: "ltr",
      },
    ],
    options: ["jij / je", "u", "jij / u", "je / u"],
    answer_language_code: "nl",
  },
};

// Real authored content: nl.a1.unit01.lesson01.exercise03.listen_formal —
// the listen_select variant routed to this same component. Compiled prompt
// carries audio_text/audio_language_code/media_asset_key for the hidden
// spoken phrase; the answer payload contract is identical (option string).
const listenSelect: Exercise = {
  id: "ex-listen-formal",
  type: "listen_select",
  order: 3,
  prompt: {
    text_blocks: [
      {
        text: "Listen and choose the situation that fits the question.",
        language_code: "en",
        direction: "ltr",
      },
    ],
    options: [
      "A formally addressed person is asked whether they are new here.",
      "A peer is asked whether they are new here.",
      "A formally addressed person is asked whether they live here.",
      "A formally addressed person is asked whether they are from here.",
    ],
    audio_text: "Bent u nieuw hier?",
    audio_language_code: "nl",
    media_asset_key: "nl.a1.audio.bent_u_nieuw_hier.formal.01",
    answer_language_code: "en",
  },
};

describe("MultipleChoice answer payload", () => {
  it("submits the selected option string verbatim (last selection wins)", () => {
    const onAnswer = vi.fn();
    render(<MultipleChoice exercise={multipleChoice} onAnswer={onAnswer} disabled={false} />);

    const check = screen.getByRole("button", { name: "common.check" });
    expect(check).toBeDisabled(); // nothing selected yet

    // Select a distractor first, then change to the correct option — the
    // payload must be the FINAL selection, not the first click.
    fireEvent.click(screen.getByRole("button", { name: "u" }));
    fireEvent.click(screen.getByRole("button", { name: "jij / je" }));

    expect(check).toBeEnabled();
    fireEvent.click(check);

    expect(onAnswer).toHaveBeenCalledTimes(1);
    const payload = onAnswer.mock.calls[0][0];
    // Choice types are graded by plain string comparison against the
    // authored option text — any transformation (index, object, array)
    // would grade incorrect for every learner.
    expect(payload).toBe("jij / je");
  });

  it("listen_select: renders the audio prompt and submits the same option-string shape", () => {
    const onAnswer = vi.fn();
    const { container } = render(
      <MultipleChoice exercise={listenSelect} onAnswer={onAnswer} disabled={false} />
    );

    // The hidden-phrase speak button must actually be offered — a
    // listen_select with no way to listen is unanswerable. Scoped to the
    // audio-prompt row because TextBlockList renders its own per-block
    // speak buttons too.
    expect(container.querySelector(".exercise-audio-prompt .speak-button")).not.toBeNull();

    fireEvent.click(
      screen.getByRole("button", {
        name: "A formally addressed person is asked whether they are new here.",
      })
    );
    fireEvent.click(screen.getByRole("button", { name: "common.check" }));

    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer.mock.calls[0][0]).toBe(
      "A formally addressed person is asked whether they are new here."
    );
  });

  it("does not submit when disabled", () => {
    const onAnswer = vi.fn();
    render(<MultipleChoice exercise={multipleChoice} onAnswer={onAnswer} disabled={true} />);
    const check = screen.getByRole("button", { name: "common.check" });
    expect(check).toBeDisabled();
    fireEvent.click(check);
    expect(onAnswer).not.toHaveBeenCalled();
  });
});
