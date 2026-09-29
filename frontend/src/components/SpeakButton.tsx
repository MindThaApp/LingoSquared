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
    } catch {
      // speak() failed outright (sync throw or rejected promise): surface the
      // same honest "no voice" fallback instead of an unhandled rejection.
      setUnavailable(true);
    } finally {
      setPlaying(false);
    }
  }

  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <button
        type="button"
        className="speak-button"
        aria-label={t("speak.play_audio")}
        onClick={handleClick}
        disabled={playing}
      >
        🔊
      </button>
      {unavailable && (
        <span className="muted" style={{ fontSize: "0.75rem" }}>
          {t("speak.no_voice_available")}
        </span>
      )}
    </span>
  );
}
