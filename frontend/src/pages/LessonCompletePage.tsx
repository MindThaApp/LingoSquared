import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { CatalogApi, LessonApi, ProgressApi } from "@lingo/shared/api/endpoints";
import type { LessonCompleteResult } from "@lingo/shared/api/types";
import { useAuth } from "../auth/AuthContext";
import { getActiveCourse } from "../lib/activeCourse";
import { computeNextItem, findNextUnit } from "../lib/nextLesson";
import { PushPrompt } from "../components/PushPrompt";
import { MissedWordsSummary } from "./LessonRunnerPage";

const CONFETTI_COLORS = ["var(--accent)", "var(--gold)", "var(--correct)"];
const CONFETTI_COUNT = 18;

// Counts up from 0 to `target` over `durationMs`, driven by
// requestAnimationFrame rather than setInterval so it stays smooth and
// self-cancels cleanly on unmount. `active` gates it to a real celebration
// mount (see the `celebrate` comment below) -- when false it just renders
// the final value immediately, no animation.
function useCountUp(target: number, active: boolean, durationMs = 700): number {
  const [value, setValue] = useState(active ? 0 : target);

  useEffect(() => {
    if (!active || target <= 0) {
      setValue(target);
      return;
    }
    let raf = 0;
    const start = performance.now();
    function tick(now: number) {
      const progress = Math.min(1, (now - start) / durationMs);
      setValue(Math.round(target * progress));
      if (progress < 1) raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // One-shot mount animation -- intentionally not re-running on every
    // `target`/`durationMs` identity (they're stable per mount here).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  return value;
}

// 15-20 CSS-only confetti particles, no external library. Randomized once
// per mount (useMemo, empty deps) so re-renders don't reshuffle/restart it.
function Confetti() {
  const pieces = useMemo(
    () =>
      Array.from({ length: CONFETTI_COUNT }, (_, i) => ({
        left: `${Math.min(97, Math.max(1, (i / CONFETTI_COUNT) * 100 + (Math.random() * 8 - 4)))}%`,
        delay: `${(Math.random() * 0.5).toFixed(2)}s`,
        rotate: `${Math.round(Math.random() * 60 - 30)}deg`,
        color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
      })),
    [],
  );
  return (
    <>
      {pieces.map((piece, i) => (
        <span
          key={i}
          className="confetti-piece"
          aria-hidden="true"
          style={
            {
              "--confetti-left": piece.left,
              "--confetti-delay": piece.delay,
              "--confetti-rotate": piece.rotate,
              "--confetti-color": piece.color,
            } as CSSProperties
          }
        />
      ))}
    </>
  );
}

export function LessonCompletePage() {
  const { t } = useTranslation();
  const location = useLocation();
  const { lessonId = "" } = useParams();
  const { user } = useAuth();
  const courseId = getActiveCourse(user?.id);
  const state = location.state as
    | {
        completion: LessonCompleteResult;
        totalXp: number;
        missedWords?: { text: string; languageCode?: string }[];
      }
    | null;

  // Route `state` is only ever populated by LessonRunnerPage.finishLesson's
  // navigate() call right after a real POST /lessons/{id}/complete -- a
  // browser refresh, back/forward revisit, or direct URL hit loses it
  // entirely (react-router state isn't persisted across a hard reload), so
  // gating the celebration on `state` being present naturally limits it to
  // a genuine, fresh completion and never replays on a retry/revisit.
  const celebrate = Boolean(state);
  const xp = useCountUp(state?.completion.xp_awarded ?? 0, celebrate);

  // Same query keys as HomePage/NavBar so the invalidation finishLesson()
  // already does refreshes these too.
  const streakQuery = useQuery({ queryKey: ["streak"], queryFn: ProgressApi.streak });
  const xpQuery = useQuery({ queryKey: ["xp"], queryFn: ProgressApi.xp });

  // "Next" is computed from existing endpoints only: lesson -> its unit_id,
  // the course's units, that unit's lessons, and (only when this was the last
  // lesson) the next unit's lessons.
  const lessonQuery = useQuery({
    queryKey: ["lesson", lessonId],
    queryFn: () => LessonApi.get(lessonId),
    enabled: !!lessonId,
  });
  const unitId = lessonQuery.data?.unit_id ?? "";
  const unitsQuery = useQuery({
    queryKey: ["units", courseId],
    queryFn: () => CatalogApi.units(courseId ?? ""),
    enabled: !!courseId,
  });
  const unitLessonsQuery = useQuery({
    queryKey: ["lessons", unitId],
    queryFn: () => CatalogApi.lessons(unitId),
    enabled: !!unitId,
  });
  const nextUnit =
    unitsQuery.data && unitId ? findNextUnit(unitsQuery.data, unitId) : null;
  const unitLessons = unitLessonsQuery.data;
  const isLastInUnit =
    !!unitLessons &&
    [...unitLessons].sort((a, b) => a.order - b.order).at(-1)?.id === lessonId;
  const nextUnitId = isLastInUnit && nextUnit && !nextUnit.locked ? nextUnit.id : "";
  const nextUnitLessonsQuery = useQuery({
    queryKey: ["lessons", nextUnitId],
    queryFn: () => CatalogApi.lessons(nextUnitId),
    enabled: !!nextUnitId,
  });
  const nextItem =
    unitsQuery.data && unitLessons
      ? computeNextItem(unitsQuery.data, unitId, unitLessons, nextUnitLessonsQuery.data, lessonId)
      : null;
  const courseHref = courseId ? `/courses/${courseId}` : "/courses";

  const streakDays = streakQuery.data?.streak_days ?? 0;
  const dailyGoal = xpQuery.data?.daily_goal ?? 0;
  const xpToday = xpQuery.data?.xp_today ?? 0;
  const goalMet = xpQuery.data != null && dailyGoal > 0 && xpToday >= dailyGoal;
  const goalPct = dailyGoal > 0 ? Math.min(100, Math.max(0, (xpToday / dailyGoal) * 100)) : 0;

  return (
    <div
      style={{ textAlign: "center", paddingTop: 40 }}
      className={celebrate ? "lesson-complete-celebration" : undefined}
    >
      {celebrate && <Confetti />}
      <div style={{ fontSize: "4rem", marginBottom: 8 }}>🎉</div>
      <h1>{t("lesson_complete.title")}</h1>
      {state ? (
        <div className="stat-grid" style={{ maxWidth: 360, margin: "20px auto" }}>
          <div className="stat-card">
            <span className={celebrate ? "stat-value xp-pop-value" : "stat-value"}>⭐ {xp}</span>
            <span className="stat-label">{t("lesson_complete.xp_earned")}</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">
              {Math.round(state.completion.accuracy * 100)}%
            </span>
            <span className="stat-label">{t("lesson_complete.accuracy")}</span>
          </div>
        </div>
      ) : (
        <p className="muted">{t("lesson_complete.finished")}</p>
      )}
      {state?.missedWords && <MissedWordsSummary words={state.missedWords} />}
      {streakDays > 0 && (
        <p style={{ fontWeight: 700, margin: "12px 0 4px" }}>
          <span className="stat-flame">🔥</span> {t("lesson_complete.streak", { count: streakDays })}
        </p>
      )}
      {xpQuery.data && dailyGoal > 0 && (
        <div style={{ maxWidth: 360, margin: "8px auto" }}>
          <span className="muted" style={{ fontSize: "0.9rem" }}>
            {goalMet
              ? t("home.daily_goal_done", { earned: xpToday })
              : t("home.daily_goal_progress", { earned: xpToday, goal: dailyGoal })}
          </span>
          <div
            className="progress-track"
            style={{ marginTop: 6 }}
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={dailyGoal}
            aria-valuenow={Math.min(xpToday, dailyGoal)}
            aria-label={t("home.daily_goal_progress", { earned: xpToday, goal: dailyGoal })}
          >
            <div
              className="progress-fill"
              style={{ width: `${goalPct}%`, ...(goalMet ? { background: "var(--correct)" } : {}) }}
            />
          </div>
        </div>
      )}
      {/* Notification permission is only ever offered here, right after a
          finished lesson (a moment of value), never on first load. */}
      <div style={{ maxWidth: 360, margin: "16px auto 0", textAlign: "start" }}>
        <PushPrompt />
      </div>
      <div
        style={{
          display: "flex",
          gap: 12,
          justifyContent: "center",
          flexWrap: "wrap",
          marginTop: 24,
        }}
      >
        {nextItem?.kind === "lesson" && (
          <Link
            className="btn"
            to={`/lessons/${nextItem.lessonId}`}
            state={courseId ? { courseId } : undefined}
          >
            {t("lesson_complete.next_lesson")}
          </Link>
        )}
        {nextItem?.kind === "checkpoint" && (
          <Link
            className="btn"
            to={`/units/${nextItem.unitId}/checkpoint`}
            state={courseId ? { courseId } : undefined}
          >
            {t("lesson_complete.next_checkpoint")}
          </Link>
        )}
        <Link className={nextItem ? "btn btn-secondary" : "btn"} to="/review">
          {t("lesson_complete.review")}
        </Link>
        <Link className="btn btn-secondary" to={courseHref}>
          {courseId ? t("lesson_complete.back_to_course") : t("lesson_complete.back_to_courses")}
        </Link>
      </div>
    </div>
  );
}
