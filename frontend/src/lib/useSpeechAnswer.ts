import { useCallback, useState } from "react";
import { getAnswerInputMode, setAnswerInputMode, type AnswerInputMode } from "@lingo/shared/lib/answerInputMode";
import { micRecordingSupported, useMicRecorder } from "./useMicRecorder";
import { clientTranscriptionSupported, transcribeClientSide } from "./whisperClient";
import { transcribeViaServer } from "../api/stt";

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
export function useSpeechAnswer(languageCode: string, onTranscript: (text: string) => void) {
  const [mode, setModeState] = useState<AnswerInputMode>(() => getAnswerInputMode());
  const [status, setStatus] = useState<SpeechAnswerStatus>("idle");
  const [error, setError] = useState<SpeechAnswerErrorCode | null>(null);
  const recorder = useMicRecorder();

  const setMode = useCallback((next: AnswerInputMode) => {
    setModeState(next);
    setAnswerInputMode(next);
    setError(null);
  }, []);

  const beginRecording = useCallback(async () => {
    setError(null);
    if (!micRecordingSupported()) {
      setMode("type");
      setError("mic_unsupported");
      return;
    }
    const started = await recorder.start();
    if (!started) {
      // Covers permission denial, no device found, or any other
      // getUserMedia failure — degrade to typing, don't retry silently.
      setMode("type");
      setError("mic_permission_denied");
      return;
    }
    setStatus("recording");
  }, [recorder, setMode]);

  const finishRecording = useCallback(async () => {
    const blob = await recorder.stop();
    if (!blob || blob.size === 0) {
      setStatus("error");
      setError("recording_empty");
      return;
    }
    setStatus("transcribing");
    try {
      let transcript: string;
      try {
        if (!clientTranscriptionSupported()) throw new Error("client_transcription_unsupported");
        transcript = await transcribeClientSide(blob, languageCode);
      } catch {
        transcript = await transcribeViaServer(blob, languageCode);
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

  const cancelRecording = useCallback(() => {
    recorder.cancel();
    setStatus("idle");
    setError(null);
  }, [recorder]);

  return {
    mode,
    setMode,
    status,
    error,
    beginRecording,
    finishRecording,
    cancelRecording,
  };
}
