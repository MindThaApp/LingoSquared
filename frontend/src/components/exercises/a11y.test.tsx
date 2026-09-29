import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type { Exercise, ExercisePrompt, ExerciseType } from "@lingo/shared/api/types";
import { expectNoSeriousA11yViolations } from "../../test/axe";
import { ExerciseRenderer } from "./ExerciseRenderer";
import { VirtualKeyboard } from "../VirtualKeyboard";
import { PronunciationFeedback } from "../PronunciationFeedback";
import { QuitConfirm } from "../QuitConfirm";
import { ReportIssueButton } from "../ReportIssueButton";
import { TeachingCardView } from "../TeachingCardView";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// Pretend the device can record so VoiceCaptureControls renders its real
// mic/keyboard toggle (the hook itself is inert until a button is pressed).
vi.mock("../../lib/useMicRecorder", async (orig) => ({
  ...(await orig<typeof import("../../lib/useMicRecorder")>()),
  micRecordingSupported: () => true,
}));

const block = (text: string, lang = "nl", direction: "ltr" | "rtl" = "ltr") => ({
  text,
  language_code: lang,
  direction,
});

const PROMPTS: Record<ExerciseType, ExercisePrompt> = {
  multiple_choice: { text_blocks: [block("Kies.")], options: ["jij / je", "u"], answer_language_code: "nl" },
  listen_select: {
    text_blocks: [block("Luister.")],
    options: ["Bent u nieuw hier?", "Ben jij nieuw hier?"],
    audio_text: "Bent u nieuw hier?",
    audio_language_code: "nl",
    answer_language_code: "nl",
  },
  dialogue_comprehension: { text_blocks: [block("Wie spreekt?")], options: ["Noor", "Omar"] },
  translation: { text_blocks: [block("parents", "en")], answer_language_code: "nl" },
  reverse_translation: { text_blocks: [block("ouders")], answer_language_code: "en" },
  listen_type: {
    text_blocks: [block("Typ wat je hoort.")],
    audio_text: "Bent u nieuw hier?",
    audio_language_code: "nl",
    answer_language_code: "nl",
  },
  dictation: {
    text_blocks: [],
    audio_text: "Ik heb morgen een afspraak bij de dokter.",
    audio_language_code: "nl",
    answer_language_code: "nl",
  },
  fill_in_blank: { text_blocks: [block("Ik kom ___ België.")], answer_language_code: "nl" },
  word_order: { text_blocks: [block("Zet op volgorde.")], word_bank: ["Ben", "jij", "nieuw", "hier"], answer_language_code: "nl" },
  listen_order: {
    text_blocks: [block("Luister en zet op volgorde.")],
    word_bank: ["Bent", "u", "nieuw", "hier"],
    audio_text: "Bent u nieuw hier?",
    audio_language_code: "nl",
    answer_language_code: "nl",
  },
  matching_pairs: {
    text_blocks: [block("Koppel.")],
    pairs: [
      { left: "jij / je", right: "informeel" },
      { left: "u", right: "formeel of beleefd" },
    ],
    answer_language_code: "nl",
  },
  listening_placeholder: { text_blocks: [block("Luisteroefening.")] },
  speaking_placeholder: { text_blocks: [block("Spreekoefening.")] },
  dialogue_response: { text_blocks: [block("Hoi! Hoe gaat het met je?")], answer_language_code: "nl" },
  grammar_check: { text_blocks: [block("Comment allez-___ ?", "fr")], answer_language_code: "fr" },
  flashcard: {
    text_blocks: [block("سلام", "fa", "rtl")],
    back_text_blocks: [block("hello", "en")],
  },
  reading_comprehension: { text_blocks: [block("Winterjas: maat M.")], options: ["M", "S"], answer_language_code: "nl" },
  writing_prompt: { text_blocks: [block("Schrijf een formele vraag.")], answer_language_code: "nl" },
  speak_response: { text_blocks: [block("Hoi! Hoe heet je?")], answer_language_code: "nl" },
  speak_repeat: { text_blocks: [block("Vous êtes. Un atelier.", "fr")], answer_language_code: "fr" },
};

function ex(type: ExerciseType, prompt: ExercisePrompt = PROMPTS[type]): Exercise {
  return { id: `ex-${type}`, type, order: 1, prompt };
}

describe("exercise renderers have no serious axe violations", () => {
  it.each(Object.keys(PROMPTS) as ExerciseType[])("%s", async (type) => {
    const { container } = render(<ExerciseRenderer exercise={ex(type)} onAnswer={vi.fn()} disabled={false} />);
    await expectNoSeriousA11yViolations(container);
  });

  it.each(Object.keys(PROMPTS) as ExerciseType[])("%s (disabled)", async (type) => {
    const { container } = render(<ExerciseRenderer exercise={ex(type)} onAnswer={vi.fn()} disabled />);
    await expectNoSeriousA11yViolations(container);
  });

  it.each([
    ["multiple_choice", true],
    ["multiple_choice", false],
    ["grammar_check", true],
    ["reading_comprehension", false],
  ] as const)("graded state %s (correct=%s)", async (type, correct) => {
    const exercise =
      type === "grammar_check"
        ? ex(type, { text_blocks: [block("Klopt dit?")], options: ["ja", "nee"], answer_language_code: "nl" })
        : ex(type);
    const options = exercise.prompt.options!;
    const { container } = render(
      <ExerciseRenderer
        exercise={exercise}
        onAnswer={vi.fn()}
        disabled
        gradedResult={{ correct, correctResponse: options[0] }}
      />,
    );
    await expectNoSeriousA11yViolations(container);
  });

  it("selected option tile exposes its state", async () => {
    render(<ExerciseRenderer exercise={ex("multiple_choice")} onAnswer={vi.fn()} disabled={false} />);
    const tile = screen.getByRole("button", { name: "u" });
    expect(tile).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(tile);
    expect(tile).toHaveAttribute("aria-pressed", "true");
  });

  it("text inputs have an accessible name", () => {
    render(<ExerciseRenderer exercise={ex("translation")} onAnswer={vi.fn()} disabled={false} />);
    expect(screen.getByRole("textbox")).toHaveAccessibleName();
  });
});

describe("RTL (fa/prs) variants", () => {
  const fa = (type: ExerciseType, prompt: Partial<ExercisePrompt>, lang = "fa") =>
    ex(type, {
      text_blocks: [block("سلام", lang, "rtl")],
      answer_language_code: lang,
      ...prompt,
    });

  it.each(["fa", "prs"])("translation %s with virtual keyboard open", async (lang) => {
    const { container } = render(
      <ExerciseRenderer exercise={fa("translation", {}, lang)} onAnswer={vi.fn()} disabled={false} />,
    );
    fireEvent.focus(screen.getByRole("textbox"));
    expect(container.querySelector(".virtual-keyboard")).not.toBeNull();
    await expectNoSeriousA11yViolations(container);
  });

  it.each(["fa", "prs"])("word_order %s", async (lang) => {
    const { container } = render(
      <ExerciseRenderer
        exercise={fa("word_order", { word_bank: ["من", "خوب", "هستم"] }, lang)}
        onAnswer={vi.fn()}
        disabled={false}
      />,
    );
    fireEvent.click(screen.getAllByRole("button", { name: "من" })[0]);
    await expectNoSeriousA11yViolations(container);
  });

  it("multiple_choice fa", async () => {
    const { container } = render(
      <ExerciseRenderer exercise={fa("multiple_choice", { options: ["سلام!", "خداحافظ"] })} onAnswer={vi.fn()} disabled={false} />,
    );
    await expectNoSeriousA11yViolations(container);
  });
});

describe("shared exercise-side components", () => {
  it("VirtualKeyboard (letters + symbols layer)", async () => {
    const { container } = render(
      <VirtualKeyboard script="arabic" onInsert={vi.fn()} onBackspace={vi.fn()} onDismiss={vi.fn()} />,
    );
    await expectNoSeriousA11yViolations(container);
    for (const b of Array.from(container.querySelectorAll("button"))) {
      expect(b).toHaveAccessibleName();
    }
  });

  it("PronunciationFeedback", async () => {
    const { container } = render(
      <PronunciationFeedback
        words={[
          { word: "Hoi", start: 0, end: 0.4, probability: 0.9 },
          { word: "daar", start: 0.5, end: 0.9, probability: 0.3 },
        ]}
      />,
    );
    await expectNoSeriousA11yViolations(container);
  });

  it("QuitConfirm", async () => {
    const { container } = render(<QuitConfirm message="Sure?" onKeepGoing={vi.fn()} onQuit={vi.fn()} />);
    await expectNoSeriousA11yViolations(container);
  });

  it("ReportIssueButton (closed and open)", async () => {
    const { container } = render(<ReportIssueButton onSubmit={vi.fn()} />);
    await expectNoSeriousA11yViolations(container);
    fireEvent.click(screen.getByRole("button"));
    await expectNoSeriousA11yViolations(container);
  });

  it("TeachingCardView", async () => {
    const { container } = render(
      <TeachingCardView
        card={{
          kind: "reading",
          title: "Tekst",
          text_blocks: [block("Ik woon in Utrecht.")],
          glosses: { woon: "live" },
          note: "A *note*",
        } as never}
      />,
    );
    await expectNoSeriousA11yViolations(container);
  });
});
