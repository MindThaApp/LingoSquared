import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ProgressApi } from "@lingo/shared/api/endpoints";
import type { AnswerResponse, ReviewAnswerResult, ReviewItem } from "@lingo/shared/api/types";
import { formatCorrectResponse } from "@lingo/shared/lib/formatAnswer";
import { resultStatus } from "@lingo/shared/lib/gradingResult";
import { ExerciseRenderer } from "./exercises/ExerciseRenderer";
import {
  FIX_MISTAKES_MAX_ITEMS,
  filterDueReviews,
  shouldShowFixCard,
  tallyFixResults,
} from "../lib/fixMistakes";

const QUERY_KEY = ["fix-mistakes-due"];

// Follows next_cursor pages up to the cap. Errors propagate to react-query;
// the section simply renders nothing on error.
async function fetchDueMistakes(): Promise<ReviewItem[]> {
  const all: ReviewItem[] = [];
  let cursor: string | undefined;
  do {
    const page = await ProgressApi.reviews(cursor);
    all.push(...page.items);
    cursor = page.next_cursor ?? undefined;
  } while (cursor && all.length < FIX_MISTAKES_MAX_ITEMS);
  return filterDueReviews(all).slice(0, FIX_MISTAKES_MAX_ITEMS);
}

/**
 * "Fix your mistakes" section on the Review page. Renders nothing while
 * loading, on error, or when nothing is due - the page looks unchanged.
 */
export function FixMistakes({
  hidden = false,
  onRunnerActiveChange,
}: {
  hidden?: boolean;
  onRunnerActiveChange?: (active: boolean) => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [session, setSession] = useState<ReviewItem[] | null>(null);

  const query = useQuery({ queryKey: QUERY_KEY, queryFn: fetchDueMistakes, retry: false });

  const runnerActive = session !== null;
  useEffect(() => {
    onRunnerActiveChange?.(runnerActive);
  }, [runnerActive, onRunnerActiveChange]);

  // An SRS session is on screen: show nothing (the runner can't be active then).
  if (hidden) return null;

  if (session) {
    return (
      <FixMistakesRunner
        items={session}
        onDone={() => {
          setSession(null);
          queryClient.invalidateQueries({ queryKey: QUERY_KEY });
        }}
      />
    );
  }

  const items = query.data ?? [];
  if (!shouldShowFixCard(items.length)) return null;

  return (
    <button
      className="card continue-card"
      style={{ width: "100%", textAlign: "start", marginTop: 12, cursor: "pointer" }}
      onClick={() => setSession(items)}
    >
      <div className="continue-info">
        <h3 style={{ margin: "0 0 4px" }}>{t("fix_mistakes.card_title", { count: items.length })}</h3>
        <span className="muted">{t("fix_mistakes.card_body")}</span>
      </div>
      <span className="btn btn-secondary">{t("review.start")}</span>
    </button>
  );
}

function FixMistakesRunner({ items, onDone }: { items: ReviewItem[]; onDone: () => void }) {
  const { t } = useTranslation();
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState<ReviewAnswerResult | null>(null);
  const [lastResponse, setLastResponse] = useState<AnswerResponse | undefined>();
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(false);
  const [outcomes, setOutcomes] = useState<boolean[]>([]);

  const current = items[index];

  async function handleAnswer(response: AnswerResponse) {
    if (!current) return;
    setSubmitting(true);
    setLastResponse(response);
    setSubmitError(false);
    try {
      setResult(await ProgressApi.answerReview(current.id, response));
    } catch {
      setSubmitError(true);
    } finally {
      setSubmitting(false);
    }
  }

  function handleContinue() {
    if (result) setOutcomes((o) => [...o, resultStatus(result) !== "incorrect"]);
    setResult(null);
    setLastResponse(undefined);
    setIndex((i) => i + 1);
  }

  if (!current) {
    const { fixed, total } = tallyFixResults(outcomes);
    return (
      <div className="card" style={{ textAlign: "center", marginTop: 12 }}>
        <div style={{ fontSize: "3rem" }}>🎉</div>
        <h2>{t("fix_mistakes.summary_title")}</h2>
        <p className="muted">{t("fix_mistakes.summary", { fixed, total })}</p>
        <button className="btn btn-block" onClick={onDone}>
          {t("fix_mistakes.back")}
        </button>
      </div>
    );
  }

  const status = result ? resultStatus(result) : null;

  return (
    <div style={{ marginTop: 12 }}>
      <div className="progress-track" style={{ marginBottom: 12 }}>
        <div className="progress-fill" style={{ width: `${(index / items.length) * 100}%` }} />
      </div>
      <span className="muted">
        {t("fix_mistakes.progress", { current: index + 1, total: items.length })}
      </span>
      <ExerciseRenderer
        key={current.id}
        exercise={{ ...current.exercise, order: 0 }}
        onAnswer={handleAnswer}
        disabled={submitting || Boolean(result) || submitError}
        gradedResult={
          result ? { correct: result.correct, correctResponse: result.correct_response } : undefined
        }
      />
      {submitError && !result && (
        <div className="feedback-banner error" role="alert">
          <p style={{ margin: "0 0 10px" }}>{t("review.submit_error")}</p>
          <button
            className="btn btn-block"
            onClick={() => lastResponse && handleAnswer(lastResponse)}
            disabled={submitting}
          >
            {t("common.retry")}
          </button>
        </div>
      )}
      {result && status && (
        <div className={`feedback-banner ${status}`} role="status">
          <p style={{ margin: "0 0 6px" }}>
            {status === "correct" && t("review.correct")}
            {status === "almost" && t("review.almost")}
            {status === "incorrect" && t("review.incorrect")}
          </p>
          {status !== "correct" && (
            <p style={{ margin: "0 0 6px", fontWeight: 400 }}>
              {t("review.correct_answer", { answer: formatCorrectResponse(result.correct_response) })}
            </p>
          )}
          <button className="btn btn-block" onClick={handleContinue}>
            {t("review.continue")}
          </button>
        </div>
      )}
    </div>
  );
}
