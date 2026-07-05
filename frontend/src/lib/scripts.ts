import type { Exercise, ScriptCode, TextBlock } from "../api/types";

// Mirrors docs/CONTRACT.md's language table. Kept as a frontend lookup
// (not derived from an API call) since it's small and fixed.
export const LANGUAGE_SCRIPT: Record<string, ScriptCode> = {
  en: "latin",
  nl: "latin",
  fr: "latin",
  de: "latin",
  it: "latin",
  es: "latin",
  ru: "cyrillic",
  zh: "han",
  fa: "arabic",
  prs: "arabic",
};

// Traditional Perso-Arabic alphabet order — shared by Farsi and Dari.
const PERSO_ARABIC_LETTERS = [
  "ا", "ب", "پ", "ت", "ث", "ج", "چ", "ح", "خ",
  "د", "ذ", "ر", "ز", "ژ", "س", "ش", "ص", "ض",
  "ط", "ظ", "ع", "غ", "ف", "ق", "ک", "گ", "ل",
  "م", "ن", "و", "ه", "ی",
];

export interface KeyboardLayout {
  direction: "ltr" | "rtl";
  rows: string[][];
  // Zero-width non-joiner — needed for correct Persian/Dari compound
  // spelling (e.g. نمی‌شود) and easy to get wrong typing manually.
  hasZwnj?: boolean;
}

const ROW_SIZE = 11;

function chunk(letters: string[], size: number): string[][] {
  const rows: string[][] = [];
  for (let i = 0; i < letters.length; i += size) {
    rows.push(letters.slice(i, i + size));
  }
  return rows;
}

export const KEYBOARD_LAYOUTS: Partial<Record<ScriptCode, KeyboardLayout>> = {
  arabic: {
    direction: "rtl",
    rows: chunk(PERSO_ARABIC_LETTERS, ROW_SIZE),
    hasZwnj: true,
  },
};

// Only non-Latin scripts get a virtual keyboard — physical keyboards
// already handle Latin (accents included, via dead keys/OS input) well
// enough that this isn't the priority gap.
export function scriptNeedsVirtualKeyboard(script: ScriptCode | null): boolean {
  return script !== null && script !== "latin" && script in KEYBOARD_LAYOUTS;
}

// Best-effort: an exercise doesn't carry an explicit "answer language,"
// so infer it from whichever text_block in the prompt is in a non-English
// (source) language — this holds for every exercise shape actually
// shipped so far. Falls back to null (no keyboard) if nothing matches.
export function scriptFromTextBlocks(blocks: TextBlock[] | undefined): ScriptCode | null {
  if (!blocks) return null;
  for (const block of blocks) {
    const script = LANGUAGE_SCRIPT[block.language_code];
    if (script && script !== "latin") return script;
  }
  return null;
}

// Preferred source of truth: the compiler-provided answer_language_code
// (exact, works for every exercise type including plain "translation"
// exercises whose prompt has no answer-language text_block to scan).
// Falls back to scanning text_blocks for older/uncompiled content that
// predates that field.
export function answerScriptForExercise(exercise: Exercise): ScriptCode | null {
  const answerLanguageCode = exercise.prompt.answer_language_code;
  if (typeof answerLanguageCode === "string") {
    return LANGUAGE_SCRIPT[answerLanguageCode] ?? null;
  }
  return scriptFromTextBlocks(exercise.prompt.text_blocks);
}
