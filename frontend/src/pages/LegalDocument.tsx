import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { legalLocaleInfo, type LegalDocId } from "./legalLocales";

// Privacy and Terms are English-only. The notice is shown (in the UI
// language) when the UI isn't English, and the English body is explicitly
// tagged lang="en" dir="ltr" so it renders correctly inside an RTL UI.
export function LegalDocument({ children, doc }: { children: ReactNode; doc?: LegalDocId }) {
  const { t, i18n } = useTranslation();
  const isEnglish = (i18n.language ?? "en").toLowerCase().split("-")[0] === "en";
  const info = doc ? legalLocaleInfo(i18n.language, doc) : undefined;
  if (info?.Translated) {
    const Translated = info.Translated;
    return (
      <div className="card" style={{ maxWidth: 720, margin: "24px auto" }}>
        <div lang={info.base} dir={info.dir} data-testid="legal-body">
          <Translated />
        </div>
      </div>
    );
  }
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
