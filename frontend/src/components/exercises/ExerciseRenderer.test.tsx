import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ExerciseRenderer } from "./ExerciseRenderer";
import type { Exercise, ExercisePrompt, ExerciseType } from "@lingo/shared/api/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// speak_repeat / speak_response mount VoiceCaptureControls, which wraps
// MediaRecorder/Worker plumbing jsdom doesn't have.
vi.mock("../VoiceCaptureControls", () => ({
  VoiceCaptureControls: () => null,
}));

// Registration guard for this project's single worst historical bug class:
// SIX exercise types once shipped in content without a case in this
// renderer's switch — the compiler and tsc were both green, and every one
// only crashed (or fell through to the unsupported-type message) in a real
// lesson in the browser (see CLAUDE.md's exercise-type-registration
// footgun). This Record is deliberately keyed on the ExerciseType union
// itself, so adding a new type to @lingo/shared/api/types makes this file
// FAIL TO COMPILE until a prompt is added here — and the test then fails
// until the renderer actually routes it somewhere real.
//
// Prompts are minimal but shape-correct per type (options for choice
// types, word_bank for order types, pairs for matching) so each component
// renders its real interactive UI, not a degenerate empty state.
const block = (text: string) => ({
  text,
  language_code: "nl",
  direction: "ltr" as const,
});

const PROMPTS: Record<ExerciseType, ExercisePrompt> = {
  multiple_choice: { text_blocks: [block("Kies.")], options: ["jij / je", "u"] },
  listen_select: {
    text_blocks: [block("Luister.")],
    options: ["Bent u nieuw hier?", "Ben jij nieuw hier?"],
    audio_text: "Bent u nieuw hier?",
    audio_language_code: "nl",
  },
  dialogue_comprehension: { text_blocks: [block("Wie spreekt?")], options: ["Noor", "Omar"] },
  translation: { text_blocks: [block("parents")], answer_language_code: "nl" },
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
  word_order: { text_blocks: [block("Zet op volgorde.")], word_bank: ["Ben", "jij", "nieuw", "hier"] },
  listen_order: {
    text_blocks: [block("Luister en zet op volgorde.")],
    word_bank: ["Bent", "u", "nieuw", "hier"],
    audio_text: "Bent u nieuw hier?",
    audio_language_code: "nl",
  },
  matching_pairs: {
    text_blocks: [block("Koppel.")],
    pairs: [
      { left: "jij / je", right: "informeel" },
      { left: "u", right: "formeel of beleefd" },
    ],
  },
  listening_placeholder: { text_blocks: [block("Luisteroefening.")] },
  speaking_placeholder: { text_blocks: [block("Spreekoefening.")] },
  dialogue_response: { text_blocks: [block("Hoi! Hoe gaat het met je?")], answer_language_code: "nl" },
  grammar_check: { text_blocks: [block("Comment allez-___ ?")], answer_language_code: "fr" },
  flashcard: {
    text_blocks: [block("سلام")],
    back_text_blocks: [{ text: "hello", language_code: "en", direction: "ltr" as const }],
  },
  reading_comprehension: { text_blocks: [block("Winterjas: maat M.")], options: ["M", "S"] },
  writing_prompt: { text_blocks: [block("Schrijf een formele vraag.")], answer_language_code: "nl" },
  speak_response: { text_blocks: [block("Hoi! Hoe heet je?")], answer_language_code: "nl" },
  speak_repeat: { text_blocks: [block("Vous êtes. Un atelier.")], answer_language_code: "fr" },
};

describe("ExerciseRenderer type registration", () => {
  it.each(Object.keys(PROMPTS) as ExerciseType[])(
    "renders a real component for %s, never the unsupported-type fallback",
    (type) => {
      const exercise: Exercise = {
        id: `ex-${type}`,
        type,
        order: 1,
        prompt: PROMPTS[type],
      };
      render(<ExerciseRenderer exercise={exercise} onAnswer={vi.fn()} disabled={false} />);
      // The default-case fallback renders t("exercise.unsupported_type") —
      // with the key-echoing t() mock that exact text appearing means the
      // type has no registered component.
      expect(screen.queryByText("exercise.unsupported_type")).not.toBeInTheDocument();
      // And something interactive actually rendered (every exercise UI,
      // including the placeholders' skip button, exposes at least one button).
      expect(screen.getAllByRole("button").length).toBeGreaterThan(0);
    }
  );
});
