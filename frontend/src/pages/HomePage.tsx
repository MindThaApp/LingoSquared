import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CheckCircle, Flame, Medal, Snowflake, Star } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { ProgressApi, ReviewApi } from "@lingo/shared/api/endpoints";
import { PushPrompt } from "../components/PushPrompt";

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

  // Every number on this page comes from its own request, and each one
  // `?? `-falls-back to 0/— . Without an explicit failure signal a fully-down
  // backend rendered a completely plausible "0 XP, 0-day streak, nothing due"
  // home screen — silently LYING rather than obviously failing, which is
  // worse than any blank state. So: one honest banner whenever any of the six
  // failed, and every individual stat shows "—" (unknown) instead of a
  // fabricated 0 when ITS OWN query is the one that failed. A genuine zero
  // from a brand-new account still renders as a real 0 — a legitimate zero is
  // never turned into an error.
  const loadFailed =
    streakQuery.isError ||
    xpQuery.isError ||
    progressQuery.isError ||
    dueQuery.isError ||
    achievementsQuery.isError ||
    questsQuery.isError;

  function retryFailedQueries() {
    if (streakQuery.isError) void streakQuery.refetch();
    if (xpQuery.isError) void xpQuery.refetch();
    if (progressQuery.isError) void progressQuery.refetch();
    if (dueQuery.isError) void dueQuery.refetch();
    if (achievementsQuery.isError) void achievementsQuery.refetch();
    if (questsQuery.isError) void questsQuery.refetch();
  }

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
  const xpToday = xp?.xp_today ?? 0;
  // Only claim the goal is met once real data has arrived — a 0-goal
  // account would otherwise flash "done" while the query is loading.
  const goalMet = xp != null && dailyGoal > 0 && xpToday >= dailyGoal;
  const goalPct = dailyGoal > 0 ? Math.min(100, Math.max(0, (xpToday / dailyGoal) * 100)) : 0;

  // Streak-at-risk banner: shown whenever there's a streak to protect and the
  // server says today's activity hasn't happened yet (active_today is computed
  // server-side in the account's timezone day boundary — never re-derive it
  // from last_activity_date with the device clock). Deliberately NOT gated on
  // "late in the day": a local-hour heuristic would add a second clock that
  // can disagree with the server's boundary, and the message is an invitation
  // rather than an alarm, so it works as the day's nudge from the first open.
  // Complements the push-notification path (POST /admin/push/notify-streaks-
  // at-risk) for users without push enabled.
  const streakAtRisk = Boolean(streak && streak.streak_days > 0 && !streak.active_today);

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
      {loadFailed && (
        <div className="feedback-banner error" role="alert" style={{ marginBottom: 12 }}>
          <p style={{ margin: "0 0 10px" }}>{t("home.data_fetch_error")}</p>
          <button className="btn btn-block" onClick={retryFailedQueries}>
            {t("common.retry")}
          </button>
        </div>
      )}
      {streakAtRisk && (
        <div
          className="card continue-card"
          role="status"
          style={{
            marginBottom: 12,
            // Warm amber, the existing validated --almost/--almost-soft
            // contrast pair (defined for both themes) — distinct but not
            // alarming, unlike --incorrect.
            background: "var(--almost-soft)",
            borderColor: "var(--almost)",
          }}
        >
          <div className="continue-info">
            <h3 style={{ color: "var(--almost)" }}>
              <Flame size={18} className="stat-flame" style={{ verticalAlign: -3 }} />{" "}
              {t("home.streak_reminder_title", { count: streak!.streak_days })}
            </h3>
            <span style={{ color: "var(--almost)" }}>{t("home.streak_reminder_body")}</span>
          </div>
          <Link className="btn" to={(dueReviews ?? 0) > 0 ? "/review" : "/practice"}>
            {t("home.streak_reminder_cta")}
          </Link>
        </div>
      )}
      {streak?.freeze_used_today && (
        <div className="card" role="status" style={{ marginBottom: 12, textAlign: "center" }}>
          <span>
            <Snowflake size={16} style={{ color: "var(--accent)", verticalAlign: -3 }} />{" "}
            {t("home.streak_freeze_used")}
          </span>
        </div>
      )}
      <div className="home-hero">
        <h1>{heroTitle}</h1>
        {/* A failed XP fetch would otherwise render "Daily goal: 0 / 20 XP"
            with an empty bar — indistinguishable from a real day with no XP
            yet, and demoralising to someone who has actually earned it. */}
        {xpQuery.isError ? (
          <div style={{ maxWidth: 360 }}>
            <span className="muted" style={{ fontSize: "0.9rem" }}>
              {t("home.daily_goal_unavailable")}
            </span>
          </div>
        ) : (
          <div style={{ maxWidth: 360 }}>
            <span
              className="muted"
              style={{ fontSize: "0.9rem", display: "flex", alignItems: "center", gap: 6 }}
            >
              {goalMet ? (
                <>
                  <CheckCircle
                    size={16}
                    style={{ color: "var(--correct)", flexShrink: 0 }}
                    aria-hidden
                  />
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
                style={{
                  width: `${goalPct}%`,
                  ...(goalMet ? { background: "var(--correct)" } : {}),
                }}
              />
            </div>
          </div>
        )}
      </div>

      <PushPrompt />

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
            {progressQuery.isError ? "—" : lessonsCompleted}
          </span>
          <span className="stat-label">{t("home.lessons_completed")}</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">
            <Medal size={20} style={{ color: "var(--gold)", verticalAlign: -3 }} />{" "}
            {achievementsQuery.isError ? "—" : achievements.length}
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
