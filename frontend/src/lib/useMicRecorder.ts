import { useCallback, useEffect, useRef, useState } from "react";

export type MicRecorderState = "idle" | "requesting" | "recording" | "stopping";

const MIME_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
];

function pickSupportedMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) return undefined;
  return MIME_CANDIDATES.find((candidate) => MediaRecorder.isTypeSupported(candidate));
}

// True only if every API this hook needs actually exists on this device/
// browser — checked once up front so callers can decide to skip straight
// to the typed fallback instead of letting getUserMedia throw later.
export function micRecordingSupported(): boolean {
  return (
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== "undefined"
  );
}

// Thin MediaRecorder wrapper: request the mic, record until stop() is
// called, resolve with the recorded Blob. Mirrors the SpeakButton/speak()
// "honest fallback" pattern — permission denial or an unsupported browser
// surfaces as `permissionDenied`/`unsupported` for the caller to act on
// (switch back to typed mode) rather than throwing into the void.
export function useMicRecorder() {
  const [state, setState] = useState<MicRecorderState>("idle");
  const [permissionDenied, setPermissionDenied] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const start = useCallback(async (): Promise<boolean> => {
    if (!micRecordingSupported()) {
      setPermissionDenied(true);
      return false;
    }
    setPermissionDenied(false);
    setState("requesting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mimeType = pickSupportedMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorderRef.current = recorder;
      recorder.start();
      setState("recording");
      return true;
    } catch {
      // NotAllowedError (permission denied), NotFoundError (no mic), or
      // any other getUserMedia failure — all treated the same: degrade to
      // typed input rather than surfacing a raw browser error.
      setPermissionDenied(true);
      setState("idle");
      return false;
    }
  }, []);

  const stop = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = recorderRef.current;
      if (!recorder || recorder.state === "inactive") {
        resolve(null);
        return;
      }
      setState("stopping");
      recorder.onstop = () => {
        const blob = chunksRef.current.length
          ? new Blob(chunksRef.current, { type: recorder.mimeType })
          : null;
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        recorderRef.current = null;
        setState("idle");
        resolve(blob);
      };
      recorder.stop();
    });
  }, []);

  const cancel = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.onstop = null;
      recorder.stop();
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
    chunksRef.current = [];
    setState("idle");
  }, []);

  // Release the mic stream/recorder if the host component unmounts mid-recording.
  const cancelRef = useRef(cancel);
  cancelRef.current = cancel;
  useEffect(() => () => cancelRef.current(), []);

  return { state, permissionDenied, start, stop, cancel };
}
