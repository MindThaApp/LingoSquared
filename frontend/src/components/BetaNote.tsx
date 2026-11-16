import { useTranslation } from "react-i18next";

/** Small "Beta" pill. */
export function BetaBadge({ className = "" }: { className?: string }) {
  const { t } = useTranslation();
  return (
    <span className={`beta-badge ${className}`.trim()} data-testid="beta-badge">
      {t("beta.label")}
    </span>
  );
}

/** Beta badge plus the short explanation (the global "Give feedback" button reports problems). */
export function BetaNote() {
  const { t } = useTranslation();
  return (
    <p className="beta-note muted" role="note" data-testid="beta-note">
      <BetaBadge /> {t("beta.note")}
    </p>
  );
}
