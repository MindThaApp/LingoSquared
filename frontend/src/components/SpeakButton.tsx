import { useState } from "react";
import { useTranslation } from "react-i18next";
import { speak } from "../api/tts";

export function SpeakButton({
  text,
  languageCode,
  mediaAssetKey,
}: {
  text: string;
  languageCode: string;
  mediaAssetKey?: string;
}) {
  const { t } = useTranslation();
  const [playing, setPlaying] = useState(false);
  const [unavailable, setUnavailable] = useState(false);

  async function handleClick() {
    if (playing) return;
    setPlaying(true);
    setUnavailable(false);
    try {
      const played = await speak(text, languageCode, mediaAssetKey);
      if (!played) setUnavailable(true);
    } finally {
      setPlaying(false);
    }
  }

  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <button
        type="button"
        className="speak-button"
        aria-label={t("speak.listen_label", { text })}
        onClick={handleClick}
        disabled={playing}
      >
        <span aria-hidden="true">🔊</span>
      </button>
      {unavailable && (
        <span className="muted" role="status" style={{ fontSize: "0.75rem" }}>
          {t("speak.no_voice_available")}
        </span>
      )}
    </span>
  );
}
