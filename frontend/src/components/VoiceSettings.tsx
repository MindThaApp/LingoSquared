import { useEffect, useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { CatalogApi } from "@lingo/shared/api/endpoints";
import { BROWSER_TTS_LANG } from "../api/tts";
import { getVoicePreference, setVoicePreference } from "../lib/voicePreferences";
import { SAMPLE_SPEECH_TEXT as SAMPLE_TEXT } from "@lingo/shared/lib/sampleSpeechText";

function useBrowserVoices(): SpeechSynthesisVoice[] {
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);

  useEffect(() => {
    if (!("speechSynthesis" in window)) return;
    const load = () => setVoices(window.speechSynthesis.getVoices());
    load();
    window.speechSynthesis.addEventListener("voiceschanged", load);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", load);
  }, []);

  return voices;
}

function voicesForLanguage(voices: SpeechSynthesisVoice[], languageCode: string): SpeechSynthesisVoice[] {
  const tag = BROWSER_TTS_LANG[languageCode];
  const primarySubtag = (tag ?? languageCode).split("-")[0].toLowerCase();
  return voices.filter((voice) => voice.lang.toLowerCase().startsWith(primarySubtag));
}

function LanguageVoiceRow({
  languageCode,
  displayName,
  voices,
}: {
  languageCode: string;
  displayName: string;
  voices: SpeechSynthesisVoice[];
}) {
  const { t } = useTranslation();
  const [selected, setSelected] = useState(() => getVoicePreference(languageCode) ?? "");
  const uid = useId();
  const nameId = `${uid}-name`;
  const available = voicesForLanguage(voices, languageCode);

  const handleChange = (voiceURI: string) => {
    setSelected(voiceURI);
    setVoicePreference(languageCode, voiceURI || null);
  };

  const preview = () => {
    if (!("speechSynthesis" in window)) return;
    const utterance = new SpeechSynthesisUtterance(SAMPLE_TEXT[languageCode] ?? displayName);
    utterance.lang = BROWSER_TTS_LANG[languageCode] ?? languageCode;
    const match = available.find((voice) => voice.voiceURI === selected);
    if (match) utterance.voice = match;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
      <span id={nameId} lang={languageCode} style={{ minWidth: 90 }}>
        {displayName}
      </span>
      {available.length === 0 ? (
        <span className="muted" style={{ fontSize: "0.85rem" }}>
          {t("voice_settings.no_voices")}
        </span>
      ) : (
        <>
          <select
            aria-labelledby={nameId}
            value={selected}
            onChange={(e) => handleChange(e.target.value)}
            style={{ flex: 1 }}
          >
            <option value="">{t("voice_settings.system_default")}</option>
            {available.map((voice) => (
              <option key={voice.voiceURI} value={voice.voiceURI}>
                {voice.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            id={`${uid}-preview`}
            aria-labelledby={`${uid}-preview ${nameId}`}
            className="btn btn-secondary"
            onClick={preview}
          >
            {t("voice_settings.preview")}
          </button>
        </>
      )}
    </div>
  );
}

export function VoiceSettings() {
  const { t } = useTranslation();
  const voices = useBrowserVoices();
  const languagesQuery = useQuery({ queryKey: ["languages"], queryFn: CatalogApi.languages });

  if (!("speechSynthesis" in window)) {
    return (
      <div className="card">
        <h2 style={{ marginTop: 0 }}>{t("voice_settings.title")}</h2>
        <p className="muted">{t("voice_settings.unsupported")}</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>{t("voice_settings.title")}</h2>
      <p className="muted" style={{ marginBottom: 16 }}>
        {t("voice_settings.description")}
      </p>
      {languagesQuery.data?.map((lang) => (
        <LanguageVoiceRow
          key={lang.code}
          languageCode={lang.code}
          displayName={lang.native_name}
          voices={voices}
        />
      ))}
    </div>
  );
}
