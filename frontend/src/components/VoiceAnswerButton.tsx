import { useTranslation } from "react-i18next";
import type { Exercise } from "@lingo/shared/api/types";
import { useTargetLanguage } from "./targetLanguageContext";
import { micPermissionBlocked, micRecordingSupported } from "../lib/useMicRecorder";
import { useSpeechAnswer } from "../lib/useSpeechAnswer";
import { voiceAnswerEligible } from "../lib/voiceAnswer";

// Live input-level bar driven by the analyser RMS (0..1). Decorative — the
// spoken/announced state lives in the aria-live status next to it. Not
// animated by CSS, so reduced-motion users still see level but no pulse.
export function MicLevelMeter({ level }: { level: number }) {
  return (
    <span className="mic-meter" aria-hidden="true">
      <span className="mic-meter__fill" style={{ transform: `scaleX(${level})` }} />
    </span>
  );
}

// Inline mic button for typed-answer exercises. Records with auto-stop,
// transcribes in the answer language and FILLS the caller's input via
// onTranscript — it never submits. Renders nothing when mic recording is
// unsupported, the answer isn't in the language being studied, or the
// learner denied mic access.
export function VoiceAnswerButton({
  exercise,
  onTranscript,
  disabled,
}: {
  exercise: Exercise;
  onTranscript: (text: string) => void;
  disabled: boolean;
}) {
  const answerLanguageCode = exercise.prompt.answer_language_code;
  const targetLanguage = useTargetLanguage();
  const eligible = voiceAnswerEligible(answerLanguageCode, targetLanguage);
  return eligible && answerLanguageCode ? (
    <VoiceAnswerButtonInner languageCode={answerLanguageCode} onTranscript={onTranscript} disabled={disabled} />
  ) : null;
}

function VoiceAnswerButtonInner({
  languageCode,
  onTranscript,
  disabled,
}: {
  languageCode: string;
  onTranscript: (text: string) => void;
  disabled: boolean;
}) {
  const { t } = useTranslation();
  const { status, error, level, beginRecording, finishRecording } = useSpeechAnswer(
    languageCode,
    onTranscript,
    { persistMode: false },
  );

  if (!micRecordingSupported() || micPermissionBlocked() || error === "mic_permission_denied" || error === "mic_unsupported") {
    return null;
  }

  const recording = status === "recording";
  const transcribing = status === "transcribing";
  const label = recording
    ? t("voice_answer.inline_stop")
    : transcribing
      ? t("voice_answer.transcribing")
      : t("voice_answer.inline_start");

  return (
    <div className="voice-answer">
      <button
        type="button"
        className={`btn-icon-toggle voice-answer__btn${recording ? " is-recording" : ""}`}
        aria-pressed={recording}
        aria-label={label}
        title={label}
        disabled={disabled || transcribing}
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => (recording ? finishRecording() : beginRecording())}
      >
        <span aria-hidden="true">🎙️</span>
      </button>
      {recording && <MicLevelMeter level={level} />}
      <span className="voice-answer__status muted" role="status" aria-live="polite">
        {recording
          ? t("voice_answer.listening")
          : transcribing
            ? t("voice_answer.transcribing")
            : error
              ? t(`voice_answer.error_${error}`)
              : ""}
      </span>
    </div>
  );
}
