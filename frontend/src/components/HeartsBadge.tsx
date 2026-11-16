import { useTranslation } from "react-i18next";
import { useGamification } from "../lib/gamification";

/** Hearts left in the lesson header. Renders nothing unless the server has hearts on. */
export function HeartsBadge() {
  const { t } = useTranslation();
  const state = useGamification();
  if (!state?.hearts.enabled) return null;
  const { hearts, max_hearts } = state.hearts;
  const label = t("gamification.hearts_label", { count: hearts, max: max_hearts });
  return (
    <span className="stat-xp" style={{ fontWeight: 700, whiteSpace: "nowrap" }} role="img" aria-label={label} title={label}>
      <span aria-hidden="true">{hearts > 0 ? "❤️" : "🤍"}</span> {hearts}
    </span>
  );
}
