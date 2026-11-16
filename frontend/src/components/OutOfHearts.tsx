import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { GamificationApi } from "@lingo/shared/api/gamification";
import { ApiError } from "@lingo/shared/api/client";
import { GAMIFICATION_KEY, formatCountdown, useGamification } from "../lib/gamification";

/** Shown instead of a dead end when a new lesson answer is refused for 0 hearts.
 *  Practice and review are always open and earn a heart back. */
export function OutOfHearts({ onBack, onRefilled }: { onBack: () => void; onRefilled?: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const state = useGamification();
  const [now, setNow] = useState(() => Date.now());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 30_000);
    return () => window.clearInterval(id);
  }, []);

  const countdown = formatCountdown(state?.hearts.next_heart_at ?? null, now);
  const cost = state?.gems.costs.heart_refill ?? 0;
  const canRefill = !!state?.gems.enabled && cost > 0;
  const enough = (state?.gems.balance ?? 0) >= cost;

  async function refill() {
    setBusy(true);
    setError(null);
    try {
      await GamificationApi.spend("heart_refill");
      await queryClient.invalidateQueries({ queryKey: GAMIFICATION_KEY });
      onRefilled?.();
    } catch (err) {
      setError(err instanceof ApiError && err.code === "insufficient_gems" ? t("gamification.not_enough_gems", { cost }) : t("gamification.spend_error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card" role="alert" style={{ textAlign: "center" }}>
      <div style={{ fontSize: "3rem" }} aria-hidden="true">🤍</div>
      <h2>{t("gamification.out_of_hearts_title")}</h2>
      <p className="muted">{t("gamification.out_of_hearts_body")}</p>
      <p className="muted">{countdown ? t("gamification.next_heart_in", { time: countdown }) : t("gamification.next_heart_soon")}</p>
      <Link className="btn btn-block" to="/practice">
        {t("gamification.practice_instead")}
      </Link>
      <Link className="btn btn-secondary btn-block" style={{ marginTop: 8 }} to="/review">
        {t("gamification.review_instead")}
      </Link>
      {canRefill && (
        <button type="button" className="btn btn-secondary btn-block" style={{ marginTop: 8 }} disabled={busy || !enough} onClick={refill}>
          {t("gamification.refill_with_gems", { cost })}
        </button>
      )}
      {canRefill && !enough && <p className="muted">{t("gamification.not_enough_gems", { cost })}</p>}
      {error && (
        <p className="form-error" role="status">
          {error}
        </p>
      )}
      <button type="button" className="btn btn-secondary btn-block" style={{ marginTop: 8 }} onClick={onBack}>
        {t("gamification.back")}
      </button>
    </div>
  );
}
