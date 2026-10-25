import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { setCrashConsent } from "../lib/crashConsent";
import { answerPendingCrash, subscribePendingCrash, type PendingCrash } from "../lib/sentry";

// Shown only in "Ask" mode, after an unhandled error. Nothing has been
// sent at this point; the buttons decide.
export function CrashReportPrompt() {
  const { t } = useTranslation();
  const [pending, setPending] = useState<PendingCrash | null>(null);

  useEffect(() => subscribePendingCrash(setPending), []);

  if (!pending) return null;

  return (
    <div
      role="alertdialog"
      aria-labelledby="crash-prompt-title"
      aria-describedby="crash-prompt-body"
      className="card crash-prompt"
    >
      <strong id="crash-prompt-title">{t("crash_report.prompt_title")}</strong>
      <p id="crash-prompt-body" className="muted" style={{ margin: "4px 0 10px" }}>
        {t("crash_report.prompt_body")}
      </p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button type="button" className="btn" onClick={() => answerPendingCrash(true)}>
          {t("crash_report.send")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => answerPendingCrash(false)}>
          {t("crash_report.not_now")}
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => {
            setCrashConsent("never");
            answerPendingCrash(false);
          }}
        >
          {t("crash_report.never_ask")}
        </button>
      </div>
    </div>
  );
}
