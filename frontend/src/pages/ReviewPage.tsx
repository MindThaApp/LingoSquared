import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { CatalogApi, ReviewApi } from "@lingo/shared/api/endpoints";
import { CourseTargetLanguage } from "../components/CourseTargetLanguage";
import { ExerciseRenderer } from "../components/exercises/ExerciseRenderer";
import { ReportIssueButton } from "../components/ReportIssueButton";
import { QuitConfirm } from "../components/QuitConfirm";
import { formatCorrectResponse } from "@lingo/shared/lib/formatAnswer";
import { resultStatus } from "@lingo/shared/lib/gradingResult";
import { answerDirectionForExercise } from "@lingo/shared/lib/scripts";
import { AlmostFeedback } from "../components/AlmostFeedback";
import type { AnswerResponse, PracticeAnswerResult, PracticeItem } from "@lingo/shared/api/types";
import { asExerciseType } from "@lingo/shared/api/types";
import { useAuth } from "../auth/AuthContext";
import { learnPath } from "../lib/activeCourse";
import { invalidateProgressQueries } from "../lib/invalidateProgress";

interface CoursePickOption {
  courseId: string;
  title: string;
  dueCount: number;
}

export function ReviewPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [courseId, setCourseId] = useState<string | null>(null);
  const [autoPicked, setAutoPicked] = useState(false);
  const [items, setItems] = useState<PracticeItem[] | null>(null);
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState<PracticeAnswerResult | null>(null);
  const [lastResponse, setLastResponse] = useState<AnswerResponse | undefined>();
  const [submitting, setSubmitting] = useState(false);
  const [reviewedCount, setReviewedCount] = useState(0);
  const [submitError, setSubmitError] = useState(false);
  const [showQuitConfirm, setShowQuitConfirm] = useState(false);
  const [sessionError, setSessionError] = useState(false);
  const [retryError, setRetryError] = useState(false);
  // Bumped by the session Retry button so the load effect re-runs even though
  // courseId is unchanged (setCourseId(null); setCourseId(id) batches to a no-op).
  const [reloadNonce, setReloadNonce] = useState(0);

  const dueQuery = useQuery({
    queryKey: ["reviews-due"],
    queryFn: () => ReviewApi.due(),
  });

  const dueCourses = dueQuery.data?.by_course.filter((c) => c.due_count > 0) ?? [];

  const titlesQuery = useQuery({
    queryKey: ["reviews-due-titles", dueCourses.map((c) => c.course_id).join(",")],
    queryFn: async (): Promise<CoursePickOption[]> =>
      Promise.all(
        dueCourses.map(async (c) => {
          const course = await CatalogApi.course(c.course_id);
          return { courseId: c.course_id, title: course.title, dueCount: c.due_count };
        }),
      ),
    enabled: dueCourses.length > 0,
  });

  // Extract the sole-due-course id as a stable primitive so the auto-pick
  // effect below depends on it (a string|null that only changes when the set
  // of due courses does) rather than on the `dueCourses` array, which is
  // rebuilt every render and re-ran the effect on every render (a guarded
  // no-op, but wasteful).
  const soleDueCourseId = dueCourses.length === 1 ? dueCourses[0].course_id : null;

  useEffect(() => {
    if (!autoPicked && soleDueCourseId) {
      setCourseId(soleDueCourseId);
      setAutoPicked(true);
    }
  }, [autoPicked, soleDueCourseId]);

  useEffect(() => {
    let cancelled = false;
    if (!courseId) return;
    setSessionError(false);
    ReviewApi.session(courseId, 10)
      .then((res) => {
        if (!cancelled) setItems(res.items);
      })
      .catch(() => {
        if (!cancelled) setSessionError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [courseId, reloadNonce]);

  function handleSessionRetry() {
    setItems(null);
    setSessionError(false);
    setReloadNonce((n) => n + 1);
  }

  const current = items?.[index];

  async function handleAnswer(response: AnswerResponse) {
    if (!current) return;
    setSubmitting(true);
    setLastResponse(response);
    setSubmitError(false);
    try {
      const res = await ReviewApi.answer(current.id, response);
      setResult(res);
      invalidateProgressQueries(queryClient);
    } catch {
      setSubmitError(true);
    } finally {
      setSubmitting(false);
    }
  }

  function handleResubmit() {
    if (lastResponse) handleAnswer(lastResponse);
  }

  function handleQuit() {
    navigate(-1);
  }

  async function handleRetry() {
    if (!current) return;
    setSubmitting(true);
    setRetryError(false);
    try {
      const res = await ReviewApi.retry(current.id);
      const fresh = res.items[0];
      setItems((prev) => {
        if (!prev) return prev;
        const copy = [...prev];
        copy[index] = fresh;
        return copy;
      });
      setResult(null);
      setLastResponse(undefined);
    } catch {
      // Without this the "Try again" button silently did nothing on a network
      // error. The result banner (and its Try again button) stays mounted
      // because setResult(null) is never reached, so this message sits right
      // next to the button that failed and the same button is the retry.
      setRetryError(true);
    } finally {
      setSubmitting(false);
    }
  }

  function handleContinue() {
    setResult(null);
    setLastResponse(undefined);
    setRetryError(false);
    setReviewedCount((n) => n + 1);
    setIndex((i) => i + 1);
  }

  if (dueQuery.isLoading) return <p className="muted">{t("review.loading")}</p>;

  if (dueQuery.isError) {
    return (
      <div className="feedback-banner error">
        <p style={{ margin: "0 0 10px" }}>{t("review.due_fetch_error")}</p>
        <button className="btn btn-block" onClick={() => dueQuery.refetch()}>
          {t("common.retry")}
        </button>
      </div>
    );
  }

  if (dueCourses.length === 0) {
    return (
      <div className="card" style={{ textAlign: "center" }}>
        <div style={{ fontSize: "3rem" }}>✅</div>
        <h2>{t("review.none_due_title")}</h2>
        <p className="muted">{t("review.none_due_body")}</p>
        <button className="btn btn-block" onClick={() => navigate(learnPath(user?.id))}>
          {t("review.continue_learning", { defaultValue: "Continue learning" })}
        </button>
      </div>
    );
  }

  if (!courseId) {
    return (
      <div>
        <h1>{t("review.pick_course_title")}</h1>
        {/* One failing CatalogApi.course() rejects the whole Promise.all, so
            without this branch the heading rendered above ZERO buttons — a
            dead screen offering the learner nothing at all. */}
        {titlesQuery.isError ? (
          <div className="feedback-banner error" role="alert">
            <p style={{ margin: "0 0 10px" }}>{t("review.titles_fetch_error")}</p>
            <button className="btn btn-block" onClick={() => titlesQuery.refetch()}>
              {t("common.retry")}
            </button>
          </div>
        ) : titlesQuery.data === undefined ? (
          <p className="muted">{t("review.loading")}</p>
        ) : (
          titlesQuery.data.map((c) => (
            <button
              key={c.courseId}
              className="card continue-card"
              style={{ width: "100%", textAlign: "start", marginBottom: 12, cursor: "pointer" }}
              onClick={() => setCourseId(c.courseId)}
            >
              <div className="continue-info">
                <h3 style={{ margin: "0 0 4px" }}>{c.title}</h3>
                <span className="muted">{t("review.due_count", { count: c.dueCount })}</span>
              </div>
              <span className="btn btn-secondary">{t("review.start")}</span>
            </button>
          ))
        )}
      </div>
    );
  }

  if (sessionError) {
    return (
      <div className="feedback-banner error">
        <p style={{ margin: "0 0 10px" }}>{t("review.session_fetch_error")}</p>
        <button className="btn btn-block" onClick={handleSessionRetry}>
          {t("common.retry")}
        </button>
      </div>
    );
  }

  if (items === null) return <p className="muted">{t("review.loading")}</p>;

  if (!current) {
    return (
      <div className="card" style={{ textAlign: "center" }}>
        <div style={{ fontSize: "3rem" }}>🎉</div>
        <h2>{t("review.all_caught_up")}</h2>
        <p className="muted">{t("review.session_summary", { count: reviewedCount })}</p>
        <button className="btn btn-block" onClick={() => navigate(courseId ? `/courses/${courseId}` : "/")}>
          {t("review.continue_learning", { defaultValue: "Continue learning" })}
        </button>
      </div>
    );
  }

  const pct = (index / items.length) * 100;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <div className="progress-track" style={{ flex: 1 }}>
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <button
          type="button"
          className="btn-icon-toggle"
          aria-label={t("review.exit_label")}
          onClick={() => setShowQuitConfirm(true)}
        >
          <X size={18} />
        </button>
      </div>
      <span className="muted">
        {t("review.progress", { current: index + 1, total: items.length })}
      </span>
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
          <p style={{ margin: "0 0 10px" }}>{t("review.submit_error")}</p>
          <button className="btn btn-block" onClick={handleResubmit} disabled={submitting}>
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
                correct={formatCorrectResponse(result.correct_response)}
                dir={answerDirectionForExercise({ id: current.id, type: asExerciseType(current.type), order: 0, prompt: current.prompt })}
              />
              <button className="btn btn-block" onClick={handleContinue}>
                {t("review.continue")}
              </button>
            </div>
          );
        }
        return (
          // role="status" (implicit aria-live="polite") - announces the grading
          // result to screen readers when the banner mounts.
          <div className={`feedback-banner ${status}`} role="status">
            <p style={{ margin: "0 0 6px" }}>
              {status === "correct" && t("review.correct")}
              {status === "incorrect" && t("review.incorrect")}
            </p>
            {status !== "correct" && (
              <p style={{ margin: "0 0 6px", fontWeight: 400 }}>
                {t("review.correct_answer", { answer: formatCorrectResponse(result.correct_response) })}
              </p>
            )}
            <div style={{ display: "flex", gap: 8 }}>
              {status === "incorrect" && (
                <button className="btn btn-secondary btn-block" onClick={handleRetry} disabled={submitting}>
                  {t("review.try_again")}
                </button>
              )}
              <button className="btn btn-block" onClick={handleContinue}>
                {t("review.continue")}
              </button>
            </div>
            {retryError && (
              <p role="alert" style={{ margin: "10px 0 0", fontWeight: 400 }}>
                {t("review.retry_error")}
              </p>
            )}
          </div>
        );
      })()}
      <div style={{ marginTop: 12, textAlign: "center" }}>
        {/* current.id is a PracticeItem id (generated by /reviews/session),
            never an Exercise id - must go through the practice-item report
            endpoint or every report here 404s. */}
        <ReportIssueButton
          lastResponse={lastResponse}
          onSubmit={(category, description, response) =>
            ReviewApi.reportIssue(current.id, category, description, response)
          }
        />
      </div>
      {showQuitConfirm && (
        <QuitConfirm
          message={t("review.quit_confirm_message")}
          onKeepGoing={() => setShowQuitConfirm(false)}
          onQuit={handleQuit}
        />
      )}
    </div>
  );
}
