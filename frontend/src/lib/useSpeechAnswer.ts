import { useCallback, useRef, useState } from "react";
import { getAnswerInputMode, setAnswerInputMode, type AnswerInputMode } from "@lingo/shared/lib/answerInputMode";
import { micRecordingSupported, useMicRecorder, type MicAutoStopReason } from "./useMicRecorder";
import { clientTranscriptionSupported, transcribeClientSide } from "./whisperClient";
import { transcribeViaServerDetailed, type SpokenWord } from "../api/stt";

export type SpeechAnswerStatus = "idle" | "recording" | "transcribing" | "error";

export type SpeechAnswerErrorCode =
  | "mic_unsupported"
  | "mic_permission_denied"
  | "recording_empty"
  | "no_speech_detected"
  | "transcription_failed";

// Orchestrates the whole speak-an-answer flow for speak_response/
// speak_repeat: mode toggle (persisted), MediaRecorder capture, then
// client-side WASM Whisper transcription with a self-hosted-server
// fallback — mirrors the SpeakButton/speak() "honest fallback, never
// silently dead" pattern used for TTS. onTranscript feeds the resulting
// text into the same controlled `value` state the typed-input path
// already uses, so submission/grading is completely unaffected.
//
// The recorder auto-stops (silence after speech / max length) and reports
// via onAutoStop; a no-speech timeout takes the existing no_speech_detected
// error path. `options.persistMode: false` stops a failure from flipping the
// persisted speak-exercise mic/keyboard preference (used by the inline mic
// button on typed-answer exercises, which has no such toggle).
export function useSpeechAnswer(
  languageCode: string,
  onTranscript: (text: string) => void,
  options?: { persistMode?: boolean },
) {
  const persistMode = options?.persistMode !== false;
  const [mode, setModeState] = useState<AnswerInputMode>(() => getAnswerInputMode());
  const [status, setStatus] = useState<SpeechAnswerStatus>("idle");
  const [error, setError] = useState<SpeechAnswerErrorCode | null>(null);
  // Per-word confidence for pronunciation feedback. Only the server path
  // returns it (the WASM model doesn't expose token probabilities), so it
  // stays null on the client path — the UI must treat it as optional, never
  // as "no feedback means perfect".
  const [words, setWords] = useState<SpokenWord[] | null>(null);
  const autoStopRef = useRef<(reason: MicAutoStopReason) => void>(() => {});
  const recorder = useMicRecorder({ onAutoStop: (reason) => autoStopRef.current(reason) });

  const setMode = useCallback((next: AnswerInputMode) => {
    setModeState(next);
    setAnswerInputMode(next);
    setError(null);
  }, []);

  const beginRecording = useCallback(async () => {
    setError(null);
    if (!micRecordingSupported()) {
      if (persistMode) setMode("type");
      setError("mic_unsupported");
      return;
    }
    const started = await recorder.start();
    if (!started) {
      // Covers permission denial, no device found, or any other
      // getUserMedia failure — degrade to typing, don't retry silently.
      if (persistMode) setMode("type");
      setError("mic_permission_denied");
      return;
    }
    setStatus("recording");
  }, [recorder, setMode, persistMode]);

  const finishRecording = useCallback(async () => {
    const blob = await recorder.stop();
    if (!blob || blob.size === 0) {
      setStatus("error");
      setError("recording_empty");
      return;
    }
    setStatus("transcribing");
    setWords(null);
    try {
      let transcript: string;
      try {
        if (!clientTranscriptionSupported()) throw new Error("client_transcription_unsupported");
        transcript = await transcribeClientSide(blob, languageCode);
      } catch {
        const detailed = await transcribeViaServerDetailed(blob, languageCode);
        transcript = detailed.transcript;
        setWords(detailed.words ?? null);
      }
      const trimmed = transcript.trim();
      if (!trimmed) {
        setStatus("error");
        setError("no_speech_detected");
        return;
      }
      onTranscript(trimmed);
      setStatus("idle");
    } catch {
      setStatus("error");
      setError("transcription_failed");
    }
  }, [recorder, languageCode, onTranscript]);

  autoStopRef.current = (reason) => {
    if (reason === "no_speech") {
      recorder.cancel();
      setStatus("error");
      setError("no_speech_detected");
      return;
    }
    void finishRecording();
  };

  const cancelRecording = useCallback(() => {
    recorder.cancel();
    setStatus("idle");
    setError(null);
    setWords(null);
  }, [recorder]);

  return {
    mode,
    setMode,
    status,
    error,
    words,
    level: recorder.level,
    beginRecording,
    finishRecording,
    cancelRecording,
  };
}
