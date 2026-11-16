import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { GamificationApi } from "@lingo/shared/api/gamification";
import { useGamification } from "../lib/gamification";

export function LeaderboardPage() {
  const { t } = useTranslation();
  const state = useGamification();
  const enabled = !!state?.leaderboard.enabled;
  const query = useQuery({
    queryKey: ["leaderboard"],
    queryFn: GamificationApi.leaderboard,
    enabled,
    retry: false,
  });

  if (state && !enabled) {
    return (
      <div>
        <h1>{t("gamification.leaderboard_title")}</h1>
        <p className="muted">{t("gamification.leaderboard_unavailable")}</p>
      </div>
    );
  }
  const board = query.data;
  return (
    <div>
      <h1>{t("gamification.leaderboard_title")}</h1>
      <p className="muted">{t("gamification.leaderboard_intro")}</p>
      {query.isError && (
        <div className="feedback-banner error" role="alert">
          <p style={{ margin: "0 0 10px" }}>{t("gamification.leaderboard_error")}</p>
          <button className="btn btn-block" onClick={() => query.refetch()}>
            {t("common.retry")}
          </button>
        </div>
      )}
      {query.isLoading && <p className="muted" role="status">{t("common.loading")}</p>}
      {board && (
        <>
          {board.opted_out ? (
            <p className="muted">
              {t("gamification.leaderboard_opted_out")} <Link to="/profile">{t("nav.profile")}</Link>
            </p>
          ) : board.me && board.me.rank !== null ? (
            <p style={{ fontWeight: 700 }}>{t("gamification.leaderboard_your_rank", { rank: board.me.rank, xp: board.me.xp })}</p>
          ) : (
            <p className="muted">{t("gamification.leaderboard_no_xp")}</p>
          )}
          {board.entries.length === 0 ? (
            <p className="muted">{t("gamification.leaderboard_empty")}</p>
          ) : (
            <ol className="card" style={{ listStyle: "none", margin: 0, padding: 12 }} aria-label={t("gamification.leaderboard_title")}>
              {board.entries.map((entry, i) => (
                <li
                  key={`${entry.rank}-${i}`}
                  aria-current={entry.is_me ? "true" : undefined}
                  style={{ display: "flex", justifyContent: "space-between", gap: 12, padding: "6px 0", fontWeight: entry.is_me ? 700 : 400 }}
                >
                  <span>
                    {entry.rank}. {entry.display_name}
                    {entry.is_me ? ` (${t("gamification.leaderboard_you")})` : ""}
                  </span>
                  <span>{entry.xp} XP</span>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </div>
  );
}
