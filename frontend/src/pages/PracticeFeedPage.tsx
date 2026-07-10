import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CatalogApi, PracticeApi, ProgressApi } from "@lingo/shared/api/endpoints";
import { ExerciseRenderer } from "../components/exercises/ExerciseRenderer";
import { ReportIssueButton } from "../components/ReportIssueButton";
import { ApiError } from "@lingo/shared/api/client";
import { formatCorrectResponse } from "@lingo/shared/lib/formatAnswer";
import { resultStatus } from "@lingo/shared/lib/gradingResult";
import type {
  AnswerResponse,
  CourseDetail,
  PracticeAnswerResult,
  PracticeItem,
} from "@lingo/shared/api/types";

const BATCH_SIZE = 10;
const PREFETCH_THRESHOLD = 3;

// These codes mean the item itself can never be answered again (already
// answered elsewhere, expired mid-scroll, or not this user's) -- distinct
// from a transient network/server failure, which IS retryable with the
// same stored response. See backend/app/api/router.py's practice_answer().
const PERMANENT_ANSWER_ERROR_CODES = new Set([
  "practice_item_not_found",
  "practice_item_answered",
  "practice_item_expired",
]);

interface EligibleCourse extends CourseDetail {
  completed_lessons: number;
}

function PracticeCard({
  item,
  onAnswered,
}: {
  item: PracticeItem;
  onAnswered: (correct: boolean, xp: number) => void;
}) {
  const { t } = useTranslation();
  const [result, setResult] = useState<PracticeAnswerResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const [submitError, setSubmitError] = useState(false);
  const [lastResponse, setLastResponse] = useState<AnswerResponse | undefined>();

  async function handleAnswer(response: AnswerResponse) {
    setSubmitting(true);
    setLastResponse(response);
    setSubmitError(false);
    try {
      const res = await PracticeApi.answer(item.id, response);
      setResult(res);
      onAnswered(res.correct, res.xp_awarded);
    } catch (err) {
      if (err instanceof ApiError && PERMANENT_ANSWER_ERROR_CODES.has(err.code)) {
        // Item may have expired mid-scroll (or already been answered/is
        // foreign to this user) — the card can't be retried, so resolve it
        // visibly instead of silently re-enabling a dead exercise.
        setUnavailable(true);
      } else {
        // Network failure or unexpected server error: retryable with the
        // same stored response, don't clear the learner's selection.
        setSubmitError(true);
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handleRetryAnswer() {
    if (lastResponse) handleAnswer(lastResponse);
  }

  return (
    <div className="card practice-card">
      <ExerciseRenderer
        exercise={{ id: item.id, type: item.type, order: 0, prompt: item.prompt }}
        onAnswer={handleAnswer}
        disabled={submitting || Boolean(result) || unavailable || submitError}
        gradedResult={
          result ? { correct: result.correct, correctResponse: result.correct_response } : undefined
        }
      />
      {submitError && !result && (
        <div className="feedback-banner error">
          <p style={{ margin: "0 0 10px" }}>{t("practice.submit_error")}</p>
          <button className="btn btn-block" onClick={handleRetryAnswer} disabled={submitting}>
            {t("common.retry")}
          </button>
        </div>
      )}
      {result && (() => {
        const status = resultStatus(result);
        return (
          <div className={`feedback-banner ${status}`}>
            <p style={{ margin: 0 }}>
              {status === "correct" && t("practice.correct", { xp: result.xp_awarded })}
              {status === "almost" &&
                t("practice.almost", {
                  xp: result.xp_awarded,
                  answer: formatCorrectResponse(result.correct_response),
                })}
              {status === "incorrect" &&
                t("lesson_runner.correct_answer", {
                  answer: formatCorrectResponse(result.correct_response),
                })}
            </p>
          </div>
        );
      })()}
      {unavailable && (
        <div className="feedback-banner">
          <p style={{ margin: 0 }}>{t("practice.item_unavailable")}</p>
        </div>
      )}
      <div style={{ marginTop: 12, textAlign: "center" }}>
        {/* item.id is a PracticeItem id, same table review/checkpoint
            items use - reported through the shared practice-item report
            endpoint, not /exercises/{id}/report. */}
        <ReportIssueButton
          lastResponse={lastResponse}
          onSubmit={(category, description, response) =>
            PracticeApi.reportIssue(item.id, category, description, response)
          }
        />
      </div>
    </div>
  );
}

export function PracticeFeedPage() {
  const { t } = useTranslation();
  const [loadingEligibility, setLoadingEligibility] = useState(true);
  const [eligibleCourses, setEligibleCourses] = useState<EligibleCourse[]>([]);
  const [courseId, setCourseId] = useState<string | null>(null);
  const [items, setItems] = useState<PracticeItem[]>([]);
  const [locked, setLocked] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [exhausted, setExhausted] = useState(false);
  const [combo, setCombo] = useState(0);
  const [xpToast, setXpToast] = useState<number | null>(null);
  const cardRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const loadingMoreRef = useRef(false);

  useEffect(() => {
    ProgressApi.progress()
      .then(async (progress) => {
        const withProgress = progress.skill_progress.filter(
          (sp) => sp.completed_lessons > 0,
        );
        const courses = await Promise.all(
          withProgress.map((sp) =>
            CatalogApi.course(sp.course_id).then((course) => ({
              ...course,
              completed_lessons: sp.completed_lessons,
            })),
          ),
        );
        setEligibleCourses(courses);
        if (courses.length === 1) setCourseId(courses[0].id);
      })
      .finally(() => setLoadingEligibility(false));
  }, []);

  const loadMore = useCallback(async () => {
    if (!courseId || loadingMoreRef.current || exhausted) return;
    loadingMoreRef.current = true;
    setLoadingMore(true);
    try {
      const res = await PracticeApi.batch(courseId, BATCH_SIZE);
      setLocked(res.locked);
      if (res.items.length === 0) {
        setExhausted(true);
      } else {
        setItems((prev) => [...prev, ...res.items]);
      }
    } finally {
      loadingMoreRef.current = false;
      setLoadingMore(false);
    }
  }, [courseId, exhausted]);

  useEffect(() => {
    if (courseId) loadMore();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId]);

  useEffect(() => {
    const targetIndex = items.length - PREFETCH_THRESHOLD;
    const target = targetIndex >= 0 ? cardRefs.current.get(targetIndex) : null;
    if (!target) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) loadMore();
      },
      { rootMargin: "200px" },
    );
    observer.observe(target);
    return () => observer.disconnect();
  }, [items.length, loadMore]);

  function handleAnswered(correct: boolean, xp: number) {
    setCombo((c) => (correct ? c + 1 : 0));
    if (xp > 0) {
      setXpToast(xp);
      window.setTimeout(() => setXpToast(null), 1500);
    }
  }

  if (loadingEligibility) {
    return <div className="page-loading">{t("common.loading")}</div>;
  }

  if (eligibleCourses.length === 0) {
    return (
      <div className="card" style={{ textAlign: "center" }}>
        <h3>{t("practice.locked_title")}</h3>
        <p className="muted">{t("practice.locked_body")}</p>
        <Link className="btn" to="/courses">
          {t("home.learn")}
        </Link>
      </div>
    );
  }

  if (!courseId) {
    return (
      <div>
        <h2>{t("practice.choose_course")}</h2>
        {eligibleCourses.map((course) => (
          <button
            key={course.id}
            className="card practice-card"
            style={{ width: "100%", textAlign: "start", cursor: "pointer" }}
            onClick={() => setCourseId(course.id)}
          >
            <strong>{course.title}</strong>
          </button>
        ))}
      </div>
    );
  }

  return (
    <div>
      <div className="practice-header">
        {combo > 1 && (
          <span className="badge practice-combo">{t("practice.combo", { count: combo })}</span>
        )}
      </div>

      {locked && items.length === 0 && (
        <div className="card" style={{ textAlign: "center" }}>
          <h3>{t("practice.locked_title")}</h3>
          <p className="muted">{t("practice.locked_body")}</p>
          <Link className="btn" to="/courses">
            {t("home.learn")}
          </Link>
        </div>
      )}

      {items.map((item, index) => (
        <div
          key={item.id}
          ref={(el) => {
            if (el) cardRefs.current.set(index, el);
            else cardRefs.current.delete(index);
          }}
        >
          <PracticeCard item={item} onAnswered={handleAnswered} />
        </div>
      ))}

      {loadingMore && <div className="page-loading">{t("common.loading")}</div>}

      {exhausted && !loadingMore && (
        <p className="muted" style={{ textAlign: "center" }}>
          {items.length > 0 ? t("practice.exhausted") : t("practice.none_yet")}
        </p>
      )}

      {xpToast !== null && (
        <div className="practice-xp-toast stat-xp">+{xpToast} XP</div>
      )}
    </div>
  );
}
