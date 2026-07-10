import type { GradingStatus } from "../api/types";

/**
 * Derive the tri-state grading status ("correct" | "almost" | "incorrect")
 * used to pick a feedback-banner style. Prefers the server's `result` field
 * (Phase C typo tolerance - see docs/CONTRACT.md) but falls back to the
 * boolean `correct` field for any response that doesn't carry a valid
 * `result` value, so a stale cached response or an unexpected runtime shape
 * degrades to the old binary correct/incorrect behavior rather than
 * crashing or rendering nothing.
 */
export function resultStatus(result: { correct: boolean; result?: GradingStatus }): GradingStatus {
  if (result.result === "correct" || result.result === "almost" || result.result === "incorrect") {
    return result.result;
  }
  return result.correct ? "correct" : "incorrect";
}
