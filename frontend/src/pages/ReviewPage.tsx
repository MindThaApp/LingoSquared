import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { CatalogApi, ReviewApi } from "../api/endpoints";
import { ExerciseRenderer } from "../components/exercises/ExerciseRenderer";
import { ReportIssueButton } from "../components/ReportIssueButton";
import type { AnswerResponse, PracticeAnswerResult, PracticeItem } from "../api/types";

interface CoursePickOption {
  courseId: string;
  title: string;
  dueCount: number;
}

export function ReviewPage() {
  const { t } = useTranslation();
  const [courseId, setCourseId] = useState<string | null>(null);
  const [autoPicked, setAutoPicked] = useState(false);
  const [items, setItems] = useState<PracticeItem[] | null>(null);
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState<PracticeAnswerResult | null>(null);
  const [lastResponse, setLastResponse] = useState<AnswerResponse | undefined>();
  const [submitting, setSubmitting] = useState(false);
  const [reviewedCount, setReviewedCount] = useState(0);

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

  useEffect(() => {
    if (!autoPicked && dueCourses.length === 1) {
      setCourseId(dueCourses[0].course_id);
      setAutoPicked(true);
    }
  }, [autoPicked, dueCourses]);

  useEffect(() => {
    let cancelled = false;
    if (!courseId) return;
    ReviewApi.session(courseId, 10).then((res) => {
      if (!cancelled) setItems(res.items);
    });
    return () => {
      cancelled = true;
    };
  }, [courseId]);

  const current = items?.[index];

  async function handleAnswer(response: AnswerResponse) {
    if (!current) return;
    setSubmitting(true);
    setLastResponse(response);
    try {
      const res = await ReviewApi.answer(current.id, response);
      setResult(res);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRetry() {
    if (!current) return;
    setSubmitting(true);
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
    } finally {
      setSubmitting(false);
    }
  }

  function handleContinue() {
    setResult(null);
    setLastResponse(undefined);
    setReviewedCount((n) => n + 1);
    setIndex((i) => i + 1);
  }

  if (dueQuery.isLoading) return <p className="muted">{t("review.loading")}</p>;

  if (dueCourses.length === 0) {
    return (
      <div className="card" style={{ textAlign: "center" }}>
        <div style={{ fontSize: "3rem" }}>✅</div>
        <h2>{t("review.none_due_title")}</h2>
        <p className="muted">{t("review.none_due_body")}</p>
      </div>
    );
  }

  if (!courseId) {
    return (
      <div>
        <h1>{t("review.pick_course_title")}</h1>
        {titlesQuery.data?.map((c) => (
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
        ))}
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
      </div>
    );
  }

  const pct = (index / items.length) * 100;

  return (
    <div>
      <div className="progress-track" style={{ marginBottom: 16 }}>
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="muted">
        {t("review.progress", { current: index + 1, total: items.length })}
      </span>
      <ExerciseRenderer
        key={current.id}
        exercise={{ id: current.id, type: current.type, order: 0, prompt: current.prompt }}
        onAnswer={handleAnswer}
        disabled={submitting || Boolean(result)}
      />
      {result && (
        <div className={`feedback-banner ${result.correct ? "correct" : "incorrect"}`}>
          <p style={{ margin: "0 0 6px" }}>
            {result.correct ? t("review.correct") : t("review.incorrect")}
          </p>
          {!result.correct && (
            <p style={{ margin: "0 0 6px", fontWeight: 400 }}>
              {t("review.correct_answer", { answer: String(result.correct_response) })}
            </p>
          )}
          <div style={{ display: "flex", gap: 8 }}>
            {!result.correct && (
              <button className="btn btn-secondary btn-block" onClick={handleRetry} disabled={submitting}>
                {t("review.try_again")}
              </button>
            )}
            <button className="btn btn-block" onClick={handleContinue}>
              {t("review.continue")}
            </button>
          </div>
        </div>
      )}
      <div style={{ marginTop: 12, textAlign: "center" }}>
        <ReportIssueButton exerciseId={current.id} lastResponse={lastResponse} />
      </div>
    </div>
  );
}
