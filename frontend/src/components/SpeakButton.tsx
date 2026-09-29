import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { speak } from "../api/tts";

export function SpeakButton({
  text,
  languageCode,
  mediaAssetKey,
  autoPlay = false,
}: {
  text: string;
  languageCode: string;
  mediaAssetKey?: string;
  autoPlay?: boolean;
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

  // Autoplay once per mount. The ref guards StrictMode's double-invoked
  // effect; rejections (autoplay policy) are swallowed silently -- the
  // learner can still tap the button, and no "no voice" nag appears.
  const autoPlayed = useRef(false);
  useEffect(() => {
    if (!autoPlay || autoPlayed.current) return;
    autoPlayed.current = true;
    speak(text, languageCode, mediaAssetKey).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
