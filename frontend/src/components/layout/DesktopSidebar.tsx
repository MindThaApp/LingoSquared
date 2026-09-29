import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CheckCircle, Flame, Star } from "lucide-react";
import { ProgressApi, ReviewApi } from "@lingo/shared/api/endpoints";
import type { LessonProgress } from "@lingo/shared/api/types";
import { useAuth } from "../../auth/AuthContext";
import { learnPath } from "../../lib/activeCourse";

// Right-hand sidebar for Home + course pages. Hidden by CSS below 1024px
// (.desktop-sidebar), so phones render exactly as before. Reuses HomePage's
// query keys/fetchers verbatim (["streak"], ["xp"], ["progress"],
// ["reviews-due"], ["quests"]) so react-query dedupes -- no new requests.
export function DesktopSidebar() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const streakQuery = useQuery({ queryKey: ["streak"], queryFn: ProgressApi.streak });
  const xpQuery = useQuery({ queryKey: ["xp"], queryFn: ProgressApi.xp });
  const progressQuery = useQuery({ queryKey: ["progress"], queryFn: ProgressApi.progress });
  const dueQuery = useQuery({ queryKey: ["reviews-due"], queryFn: ReviewApi.due });
  const questsQuery = useQuery({ queryKey: ["quests"], queryFn: ProgressApi.quests });

  const streak = streakQuery.data;
  const xp = xpQuery.data;
  const dueReviews = dueQuery.data?.due_count ?? null;
  const quests = questsQuery.data?.quests ?? [];

  // Same "most recently started unfinished lesson" rule as HomePage.
  const inProgressLesson = (progressQuery.data?.lesson_progress ?? [])
    .filter((lp) => lp.started_at && !lp.completed_at)
    .reduce<LessonProgress | undefined>((best, lp) => {
      const ts = Date.parse(lp.started_at ?? "");
      const bestTs = best ? Date.parse(best.started_at ?? "") : -Infinity;
      return !best || (Number.isNaN(bestTs) ? -Infinity : bestTs) < (Number.isNaN(ts) ? -Infinity : ts)
        ? lp
        : best;
    }, undefined);

  const dailyGoal = xp?.daily_goal ?? 20;
  const xpToday = xp?.xp_today ?? 0;
  const goalMet = xp != null && dailyGoal > 0 && xpToday >= dailyGoal;
  const goalPct = dailyGoal > 0 ? Math.min(100, Math.max(0, (xpToday / dailyGoal) * 100)) : 0;

  return (
    <aside className="desktop-sidebar" aria-label={t("nav.sidebar")}>
      <div className="card desktop-sidebar-next">
        <h3>{t("nav.next_lesson")}</h3>
        <p className="muted">{inProgressLesson ? t("home.restart_hint") : t("home.choose_course")}</p>
        <Link
          className="btn btn-block"
          to={inProgressLesson ? `/lessons/${inProgressLesson.lesson_id}` : learnPath(user?.id)}
        >
          {inProgressLesson ? t("home.restart") : t("home.learn")}
        </Link>
      </div>

      <div className="card">
        <div className="desktop-sidebar-stats">
          <span className="desktop-sidebar-stat" data-testid="sidebar-streak">
            <Flame size={18} className="stat-flame" aria-hidden="true" /> {streak?.streak_days ?? "—"}
            <span className="muted"> {t("home.day_streak")}</span>
          </span>
          <span className="desktop-sidebar-stat" data-testid="sidebar-xp-today">
            <Star size={18} className="stat-xp" aria-hidden="true" /> {xpQuery.isError ? "—" : xpToday}
            <span className="muted"> {t("nav.xp_today")}</span>
          </span>
        </div>
        {!xpQuery.isError && (
          <div style={{ marginTop: 12 }}>
            <span className="muted" style={{ fontSize: "0.85rem", display: "flex", alignItems: "center", gap: 6 }}>
              {goalMet ? (
                <>
                  <CheckCircle size={16} style={{ color: "var(--correct)", flexShrink: 0 }} aria-hidden="true" />
                  {t("home.daily_goal_done", { earned: xpToday })}
                </>
              ) : (
                t("home.daily_goal_progress", { earned: xpToday, goal: dailyGoal })
              )}
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
      </div>

      <div className="card">
        <h3>{t("nav.due_reviews")}</h3>
        {dueReviews === null ? (
          <p className="muted">—</p>
        ) : dueReviews > 0 ? (
          <>
            <p className="muted">{t("home.review_cta_title", { count: dueReviews })}</p>
            <Link className="btn btn-secondary btn-block" to="/review">
              {t("home.review")}
            </Link>
          </>
        ) : (
          <p className="muted">{t("nav.nothing_due")}</p>
        )}
      </div>

      {quests.length > 0 && (
        <div className="card">
          <h3>{t("home.daily_quests")}</h3>
          {quests.map((quest) => {
            const pct = quest.target > 0 ? Math.min(100, Math.max(0, (quest.progress / quest.target) * 100)) : 0;
            return (
              <div key={quest.code} style={{ marginBottom: 10, opacity: quest.completed ? 0.6 : 1 }}>
                <div style={{ fontWeight: 700, fontSize: "0.9rem" }}>
                  {quest.completed && (
                    <CheckCircle
                      size={14}
                      style={{ color: "var(--correct)", marginInlineEnd: 4, verticalAlign: -2 }}
                      aria-label={t("home.quest_completed")}
                    />
                  )}
                  {t(`quests.${quest.code}.title`, { defaultValue: quest.title })}
                </div>
                <div className="progress-track" style={{ marginTop: 4 }}>
                  <div className="progress-fill" style={{ width: `${pct}%` }} />
                </div>
                <span className="muted" style={{ fontSize: "0.75rem" }}>
                  {t("home.quest_progress", { progress: quest.progress, target: quest.target })}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </aside>
  );
}
