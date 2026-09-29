import { useState } from "react";
import { useTranslation } from "react-i18next";
import { LessonApi } from "@lingo/shared/api/endpoints";
import { formatCorrectResponse } from "@lingo/shared/lib/formatAnswer";
import { resultStatus } from "@lingo/shared/lib/gradingResult";
import type { AnswerResponse, AnswerResult, Exercise, TeachingCard } from "@lingo/shared/api/types";
import { TeachingCardView } from "./TeachingCardView";
import { EmphasizedText } from "./EmphasizedText";
import { ExerciseRenderer } from "./exercises/ExerciseRenderer";

// Reusable "reading passage + its comprehension questions on one screen"
// component. The passage is pinned at the top (sticky, self-scrolling if
// long) so the learner can keep reading it while answering the questions
// below — today they have to scroll back to the passage between questions.
// Each question is graded independently through the real answer endpoint
// (LessonApi.answer), so the demo is honest rather than a mocked correctness
// display.
export function ReadingPassageWithQuestions({
  passageCard,
  questions,
}: {
  passageCard: TeachingCard;
  questions: Exercise[];
}) {
  const { t } = useTranslation();
  const [results, setResults] = useState<Record<string, AnswerResult>>({});
  const [submitting, setSubmitting] = useState<Record<string, boolean>>({});

  async function handleAnswer(exercise: Exercise, response: AnswerResponse) {
    // One graded answer per question — ignore resubmits once graded.
    if (results[exercise.id] || submitting[exercise.id]) return;
    setSubmitting((s) => ({ ...s, [exercise.id]: true }));
    try {
      const res = await LessonApi.answer(exercise.id, response);
      setResults((r) => ({ ...r, [exercise.id]: res }));
    } catch {
      // Leave the question answerable again on a network/server error rather
      // than trapping it in a permanently-disabled state.
    } finally {
      setSubmitting((s) => ({ ...s, [exercise.id]: false }));
    }
  }

  return (
    <div>
      <div
        style={{
          position: "sticky",
          top: 0,
          zIndex: 2,
          background: "var(--bg)",
          paddingBottom: 8,
          maxHeight: "55vh",
          overflowY: "auto",
        }}
      >
        <TeachingCardView card={passageCard} />
      </div>
      <div>
        {questions.map((question) => {
          const result = results[question.id];
          const status = result ? resultStatus(result) : null;
          return (
            <div key={question.id} style={{ marginTop: 16 }}>
              <ExerciseRenderer
                exercise={question}
                onAnswer={(response) => handleAnswer(question, response)}
                disabled={submitting[question.id] || Boolean(result)}
                gradedResult={
                  result
                    ? { correct: result.correct, correctResponse: result.correct_response }
                    : undefined
                }
              />
              <div role="status" aria-live="polite">
              {result && status && (
                <div className={`feedback-banner ${status}`}>
                  <p style={{ margin: "0 0 6px" }}>
                    {status === "correct" && t("lesson_runner.correct")}
                    {status === "almost" && t("lesson_runner.almost")}
                    {status === "incorrect" && t("lesson_runner.incorrect")}
                  </p>
                  {status !== "correct" && (
                    <p style={{ margin: "0 0 6px", fontWeight: 400 }}>
                      {t("lesson_runner.correct_answer", {
                        answer: formatCorrectResponse(result.correct_response),
                      })}
                    </p>
                  )}
                  {result.feedback && (
                    <p style={{ margin: 0, fontWeight: 400 }}>
                      <EmphasizedText text={result.feedback} />
                    </p>
                  )}
                </div>
              )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
