import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import { ProgressApi, ReviewApi } from "../api/endpoints";
import type { Achievement, Progress, Streak, Xp } from "../api/types";

export function HomePage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [streak, setStreak] = useState<Streak | null>(null);
  const [xp, setXp] = useState<Xp | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [dueReviews, setDueReviews] = useState<number | null>(null);
  const [achievements, setAchievements] = useState<Achievement[]>([]);

  useEffect(() => {
    ProgressApi.streak().then(setStreak).catch(() => {});
    ProgressApi.xp().then(setXp).catch(() => {});
    ProgressApi.progress().then(setProgress).catch(() => {});
    ReviewApi.due()
      .then((due) => setDueReviews(due.due_count))
      .catch(() => {});
    ProgressApi.achievements()
      .then((all) => setAchievements(all.filter((a) => a.earned)))
      .catch(() => {});
  }, []);

  const inProgressLesson = progress?.lesson_progress.find(
    (lp) => lp.started_at && !lp.completed_at,
  );
  const lessonsCompleted = progress?.lessons_completed ?? 0;
  const dailyGoal = xp?.daily_goal ?? 20;

  const heroTitle =
    streak && streak.streak_days > 0
      ? user?.display_name
        ? t("home.streak_title_named", { count: streak.streak_days, name: user.display_name })
        : t("home.streak_title", { count: streak.streak_days })
      : user?.display_name
        ? t("home.welcome_named", { name: user.display_name })
        : t("home.welcome");

  return (
    <div>
      {streak?.freeze_used_today && (
        <div className="card" style={{ marginBottom: 12, textAlign: "center" }}>
          <span>❄️ {t("home.streak_freeze_used")}</span>
        </div>
      )}
      <div className="home-hero">
        <h1>{heroTitle}</h1>
        <span className="muted">
          {t("home.daily_goal", { goal: dailyGoal, total: xp?.total_xp ?? "—" })}
        </span>
      </div>

      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-value">
            🔥 {streak?.streak_days ?? "—"}
            {Boolean(streak?.streak_freezes_available) && (
              <span title={t("home.streak_freeze_available")}> ❄️</span>
            )}
          </span>
          <span className="stat-label">{t("home.day_streak")}</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">⭐ {xp?.total_xp ?? "—"}</span>
          <span className="stat-label">{t("home.total_xp")}</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">✅ {lessonsCompleted}</span>
          <span className="stat-label">{t("home.lessons_completed")}</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">🏅 {achievements.length}</span>
          <span className="stat-label">{t("home.achievements")}</span>
        </div>
      </div>

      {dueReviews !== null && dueReviews > 0 && (
        <div className="card continue-card">
          <div className="continue-info">
            <h3>{t("home.review_cta_title", { count: dueReviews })}</h3>
            <span className="muted">{t("home.review_cta_body")}</span>
          </div>
          <Link className="btn" to="/review">
            {t("home.review")}
          </Link>
        </div>
      )}

      <div className="card continue-card">
        <div className="continue-info">
          <h3>{inProgressLesson ? t("home.continue_lesson") : t("home.start_learning")}</h3>
          <span className="muted">
            {inProgressLesson ? t("home.pick_up") : t("home.choose_course")}
          </span>
        </div>
        {inProgressLesson ? (
          <Link
            className={dueReviews ? "btn btn-secondary" : "btn"}
            to={`/lessons/${inProgressLesson.lesson_id}`}
          >
            {t("home.continue")}
          </Link>
        ) : (
          <Link className={dueReviews ? "btn btn-secondary" : "btn"} to="/courses">
            {t("home.learn")}
          </Link>
        )}
      </div>

      {achievements.length > 0 && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>{t("home.recent_achievements")}</h3>
          {achievements.slice(0, 5).map((a) => (
            <div key={a.id} style={{ marginBottom: 8 }}>
              <span className="badge">🏅 {a.title}</span>{" "}
              <span className="muted" style={{ fontSize: "0.85rem" }}>
                {a.description}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
