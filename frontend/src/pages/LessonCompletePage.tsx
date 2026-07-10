import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { LessonCompleteResult } from "@lingo/shared/api/types";
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
      <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 24 }}>
        <Link className="btn btn-secondary" to="/courses">
          {t("lesson_complete.back_to_courses")}
        </Link>
        <Link className="btn" to="/review">
          {t("lesson_complete.go_to_review")}
        </Link>
      </div>
    </div>
  );
}
