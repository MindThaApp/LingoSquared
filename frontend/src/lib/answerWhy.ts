import type { ExercisePrompt } from "@lingo/shared/api/types";

// Authored explanation-like fields an exercise prompt may carry. Nothing is
// synthesised: if the content has none of these, there is no "Why?".
const WHY_KEYS = ["explanation", "why", "grammar_note", "note", "gloss", "english_gloss"] as const;

function asText(value: unknown): string | null {
  if (typeof value === "string") return value.trim() || null;
  if (Array.isArray(value)) {
    const parts = value
      .map((v) => (typeof v === "string" ? v : (v as { text?: unknown } | null)?.text))
      .filter((v): v is string => typeof v === "string" && v.trim() !== "");
    return parts.length ? parts.join(" ") : null;
  }
  return null;
}

/** Existing explanation / grammar note / gloss on the exercise, or [] if none. */
export function answerWhy(prompt: ExercisePrompt | undefined): string[] {
  if (!prompt) return [];
  const out: string[] = [];
  for (const key of WHY_KEYS) {
    const text = asText(prompt[key]);
    if (text && !out.includes(text)) out.push(text);
  }
  return out;
}
