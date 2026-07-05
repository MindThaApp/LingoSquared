import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CatalogApi, PracticeApi, ProgressApi } from "../api/endpoints";
import { ExerciseRenderer } from "../components/exercises/ExerciseRenderer";
import type {
  AnswerResponse,
  CourseDetail,
  PracticeAnswerResult,
  PracticeItem,
} from "../api/types";

const BATCH_SIZE = 10;
const PREFETCH_THRESHOLD = 3;

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

  async function handleAnswer(response: AnswerResponse) {
    setSubmitting(true);
    try {
      const res = await PracticeApi.answer(item.id, response);
      setResult(res);
      onAnswered(res.correct, res.xp_awarded);
    } catch {
      // Item may have expired mid-scroll (or already been answered/is
      // foreign to this user) — the card can't be retried, so resolve it
      // visibly instead of silently re-enabling a dead exercise.
      setUnavailable(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card practice-card">
      <ExerciseRenderer
        exercise={{ id: item.id, type: item.type, order: 0, prompt: item.prompt }}
        onAnswer={handleAnswer}
        disabled={submitting || Boolean(result) || unavailable}
      />
      {result && (
        <div className={`feedback-banner ${result.correct ? "correct" : "incorrect"}`}>
          <p style={{ margin: 0 }}>
            {result.correct
              ? t("practice.correct", { xp: result.xp_awarded })
              : t("lesson_runner.correct_answer", {
                  answer: String(result.correct_response),
                })}
          </p>
        </div>
      )}
      {unavailable && (
        <div className="feedback-banner">
          <p style={{ margin: 0 }}>{t("practice.item_unavailable")}</p>
        </div>
      )}
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

      {exhausted && items.length > 0 && (
        <p className="muted" style={{ textAlign: "center" }}>
          {t("practice.exhausted")}
        </p>
      )}

      {xpToast !== null && (
        <div className="practice-xp-toast stat-xp">+{xpToast} XP</div>
      )}
    </div>
  );
}
