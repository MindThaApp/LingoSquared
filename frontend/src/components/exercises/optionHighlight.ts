import type { GradedResult } from "./types";

/**
 * Determine which of an exercise's `options` (if any) is the "correct" one,
 * for post-grade highlighting in choice-based components (MultipleChoice,
 * GrammarCheck's closed-question mode, ReadingComprehension).
 *
 * `correct_response` is an untyped `unknown` whose actual shape varies by
 * exercise type - this project has already shipped two real grading bugs
 * (matching_pairs, word_order/listen_order - see CLAUDE.md footguns) from
 * assuming its shape without checking real content. Stay conservative here
 * too: only ever return a match when correct_response is a plain string (or
 * an array whose first/only element is a plain string) that is literally
 * one of the exercise's own `options`. Any other shape returns null and
 * callers must skip highlighting entirely rather than guess.
 */
export function correctOptionFromResponse(correctResponse: unknown, options: string[]): string | null {
  const candidate = Array.isArray(correctResponse) ? correctResponse[0] : correctResponse;
  if (typeof candidate === "string" && options.includes(candidate)) return candidate;
  return null;
}

/**
 * className for a single option button, before vs. after grading.
 * - Before grading (no gradedResult, or correctOption couldn't be
 *   determined): the existing "selected" accent highlight only.
 * - After grading with a resolvable correct option: the correct option
 *   turns green; the learner's own choice turns red if it was wrong.
 */
export function optionClassName(
  option: string,
  selected: string | null,
  gradedResult: GradedResult | undefined,
  correctOption: string | null,
): string {
  if (gradedResult && correctOption) {
    if (option === correctOption) return "exercise-option correct";
    if (option === selected) return "exercise-option incorrect";
    return "exercise-option";
  }
  return `exercise-option${selected === option ? " selected" : ""}`;
}

/**
 * Post-grade marker state for one option (same resolution rules as
 * optionClassName): "correct" for the correct option, "incorrect" for the
 * learner's wrong choice, null otherwise / before grading.
 */
export function optionGradeState(
  option: string,
  selected: string | null,
  gradedResult: GradedResult | undefined,
  correctOption: string | null,
): "correct" | "incorrect" | null {
  if (gradedResult && correctOption) {
    if (option === correctOption) return "correct";
    if (option === selected) return "incorrect";
  }
  return null;
}
