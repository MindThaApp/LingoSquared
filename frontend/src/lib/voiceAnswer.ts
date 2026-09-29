import type { AnswerMeta, AnswerResponse } from "@lingo/shared/api/types";

// The mic answer option is offered only when the answer is in the language
// being studied. If either side is unknown we hide it (never guess).
export function voiceAnswerEligible(
  answerLanguageCode: string | null | undefined,
  targetLanguageCode: string | null | undefined,
): boolean {
  if (!answerLanguageCode) return false;
  const answer = answerLanguageCode.split("-")[0];
  const target = (targetLanguageCode ?? answerLanguageCode).split("-")[0];
  return answer === target;
}

// Typed answers must call onAnswer with exactly one argument (no meta at
// all); only voice-produced answers carry { inputMode: "spoken" }.
export function submitAnswer(
  onAnswer: (response: AnswerResponse, meta?: AnswerMeta) => void,
  response: AnswerResponse,
  spoken: boolean,
): void {
  if (spoken) onAnswer(response, { inputMode: "spoken" });
  else onAnswer(response);
}
