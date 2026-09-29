import { useTranslation } from "react-i18next";
import { micRecordingSupported } from "../lib/useMicRecorder";
import { useSpeechAnswer } from "../lib/useSpeechAnswer";
import { PronunciationFeedback } from "./PronunciationFeedback";
import { MicLevelMeter } from "./VoiceAnswerButton";
import type { AnswerInputMode } from "@lingo/shared/lib/answerInputMode";

// Shared mic/keyboard toggle + record/transcribe UI for speak_response and
// speak_repeat. Deliberately NOT a text-field replacement — it just feeds
// transcript text into the same controlled `value` the caller's existing
// <input> already uses, so every exercise component keeps its own
// input/virtual-keyboard/submit-button code unchanged.
export function VoiceCaptureControls({
  languageCode,
  onTranscript,
  disabled,
}: {
  languageCode: string;
  onTranscript: (text: string) => void;
  disabled: boolean;
}) {
  const { t } = useTranslation();
  const { mode, setMode, status, error, words, level, beginRecording, finishRecording, cancelRecording } =
    useSpeechAnswer(languageCode, onTranscript);

  if (!micRecordingSupported()) {
    // No point offering a toggle that can only ever fail — this device/
    // browser has no MediaRecorder/getUserMedia at all.
    return null;
  }

  function handleModeClick(next: AnswerInputMode) {
    if (mode === "voice" && next === "type") cancelRecording();
    setMode(next);
  }

  return (
    <div className="voice-capture" style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 8 }}>
      <div style={{ display: "flex", gap: 6 }}>
        <button
          type="button"
          className="btn-icon-toggle"
          aria-pressed={mode === "voice"}
          disabled={disabled}
          onClick={() => handleModeClick("voice")}
          title={t("voice_answer.switch_to_voice")}
          aria-label={t("voice_answer.switch_to_voice")}
        >
          🎙️
        </button>
        <button
          type="button"
          className="btn-icon-toggle"
          aria-pressed={mode === "type"}
          disabled={disabled}
          onClick={() => handleModeClick("type")}
          title={t("voice_answer.switch_to_type")}
          aria-label={t("voice_answer.switch_to_type")}
        >
          ⌨️
        </button>
      </div>

      {mode === "voice" && (
        <button
          type="button"
          className={`btn btn-block${status === "recording" ? " is-recording" : ""}`}
          aria-pressed={status === "recording"}
          disabled={disabled || status === "transcribing"}
          onClick={() => (status === "recording" ? finishRecording() : beginRecording())}
        >
          {status === "recording"
            ? t("voice_answer.record_stop")
            : status === "transcribing"
              ? t("voice_answer.transcribing")
              : t("voice_answer.record_start")}
        </button>
      )}
      {status === "recording" && (
        <div className="voice-answer" role="status" aria-live="polite">
          <MicLevelMeter level={level} />
          <span className="muted">{t("voice_answer.listening")}</span>
        </div>
      )}
      {error && (
        // Rendered regardless of current mode — beginRecording() flips mode
        // back to "type" on permission denial/unsupported before this ever
        // renders, so the explanation must survive that mode switch, not
        // live only inside the voice-mode block.
        <p className="muted" role="alert" style={{ fontSize: "0.85rem" }}>
          {t(`voice_answer.error_${error}`)}
        </p>
      )}
      {/* Only the server STT path returns word confidences, so this is absent
          on the client-side WASM path. Absent means "no signal", never "your
          pronunciation was perfect" — the component renders nothing at all. */}
      <PronunciationFeedback words={words} />
    </div>
  );
}
