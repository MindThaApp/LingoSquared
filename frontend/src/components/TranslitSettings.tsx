import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import { clearTranslitPreference, getTranslitPreference, setTranslitPreference } from "../lib/translitPreference";

/**
 * Profile card: "Show pronunciation" default. Unset follows the course level (on at A1, off
 * from A2); choosing here pins it for this account on this device. The lesson view has a
 * quick toggle too.
 */
export function TranslitSettings() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const uid = useId();
  const stored = getTranslitPreference(userId);
  const [mode, setMode] = useState<"auto" | "on" | "off">(stored === null ? "auto" : stored ? "on" : "off");
  return (
    <div className="card" style={{ marginTop: 16 }}>
      <h3 style={{ marginTop: 0 }}>{t("translit.settings_title")}</h3>
      <label htmlFor={`${uid}-mode`} style={{ display: "block", marginBottom: 6 }}>
        {t("translit.show_label")}
      </label>
      <select
        id={`${uid}-mode`}
        value={mode}
        onChange={(e) => {
          const next = e.target.value as "auto" | "on" | "off";
          setMode(next);
          if (next === "auto") clearTranslitPreference(userId);
          else setTranslitPreference(userId, next === "on");
        }}
      >
        <option value="auto">{t("translit.mode_auto")}</option>
        <option value="on">{t("translit.mode_on")}</option>
        <option value="off">{t("translit.mode_off")}</option>
      </select>
      <p className="muted" style={{ margin: "8px 0 0", fontSize: "0.85rem" }}>{t("translit.settings_hint")}</p>
    </div>
  );
}
