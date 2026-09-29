import { useTranslation } from "react-i18next";
import type { Direction } from "@lingo/shared/api/types";
import { diffAnswers, type DiffSegment } from "../lib/answerDiff";

function Segments({ segments, kind }: { segments: DiffSegment[]; kind: "wrong" | "right" }) {
  return (
    <>
      {segments.map((s, i) =>
        s.changed ? (
          <mark key={i} className={`almost-mark almost-mark-${kind}`}>
            {s.text}
          </mark>
        ) : (
          <span key={i}>{s.text}</span>
        ),
      )}
    </>
  );
}

/**
 * Amber "Almost right" banner content, shared by every result surface.
 * Render inside `<div className="feedback-banner almost" role="status">`.
 * `dir` is the answer language's direction; learner/correct strings sit in
 * <bdi> so mixed-direction text never reorders the surrounding labels.
 * When `correct` is unavailable only the headline is shown.
 */
export function AlmostFeedback({
  learner,
  correct,
  dir,
}: {
  learner?: string;
  correct?: string;
  dir: Direction;
}) {
  const { t } = useTranslation();
  const hasCorrect = typeof correct === "string" && correct.length > 0;
  const hasLearner = typeof learner === "string" && learner.trim().length > 0;
  const diff = hasCorrect && hasLearner ? diffAnswers(learner!, correct!) : null;
  return (
    <div className="almost-feedback">
      <span className="visually-hidden">
        {hasCorrect ? t("almost_feedback.sr", { answer: correct }) : t("almost_feedback.sr_plain")}
      </span>
      <p className="almost-title" aria-hidden="true">
        <span className="almost-icon">≈</span> {t("almost_feedback.title")}
      </p>
      {hasCorrect && (
        <div className="almost-lines" dir={dir} aria-hidden="true">
          <p className="almost-line">
            {t("almost_feedback.correct_answer")}{" "}
            <bdi dir={dir}>{diff ? <Segments segments={diff.correct} kind="right" /> : correct}</bdi>
          </p>
          {hasLearner && (
            <p className="almost-line almost-line-learner">
              {t("almost_feedback.your_answer")}{" "}
              <bdi dir={dir}>{diff ? <Segments segments={diff.learner} kind="wrong" /> : learner}</bdi>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
