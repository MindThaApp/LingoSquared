import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { formatCorrectResponse } from "@lingo/shared/lib/formatAnswer";
import { resultStatus } from "@lingo/shared/lib/gradingResult";
import type { ExercisePrompt, GradingStatus } from "@lingo/shared/api/types";
import { speak } from "../api/tts";
import { playAnswerCue } from "../lib/answerCue";
import { answerWhy } from "../lib/answerWhy";
import { getAutoPlayAnswer } from "../lib/feedbackPreferences";

interface GradedResult {
  correct: boolean;
  result?: GradingStatus;
  correct_response: unknown;
}

/**
 * Fires once per graded answer: a short cue (correct/wrong) and, on a wrong or
 * near-miss answer, the correct answer read aloud when a TTS voice exists.
 * Renders the "Why?" expander only when the exercise carries an authored
 * explanation, grammar note or gloss.
 */
export function AnswerFeedbackExtras({
  result,
  prompt,
}: {
  result: GradedResult;
  prompt: ExercisePrompt | undefined;
}) {
  const { t } = useTranslation();
  const status = resultStatus(result);
  const firedFor = useRef<GradedResult | null>(null);

  useEffect(() => {
    if (firedFor.current === result) return;
    firedFor.current = result;
    playAnswerCue(status === "incorrect" ? "incorrect" : "correct");
    if (status === "correct" || !getAutoPlayAnswer()) return;
    const lang = prompt?.answer_language_code ?? prompt?.audio_language_code;
    const text = formatCorrectResponse(result.correct_response);
    if (!lang || !text) return;
    // Autoplay-policy rejections and "no voice" are silent: the learner can
    // still use the speaker button.
    void Promise.resolve(speak(text, lang, undefined)).catch(() => {});
  }, [result, status, prompt]);

  const why = status === "correct" ? [] : answerWhy(prompt);
  if (why.length === 0) return null;
  return (
    <details className="why-expander">
      <summary>{t("feedback.why")}</summary>
      {why.map((text, i) => (
        <p key={i} dir="auto" style={{ margin: "6px 0 0", fontWeight: 400 }}>
          {text}
        </p>
      ))}
    </details>
  );
}
