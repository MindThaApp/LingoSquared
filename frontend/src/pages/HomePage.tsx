import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CheckCircle, Flame, Medal, Snowflake, Star } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { ProgressApi, ReviewApi } from "../api/endpoints";

export function HomePage() {
  const { t } = useTranslation();
  const { user } = useAuth();

  const streakQuery = useQuery({ queryKey: ["streak"], queryFn: ProgressApi.streak });
  const xpQuery = useQuery({ queryKey: ["xp"], queryFn: ProgressApi.xp });
  const progressQuery = useQuery({ queryKey: ["progress"], queryFn: ProgressApi.progress });
  const dueQuery = useQuery({ queryKey: ["reviews-due"], queryFn: ReviewApi.due });
  const achievementsQuery = useQuery({
    queryKey: ["achievements"],
    queryFn: ProgressApi.achievements,
  });
  // Progress/target here are always computed live server-side and XP is
  // awarded at most once per quest per day (server-enforced) — refetching
  // this on every Home load is safe and never double-pays.
  const questsQuery = useQuery({ queryKey: ["quests"], queryFn: ProgressApi.quests });

  const streak = streakQuery.data;
  const xp = xpQuery.data;
  const progress = progressQuery.data;
  const dueReviews = dueQuery.data?.due_count ?? null;
  const achievements = (achievementsQuery.data ?? []).filter((a) => a.earned);
  const quests = questsQuery.data?.quests ?? [];
  const allQuestsComplete = quests.length > 0 && quests.every((q) => q.completed);

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
          <span>
            <Snowflake size={16} style={{ color: "var(--accent)", verticalAlign: -3 }} />{" "}
            {t("home.streak_freeze_used")}
          </span>
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
            <Flame size={20} className="stat-flame" style={{ verticalAlign: -3 }} />{" "}
            {streak?.streak_days ?? "—"}
            {Boolean(streak?.streak_freezes_available) && (
              <Snowflake
                size={16}
                style={{ color: "var(--accent)", verticalAlign: -2, marginLeft: 4 }}
                aria-label={t("home.streak_freeze_available")}
              />
            )}
          </span>
          <span className="stat-label">{t("home.day_streak")}</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">
            <Star size={20} className="stat-xp" style={{ verticalAlign: -3 }} /> {xp?.total_xp ?? "—"}
          </span>
          <span className="stat-label">{t("home.total_xp")}</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">
            <CheckCircle size={20} style={{ color: "var(--correct)", verticalAlign: -3 }} />{" "}
            {lessonsCompleted}
          </span>
          <span className="stat-label">{t("home.lessons_completed")}</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">
            <Medal size={20} style={{ color: "var(--gold)", verticalAlign: -3 }} /> {achievements.length}
          </span>
          <span className="stat-label">{t("home.achievements")}</span>
        </div>
      </div>

      {quests.length > 0 && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>{t("home.daily_quests")}</h3>
          {allQuestsComplete ? (
            <p className="muted" style={{ margin: 0 }}>{t("home.daily_quests_all_complete")}</p>
          ) : (
            quests.map((quest) => {
              const pct = quest.target > 0
                ? Math.min(100, Math.max(0, (quest.progress / quest.target) * 100))
                : 0;
              return (
                <div
                  key={quest.code}
                  style={{
                    marginBottom: 12,
                    opacity: quest.completed ? 0.6 : 1,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: 8,
                      marginBottom: 4,
                    }}
                  >
                    <span style={{ fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
                      {quest.completed && (
                        <CheckCircle
                          size={16}
                          style={{ color: "var(--correct)" }}
                          aria-label={t("home.quest_completed")}
                        />
                      )}
                      {quest.title}
                    </span>
                    <span className="badge">{t("home.quest_xp_reward", { xp: quest.xp_reward })}</span>
                  </div>
                  <span className="muted" style={{ fontSize: "0.85rem" }}>
                    {quest.description}
                  </span>
                  <div className="progress-track" style={{ marginTop: 6 }}>
                    <div className="progress-fill" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="muted" style={{ fontSize: "0.75rem" }}>
                    {t("home.quest_progress", { progress: quest.progress, target: quest.target })}
                  </span>
                </div>
              );
            })
          )}
        </div>
      )}

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
              <span className="badge">
                <Medal size={14} style={{ color: "var(--gold)", verticalAlign: -2 }} /> {a.title}
              </span>{" "}
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
