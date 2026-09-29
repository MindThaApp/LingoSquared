import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { CheckpointApi } from "@lingo/shared/api/endpoints";
import { ApiError } from "@lingo/shared/api/client";
import { CourseTargetLanguage } from "../components/CourseTargetLanguage";
import { ExerciseRenderer } from "../components/exercises/ExerciseRenderer";
import { QuitConfirm } from "../components/QuitConfirm";
import { formatCorrectResponse } from "@lingo/shared/lib/formatAnswer";
import { resultStatus } from "@lingo/shared/lib/gradingResult";
import { answerDirectionForExercise } from "@lingo/shared/lib/scripts";
import { AlmostFeedback } from "../components/AlmostFeedback";
import type { AnswerResponse, CheckpointResult, PracticeAnswerResult, PracticeItem } from "@lingo/shared/api/types";
import { asExerciseType } from "@lingo/shared/api/types";
import { invalidateProgressQueries } from "../lib/invalidateProgress";

type Phase =
  | "loading"
  | "blocked"
  | "unavailable"
  | "network_error"
  | "in_progress"
  | "scoring"
  | "scoring_error"
  | "done";

// The minute count is rendered through i18next's own plural machinery
// (`checkpoint.retry_minutes_one` / `_other`) rather than an English
// "1 minute"/"N minutes" ternary -- the previous hardcoded ternary was the
// only English left on this screen for fa/prs/nl learners. Every locale
// defines BOTH suffixes even where the language has no singular/plural
// distinction (fa/prs), because i18next picks the suffix from
// Intl.PluralRules and falls back to English if the chosen suffix is absent.
function retryAfterMinutes(seconds: number): number {
  return Math.max(1, Math.ceil(seconds / 60));
}

export function CheckpointPage() {
  const { t } = useTranslation();
  const { unitId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const location = useLocation();
  // Threaded via route state when the checkpoint is entered from a course
  // path; may be absent, in which case the drill target still seeds the
  // feed and PracticeFeedPage resolves the course itself.
  const courseId = (location.state as { courseId?: string } | null)?.courseId;

  const [phase, setPhase] = useState<Phase>("loading");
  const [items, setItems] = useState<PracticeItem[]>([]);
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState<PracticeAnswerResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [retryAfterSeconds, setRetryAfterSeconds] = useState<number | null>(null);
  const [finalResult, setFinalResult] = useState<CheckpointResult | null>(null);
  const [lastResponse, setLastResponse] = useState<AnswerResponse | undefined>();
  const [lastSpoken, setLastSpoken] = useState(false);
  const [submitError, setSubmitError] = useState(false);
  const [showQuitConfirm, setShowQuitConfirm] = useState(false);
  // Bumped by the network-error Retry button to re-run the start effect.
  const [reloadNonce, setReloadNonce] = useState(0);

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
        } else if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
          setPhase("unavailable");
        } else {
          // Fetch rejection (offline/DNS), 5xx, or anything that isn't a
          // definitive 4xx: the checkpoint may well exist, so offer Retry
          // instead of claiming it's unavailable.
          setPhase("network_error");
        }
      }
    }
    setPhase("loading");
    start();
    return () => {
      cancelled = true;
    };
  }, [unitId, reloadNonce]);

  const current = items[index];

  async function handleAnswer(response: AnswerResponse, meta?: { inputMode?: "spoken" }) {
    if (!current) return;
    setSubmitting(true);
    setLastResponse(response);
    setLastSpoken(meta?.inputMode === "spoken");
    setSubmitError(false);
    try {
      const res = await CheckpointApi.answer(current.id, response, meta);
      setResult(res);
    } catch {
      setSubmitError(true);
    } finally {
      setSubmitting(false);
    }
  }

  function handleRetryAnswer() {
    if (lastResponse) handleAnswer(lastResponse, lastSpoken ? { inputMode: "spoken" } : undefined);
  }

  async function scoreCheckpoint() {
    setPhase("scoring");
    try {
      const scored = await CheckpointApi.result(unitId);
      setFinalResult(scored);
      setPhase("done");
      invalidateProgressQueries(queryClient);
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

  if (phase === "network_error") {
    return (
      <div className="card" style={{ textAlign: "center" }}>
        <p className="muted">
          {t("checkpoint.load_error", {
            defaultValue: "Couldn't load this checkpoint — check your connection and try again.",
          })}
        </p>
        <button className="btn" onClick={() => setReloadNonce((n) => n + 1)}>
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
            ? t("checkpoint.blocked_body_with_time", {
                time: t("checkpoint.retry_minutes", { count: retryAfterMinutes(retryAfterSeconds) }),
              })
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
        {finalResult.weak_lexeme_ids?.length ? (
          <div style={{ marginTop: 24 }}>
            <Link
              className="btn"
              to="/practice"
              state={{ courseId, targetLexemeIds: finalResult.weak_lexeme_ids }}
            >
              {t("checkpoint.drill_weak_outcomes")}
            </Link>
          </div>
        ) : null}
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
      <CourseTargetLanguage courseId={courseId}><ExerciseRenderer
        key={current.id}
        exercise={{ id: current.id, type: asExerciseType(current.type), order: 0, prompt: current.prompt }}
        onAnswer={handleAnswer}
        disabled={submitting || Boolean(result) || submitError}
        gradedResult={
          result ? { correct: result.correct, correctResponse: result.correct_response } : undefined
        }
      /></CourseTargetLanguage>
      {submitError && !result && (
        <div className="feedback-banner error" role="alert">
          <p style={{ margin: "0 0 10px" }}>{t("checkpoint.submit_error")}</p>
          <button className="btn btn-block" onClick={handleRetryAnswer} disabled={submitting}>
            {t("common.retry")}
          </button>
        </div>
      )}
      {result && (() => {
        const status = resultStatus(result);
        if (status === "almost") {
          return (
            <div className="feedback-banner almost" role="status">
              <AlmostFeedback
                learner={typeof lastResponse === "string" ? lastResponse : undefined}
                spoken={lastSpoken}
                correct={formatCorrectResponse(result.correct_response)}
                dir={answerDirectionForExercise({ id: current.id, type: asExerciseType(current.type), order: 0, prompt: current.prompt })}
              />
              <button className="btn btn-block" onClick={handleContinue}>
                {t("checkpoint.continue")}
              </button>
            </div>
          );
        }
        return (
          // role="status" (implicit aria-live="polite") - announces the grading
          // result to screen readers when the banner mounts.
          <div className={`feedback-banner ${status}`} role="status">
            <p style={{ margin: "0 0 6px" }}>
              {status === "correct" && t("checkpoint.correct")}
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
