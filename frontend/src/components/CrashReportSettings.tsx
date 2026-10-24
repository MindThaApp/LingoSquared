import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { CRASH_CONSENT_VALUES, getCrashConsent, setCrashConsent, type CrashConsent } from "../lib/crashConsent";

export function CrashReportSettings() {
  const { t } = useTranslation();
  const [value, setValue] = useState<CrashConsent>(() => getCrashConsent());
  const name = useId();

  return (
    <fieldset className="card" style={{ marginTop: 16, border: "none" }}>
      <legend style={{ fontWeight: 600, padding: 0 }}>{t("crash_report.settings_title")}</legend>
      <p className="muted" style={{ marginTop: 4 }}>{t("crash_report.settings_hint")}</p>
      {CRASH_CONSENT_VALUES.map((option) => (
        <label key={option} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
          <input
            type="radio"
            name={name}
            value={option}
            checked={value === option}
            onChange={() => {
              setValue(option);
              setCrashConsent(option);
            }}
          />
          {t(`crash_report.option_${option}`)}
        </label>
      ))}
    </fieldset>
  );
}
