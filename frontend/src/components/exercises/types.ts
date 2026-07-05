import type { AnswerResponse, Exercise } from "../../api/types";

export interface ExerciseComponentProps {
  exercise: Exercise;
  onAnswer: (response: AnswerResponse) => void;
  disabled: boolean;
}
