import type { AnswerResponse, Exercise } from "../../api/types";

// Passed down from pages once an answer has been graded, so option-based
// components can highlight the correct/wrong option instead of just
// disabling the buttons. `correctResponse` is intentionally `unknown` here
// too - see components/exercises/optionHighlight.ts for why it must be
// checked defensively rather than assumed to be a plain string.
export interface GradedResult {
  correct: boolean;
  correctResponse: unknown;
}

export interface ExerciseComponentProps {
  exercise: Exercise;
  onAnswer: (response: AnswerResponse) => void;
  disabled: boolean;
  gradedResult?: GradedResult;
}
