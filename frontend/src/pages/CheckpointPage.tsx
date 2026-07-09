import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { CheckpointApi } from "../api/endpoints";
import { ApiError } from "../api/client";
import { ExerciseRenderer } from "../components/exercises/ExerciseRenderer";
import { QuitConfirm } from "../components/QuitConfirm";
import { formatCorrectResponse } from "../lib/formatAnswer";
import { resultStatus } from "../lib/gradingResult";
import type { AnswerResponse, CheckpointResult, PracticeAnswerResult, PracticeItem } from "../api/types";

type Phase =
  | "loading"
  | "blocked"
  | "unavailable"
  | "in_progress"
  | "scoring"
  | "scoring_error"
  | "done";

function formatRetryAfter(seconds: number): string {
  const minutes = Math.ceil(seconds / 60);
  return minutes <= 1 ? "1 minute" : `${minutes} minutes`;
}

export function CheckpointPage() {
  const { t } = useTranslation();
  const { unitId = "" } = useParams();
  const navigate = useNavigate();

  const [phase, setPhase] = useState<Phase>("loading");
  const [items, setItems] = useState<PracticeItem[]>([]);
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState<PracticeAnswerResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [retryAfterSeconds, setRetryAfterSeconds] = useState<number | null>(null);
  const [finalResult, setFinalResult] = useState<CheckpointResult | null>(null);
  const [lastResponse, setLastResponse] = useState<AnswerResponse | undefined>();
  const [submitError, setSubmitError] = useState(false);
  const [showQuitConfirm, setShowQuitConfirm] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function start() {
      try {
        const res = await CheckpointApi.start(unitId);
        if (cancelled) return;
        if (res.items.length === 0) {
          setPhase("unavailable");
        } else {
          setItems(res.items);
          setPhase("in_progress");
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.code === "checkpoint_retake_delayed") {
          const seconds = err.details.retry_after_seconds;
          setRetryAfterSeconds(typeof seconds === "number" ? seconds : null);
          setPhase("blocked");
        } else {
          setPhase("unavailable");
        }
      }
    }
    start();
    return () => {
      cancelled = true;
    };
  }, [unitId]);

  const current = items[index];

  async function handleAnswer(response: AnswerResponse) {
    if (!current) return;
    setSubmitting(true);
    setLastResponse(response);
    setSubmitError(false);
    try {
      const res = await CheckpointApi.answer(current.id, response);
      setResult(res);
    } catch {
      setSubmitError(true);
    } finally {
      setSubmitting(false);
    }
  }

  function handleRetryAnswer() {
    if (lastResponse) handleAnswer(lastResponse);
  }

  async function scoreCheckpoint() {
    setPhase("scoring");
    try {
      const scored = await CheckpointApi.result(unitId);
      setFinalResult(scored);
      setPhase("done");
    } catch {
      setPhase("scoring_error");
    }
  }

  async function handleContinue() {
    setResult(null);
    if (index + 1 < items.length) {
      setIndex(index + 1);
      return;
    }
    await scoreCheckpoint();
  }

  function handleQuit() {
    navigate(-1);
  }

  if (phase === "loading" || phase === "scoring") {
    return <div className="page-loading">{t("checkpoint.loading")}</div>;
  }

  if (phase === "scoring_error") {
    return (
      <div className="card" style={{ textAlign: "center" }}>
        <p className="muted">{t("checkpoint.scoring_error")}</p>
        <button className="btn" onClick={scoreCheckpoint}>
          {t("common.retry")}
        </button>
      </div>
    );
  }

  if (phase === "blocked") {
    return (
      <div className="card" style={{ textAlign: "center" }}>
        <div style={{ fontSize: "3rem" }}>⏳</div>
        <h2>{t("checkpoint.blocked_title")}</h2>
        <p className="muted">
          {retryAfterSeconds !== null
            ? t("checkpoint.blocked_body_with_time", { time: formatRetryAfter(retryAfterSeconds) })
            : t("checkpoint.blocked_body")}
        </p>
        <button className="btn" onClick={() => navigate(-1)}>
          {t("checkpoint.go_back")}
        </button>
      </div>
    );
  }

  if (phase === "unavailable") {
    return (
      <div className="card" style={{ textAlign: "center" }}>
        <div style={{ fontSize: "3rem" }}>🤔</div>
        <h2>{t("checkpoint.unavailable_title")}</h2>
        <p className="muted">{t("checkpoint.unavailable_body")}</p>
        <button className="btn" onClick={() => navigate(-1)}>
          {t("checkpoint.go_back")}
        </button>
      </div>
    );
  }

  if (phase === "done" && finalResult) {
    return (
      <div style={{ textAlign: "center", paddingTop: 20 }}>
        <div style={{ fontSize: "4rem", marginBottom: 8 }}>
          {finalResult.passed ? "🎉" : "💪"}
        </div>
        <h1>
          {finalResult.passed ? t("checkpoint.passed_title") : t("checkpoint.failed_title")}
        </h1>
        <p className="stat-value" style={{ fontSize: "2rem", margin: "8px 0" }}>
          {Math.round((finalResult.score ?? 0) * 100)}%
        </p>
        <p className="muted">
          {finalResult.passed ? t("checkpoint.passed_body") : t("checkpoint.failed_body")}
        </p>
        {!finalResult.passed && finalResult.weak_outcomes.length > 0 && (
          <div className="card" style={{ marginTop: 16, textAlign: "start", maxWidth: 420, marginInline: "auto" }}>
            <h3 style={{ marginTop: 0 }}>{t("checkpoint.weak_outcomes_title")}</h3>
            <ul style={{ margin: 0, paddingInlineStart: 20 }}>
              {finalResult.weak_outcomes.map((outcome) => (
                <li key={outcome}>{outcome}</li>
              ))}
            </ul>
          </div>
        )}
        <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 24 }}>
          <Link className="btn btn-secondary" to={`/units/${unitId}`}>
            {t("checkpoint.back_to_lessons")}
          </Link>
          <Link className="btn" to="/courses">
            {t("checkpoint.back_to_courses")}
          </Link>
        </div>
      </div>
    );
  }

  if (!current) return null;

  const pct = (index / items.length) * 100;

  return (
    <div>
      <div className="card" style={{ marginBottom: 16, textAlign: "center", background: "var(--surface-2)" }}>
        <strong>{t("checkpoint.header")}</strong>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <div className="progress-track" style={{ flex: 1 }}>
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <span className="muted" style={{ whiteSpace: "nowrap" }}>
          {t("checkpoint.progress", { current: index + 1, total: items.length })}
        </span>
        <button
          type="button"
          className="btn-icon-toggle"
          aria-label={t("checkpoint.exit_label")}
          onClick={() => setShowQuitConfirm(true)}
        >
          <X size={18} />
        </button>
      </div>
      <ExerciseRenderer
        key={current.id}
        exercise={{ id: current.id, type: current.type, order: 0, prompt: current.prompt }}
        onAnswer={handleAnswer}
        disabled={submitting || Boolean(result) || submitError}
        gradedResult={
          result ? { correct: result.correct, correctResponse: result.correct_response } : undefined
        }
      />
      {submitError && !result && (
        <div className="feedback-banner error">
          <p style={{ margin: "0 0 10px" }}>{t("checkpoint.submit_error")}</p>
          <button className="btn btn-block" onClick={handleRetryAnswer} disabled={submitting}>
            {t("common.retry")}
          </button>
        </div>
      )}
      {result && (() => {
        const status = resultStatus(result);
        return (
          <div className={`feedback-banner ${status}`}>
            <p style={{ margin: "0 0 6px" }}>
              {status === "correct" && t("checkpoint.correct")}
              {status === "almost" && t("checkpoint.almost")}
              {status === "incorrect" && t("checkpoint.incorrect")}
            </p>
            {status !== "correct" && (
              <p style={{ margin: "0 0 10px", fontWeight: 400 }}>
                {t("checkpoint.correct_answer", { answer: formatCorrectResponse(result.correct_response) })}
              </p>
            )}
            <button className="btn btn-block" onClick={handleContinue}>
              {t("checkpoint.continue")}
            </button>
          </div>
        );
      })()}
      {showQuitConfirm && (
        <QuitConfirm
          message={t("checkpoint.quit_confirm_message")}
          onKeepGoing={() => setShowQuitConfirm(false)}
          onQuit={handleQuit}
        />
      )}
    </div>
  );
}
