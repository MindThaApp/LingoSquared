import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ProgressApi } from "@lingo/shared/api/endpoints";
import { isGuestUser, useAuth } from "../auth/AuthContext";
import { VoiceSettings } from "../components/VoiceSettings";
import { SpeechSpeedSettings } from "../components/SpeechSpeedSettings";

export function ProfilePage() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const isGuest = isGuestUser(user);
  const progressQuery = useQuery({ queryKey: ["progress"], queryFn: ProgressApi.progress });
  const streakQuery = useQuery({ queryKey: ["streak"], queryFn: ProgressApi.streak });
  const xpQuery = useQuery({ queryKey: ["xp"], queryFn: ProgressApi.xp });
  const achievementsQuery = useQuery({
    queryKey: ["achievements"],
    queryFn: ProgressApi.achievements,
  });

  return (
    <div>
      <div className="home-hero">
        <h1>{user?.display_name || user?.email}</h1>
      </div>

      {isGuest && (
        <div className="form-error" style={{ background: "var(--surface-2)", color: "var(--text-soft)" }}>
          {t("profile.guest_notice")}
        </div>
      )}

      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-value">⭐ {xpQuery.data?.total_xp ?? "—"}</span>
          <span className="stat-label">{t("profile.total_xp")}</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">🔥 {streakQuery.data?.streak_days ?? "—"}</span>
          <span className="stat-label">{t("profile.day_streak")}</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{xpQuery.data?.daily_goal ?? "—"}</span>
          <span className="stat-label">{t("profile.daily_goal")}</span>
        </div>
      </div>

      {progressQuery.data && (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>{t("profile.progress")}</h2>
          <p className="muted">
            {t("profile.lessons_completed", {
              completed: progressQuery.data.lessons_completed,
              started: progressQuery.data.lessons_started,
            })}
          </p>
          {progressQuery.data.skill_progress.map((skill) => (
            <div key={skill.course_id} style={{ marginBottom: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span>{t("course_units.lesson_count", { count: skill.completed_lessons })}</span>
                <span className="muted">
                  {t("profile.mastery", { pct: Math.round(skill.mastery * 100) })}
                </span>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${Math.round(skill.mastery * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <h2 style={{ marginTop: 0 }}>{t("profile.achievements")}</h2>
        {/* Without the error branch, a failed achievements fetch silently
            renders the "no achievements yet" empty state -- misleading for a
            user who has earned some. */}
        {achievementsQuery.isError ? (
          <div className="feedback-banner error">
            <p style={{ margin: "0 0 10px" }}>{t("profile.achievements_fetch_error")}</p>
            <button className="btn btn-block" onClick={() => achievementsQuery.refetch()}>
              {t("common.retry")}
            </button>
          </div>
        ) : achievementsQuery.data?.length ? (
          achievementsQuery.data.map((achievement) => (
            <div key={achievement.id} style={{ marginBottom: 8, opacity: achievement.earned ? 1 : 0.4 }}>
              <span className="badge">🏅 {achievement.title}</span>{" "}
              <span className="muted" style={{ fontSize: "0.85rem" }}>
                {achievement.description}
              </span>
            </div>
          ))
        ) : (
          <p className="muted">{t("profile.no_achievements")}</p>
        )}
      </div>

      <SpeechSpeedSettings />
      <VoiceSettings />

      <button className="btn btn-secondary btn-block" onClick={logout} style={{ marginTop: 8 }}>
        {t("profile.logout")}
      </button>
    </div>
  );
}
