import type { Direction, Exercise, ScriptCode, TextBlock } from "../api/types";

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
  pl: "latin",
  ro: "latin",
  hi: "devanagari",
};

// Traditional Perso-Arabic alphabet order — shared by Farsi and Dari.
const PERSO_ARABIC_LETTERS = [
  "ا", "ب", "پ", "ت", "ث", "ج", "چ", "ح", "خ",
  "د", "ذ", "ر", "ز", "ژ", "س", "ش", "ص", "ض",
  "ط", "ظ", "ع", "غ", "ف", "ق", "ک", "گ", "ل",
  "م", "ن", "و", "ه", "ی",
];

// Devanagari (Hindi) characters, ordered per the InScript standard — India's
// official government Devanagari keyboard (Bureau of Indian Standards; the
// layout every major OS's built-in Hindi input ships), NOT a guessed
// alphabetical list: independent vowels (svar, used word-initially) first,
// then their dependent forms (matras, attached after a consonant — InScript's
// defining design principle is splitting vowels/matras onto one hand and
// consonants onto the other), then consonants (vyanjan) in traditional varga
// (class) order, then the common nukta consonants InScript assigns to
// shifted keys for Persian/Arabic loanword sounds (ज़/फ़/ड़ etc., frequent in
// real Hindi text), then the standalone marks (anusvara/visarga/
// chandrabindu/virama). Cross-checked against two independent InScript
// references (jptyping.com/inscript-keyboard, rajbhasha.net) which agreed on
// every key checked. Devanagari genuinely needs separate independent-vowel
// and matra glyphs — unlike Perso-Arabic, where one letter form suffices —
// so a naive single-alphabet guess here would have been wrong.
const DEVANAGARI_LETTERS = [
  // Independent vowels (svar)
  "अ", "आ", "इ", "ई", "उ", "ऊ", "ऋ", "ए", "ऐ", "ओ", "औ",
  // Dependent vowel signs (matras)
  "ा", "ि", "ी", "ु", "ू", "ृ", "े", "ै", "ो", "ौ",
  // Consonants (vyanjan), traditional varga order
  "क", "ख", "ग", "घ", "ङ",
  "च", "छ", "ज", "झ", "ञ",
  "ट", "ठ", "ड", "ढ", "ण",
  "त", "थ", "द", "ध", "न",
  "प", "फ", "ब", "भ", "म",
  "य", "र", "ल", "व",
  "श", "ष", "स", "ह",
  // Nukta consonants for common loanword sounds
  "क़", "ख़", "ग़", "ज़", "ड़", "ढ़", "फ़",
  // Standalone marks: anusvara, visarga, chandrabindu, virama/halant
  "ं", "ः", "ँ", "्",
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
  devanagari: {
    // Unlike Perso-Arabic-family scripts, Devanagari reads left-to-right.
    direction: "ltr",
    rows: chunk(DEVANAGARI_LETTERS, ROW_SIZE),
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

// word_order/listen_order/matching_pairs assemble raw tokens (word_bank,
// pairs) that carry no per-item direction of their own, unlike text_blocks
// (see TextBlock.tsx's own comment: never inherit direction from the page).
// A tile-click UI for these needs an explicit container `dir` or the
// browser lays every language out LTR regardless of script -- found live
// 2026-07-09: Farsi/Dari learners tapping tiles in the correct (right-to-
// left) reading order still saw them stack left-to-right, because nothing
// ever set `dir` on the answer row. Reuses the same answer_language_code
// source of truth as answerScriptForExercise above.
export function answerDirectionForExercise(exercise: Exercise): Direction {
  return scriptDirection(answerScriptForExercise(exercise));
}

// General script -> reading direction, for any component that already has a
// `script` (not a whole exercise) and needs to set an explicit `dir` rather
// than assume only the Perso-Arabic family is ever RTL — every free-text
// exercise input (Translation/WritingPrompt/FillInBlank/GrammarCheck/
// SpeakRepeat/DialogueResponse) used to hardcode `script === "arabic"`
// directly, which happened to still render correctly for a new LTR script
// like Devanagari (falls through to the `undefined`/browser-default case)
// but was the same "only checked against one script family" trap the
// word_bank RTL footgun above warns about — fixed 2026-07-09 while adding
// Devanagari so it no longer silently depends on Arabic being the only
// non-Latin script that's ever RTL.
export function scriptDirection(script: ScriptCode | null): Direction {
  return KEYBOARD_LAYOUTS[script ?? "latin"]?.direction ?? "ltr";
}
