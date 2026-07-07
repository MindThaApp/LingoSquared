import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { CatalogApi } from "../api/endpoints";
import { speak } from "../api/tts";
import { SAMPLE_SPEECH_TEXT } from "../lib/sampleSpeechText";
import {
  DEFAULT_SPEED,
  MAX_SPEED,
  MIN_SPEED,
  getSpeedPreference,
  setSpeedPreference,
} from "../lib/ttsSpeedPreferences";
import { useStudiedLanguages } from "../lib/useStudiedLanguages";

const STEP = 0.05;

function LanguageSpeedRow({
  languageCode,
  displayName,
}: {
  languageCode: string;
  displayName: string;
}) {
  const { t } = useTranslation();
  const [speed, setSpeed] = useState(() => getSpeedPreference(languageCode));

  const handleChange = (value: number) => {
    setSpeed(value);
    setSpeedPreference(languageCode, value);
  };

  const preview = () => {
    void speak(SAMPLE_SPEECH_TEXT[languageCode] ?? displayName, languageCode);
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
      <span style={{ minWidth: 90 }}>{displayName}</span>
      <input
        type="range"
        min={MIN_SPEED}
        max={MAX_SPEED}
        step={STEP}
        value={speed}
        onChange={(e) => handleChange(Number(e.target.value))}
        style={{ flex: 1 }}
        aria-label={t("speech_speed_settings.slider_label", { language: displayName })}
      />
      <span className="muted" style={{ minWidth: 44, textAlign: "right" }}>
        {Math.round(speed * 100)}%
      </span>
      {speed !== DEFAULT_SPEED && (
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => handleChange(DEFAULT_SPEED)}
        >
          {t("speech_speed_settings.reset")}
        </button>
      )}
      <button type="button" className="btn btn-secondary" onClick={preview}>
        {t("speech_speed_settings.preview")}
      </button>
    </div>
  );
}

export function SpeechSpeedSettings() {
  const { t } = useTranslation();
  const { languageCodes, isLoading } = useStudiedLanguages();
  const languagesQuery = useQuery({ queryKey: ["languages"], queryFn: CatalogApi.languages });
  const displayName = (code: string) =>
    languagesQuery.data?.find((lang) => lang.code === code)?.native_name ?? code;

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>{t("speech_speed_settings.title")}</h2>
      <p className="muted" style={{ marginBottom: 16 }}>
        {t("speech_speed_settings.description")}
      </p>
      {isLoading ? (
        <p className="muted">{t("speech_speed_settings.loading")}</p>
      ) : languageCodes.length === 0 ? (
        <p className="muted">{t("speech_speed_settings.no_languages")}</p>
      ) : (
        languageCodes.map((code) => (
          <LanguageSpeedRow key={code} languageCode={code} displayName={displayName(code)} />
        ))
      )}
    </div>
  );
}
