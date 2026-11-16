import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { GamificationApi } from "@lingo/shared/api/gamification";
import { ApiError } from "@lingo/shared/api/client";
import { GAMIFICATION_KEY, useGamification } from "../lib/gamification";

/** Profile card: gem balance + streak freeze, and the leaderboard privacy opt-out.
 *  Each half only shows when its server flag is on. */
export function GamificationSettings() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const state = useGamification();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  if (!state || (!state.gems.enabled && !state.leaderboard.enabled)) return null;

  const freezeCost = state.gems.costs.streak_freeze ?? 0;

  async function buyFreeze() {
    setBusy(true);
    setMessage(null);
    try {
      await GamificationApi.spend("streak_freeze");
      await queryClient.invalidateQueries({ queryKey: GAMIFICATION_KEY });
      await queryClient.invalidateQueries({ queryKey: ["streak"] });
    } catch (err) {
      if (err instanceof ApiError && err.code === "insufficient_gems") setMessage(t("gamification.not_enough_gems", { cost: freezeCost }));
      else if (err instanceof ApiError && err.code === "freeze_limit") setMessage(t("gamification.freeze_limit"));
      else setMessage(t("gamification.spend_error"));
    } finally {
      setBusy(false);
    }
  }

  async function setShown(shown: boolean) {
    setBusy(true);
    setMessage(null);
    try {
      await GamificationApi.setLeaderboardOptOut(!shown);
      await queryClient.invalidateQueries({ queryKey: GAMIFICATION_KEY });
      await queryClient.invalidateQueries({ queryKey: ["leaderboard"] });
    } catch {
      setMessage(t("gamification.spend_error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card" data-testid="gamification-settings">
      {state.gems.enabled && (
        <>
          <h2 style={{ marginTop: 0 }}>{t("gamification.gems_title")}</h2>
          <p style={{ fontWeight: 700 }}>
            <span aria-hidden="true">💎</span> {t("gamification.gems_label", { count: state.gems.balance })}
          </p>
          <p className="muted">{t("gamification.gems_body")}</p>
          <button type="button" className="btn btn-secondary" disabled={busy || state.gems.balance < freezeCost} onClick={buyFreeze}>
            {t("gamification.freeze_buy", { cost: freezeCost })}
          </button>
        </>
      )}
      {state.leaderboard.enabled && (
        <>
          <h2 style={{ marginTop: state.gems.enabled ? 24 : 0 }}>{t("gamification.privacy_title")}</h2>
          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={!state.leaderboard.opted_out}
              disabled={busy}
              onChange={(e) => setShown(e.target.checked)}
            />
            {t("gamification.privacy_body")}
          </label>
        </>
      )}
      {message && (
        <p className="form-error" role="status">
          {message}
        </p>
      )}
    </div>
  );
}
