import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  getAutoPlayAnswer,
  getFeedbackCues,
  setAutoPlayAnswer,
  setFeedbackCues,
} from "../lib/feedbackPreferences";

/** Profile card: answer-feedback toggles (auto-play correct answer, sound/vibration cues). */
export function FeedbackSettings() {
  const { t } = useTranslation();
  const uid = useId();
  const [autoPlay, setAutoPlay] = useState(getAutoPlayAnswer);
  const [cues, setCues] = useState(getFeedbackCues);
  return (
    <div className="card" style={{ marginTop: 16 }}>
      <h3 style={{ marginTop: 0 }}>{t("feedback.settings_title")}</h3>
      <label htmlFor={`${uid}-ap`} style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10 }}>
        <input
          id={`${uid}-ap`}
          type="checkbox"
          checked={autoPlay}
          onChange={(e) => {
            setAutoPlay(e.target.checked);
            setAutoPlayAnswer(e.target.checked);
          }}
        />
        <span>{t("feedback.autoplay_label")}</span>
      </label>
      <label htmlFor={`${uid}-cue`} style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <input
          id={`${uid}-cue`}
          type="checkbox"
          checked={cues}
          onChange={(e) => {
            setCues(e.target.checked);
            setFeedbackCues(e.target.checked);
          }}
        />
        <span>{t("feedback.cues_label")}</span>
      </label>
      <p className="muted" style={{ margin: "8px 0 0", fontSize: "0.85rem" }}>{t("feedback.settings_hint")}</p>
    </div>
  );
}
