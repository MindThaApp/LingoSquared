import type { AnswerMeta, AnswerResponse, CefrLevel, Exercise } from "@lingo/shared/api/types";

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
  onAnswer: (response: AnswerResponse, meta?: AnswerMeta) => void;
  disabled: boolean;
  gradedResult?: GradedResult;
  // Word-bank (tap-to-build) answer mode inputs. All optional: callers that
  // omit courseLevel (review/practice/checkpoint) always get the typed input.
  courseLevel?: CefrLevel | null;
  lessonExercises?: Exercise[];
  // Correct answer of the previous miss, already shown on screen.
  answerHint?: string;
  // Self-graded types (flashcard) only: offer Again/Hard/Good/Easy instead of
  // the two-button known/unknown pair. Ignored by auto-graded types.
  ratings?: boolean;
}
