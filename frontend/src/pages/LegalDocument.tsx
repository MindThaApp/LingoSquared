import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

// Privacy and Terms are English-only. The notice is shown (in the UI
// language) when the UI isn't English, and the English body is explicitly
// tagged lang="en" dir="ltr" so it renders correctly inside an RTL UI.
export function LegalDocument({ children }: { children: ReactNode }) {
  const { t, i18n } = useTranslation();
  const isEnglish = (i18n.language ?? "en").toLowerCase().split("-")[0] === "en";
  return (
    <div className="card" style={{ maxWidth: 720, margin: "24px auto" }}>
      {!isEnglish && (
        <p className="muted" role="note" data-testid="legal-english-only-notice">
          {t("legal.english_only_notice")}
        </p>
      )}
      <div lang="en" dir="ltr" data-testid="legal-body">
        {children}
      </div>
    </div>
  );
}
