import type { GradingStatus } from "@lingo/shared/api/types";
import { resultStatus } from "@lingo/shared/lib/gradingResult";

/** "almost" is a PASS (server accepts it, XP awarded) - only "incorrect" is a miss. */
export function isPassingStatus(status: GradingStatus): boolean {
  return status !== "incorrect";
}

/** True when a graded result should be treated as passed (correct or almost). */
export function resultPassed(result: { correct: boolean; result?: GradingStatus }): boolean {
  return result.correct || isPassingStatus(resultStatus(result));
}

export interface AnswerOutcome {
  /** Item is resolved and leaves the queue. */
  resolved: boolean;
  /** Item goes to the back of the queue for another attempt. */
  requeue: boolean;
  /** Item should be recorded in the lesson's missed-words list. */
  recordMissed: boolean;
}

/** What the lesson queue does after a graded answer. Almost behaves exactly like correct. */
export function answerOutcome(
  result: { correct: boolean; result?: GradingStatus },
  isConfirmation: boolean,
): AnswerOutcome {
  const passed = resultPassed(result);
  const resolved = passed || isConfirmation;
  return { resolved, requeue: !resolved, recordMissed: !passed };
}

/** Fraction of answers that passed (correct or almost); almost is not a mistake. */
export function passAccuracy(results: { correct: boolean; result?: GradingStatus }[]): number {
  if (results.length === 0) return 0;
  return results.filter(resultPassed).length / results.length;
}
