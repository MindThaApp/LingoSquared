import { useCallback, useEffect, useRef, useState } from "react";
import {
  MAX_RECORDING_MS,
  initialVoiceActivityState,
  rmsToLevel,
  stepVoiceActivity,
} from "./voiceActivity";

export type MicRecorderState = "idle" | "requesting" | "recording" | "stopping";

// Why the recorder ended on its own (manual stop()/cancel() never fire this).
export type MicAutoStopReason = "silence" | "max" | "no_speech";

const ANALYSE_INTERVAL_MS = 50;

// Set once the browser reports the user denied mic access, so every mic
// button hides for the rest of the session instead of re-prompting.
let micBlockedForSession = false;
export function micPermissionBlocked(): boolean {
  return micBlockedForSession;
}

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
    (typeof window === "undefined" || window.isSecureContext !== false) &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== "undefined"
  );
}

// Thin MediaRecorder wrapper: request the mic, record until stop() is
// called, resolve with the recorded Blob. Mirrors the SpeakButton/speak()
// "honest fallback" pattern — permission denial or an unsupported browser
// surfaces as `permissionDenied`/`unsupported` for the caller to act on
// (switch back to typed mode) rather than throwing into the void.
export function useMicRecorder(options?: { onAutoStop?: (reason: MicAutoStopReason) => void }) {
  const [state, setState] = useState<MicRecorderState>("idle");
  // 0..1 live input level from the analyser (0 when no analyser available).
  const [level, setLevel] = useState(0);
  const onAutoStopRef = useRef(options?.onAutoStop);
  onAutoStopRef.current = options?.onAutoStop;
  const monitorRef = useRef<{ teardown: () => void } | null>(null);
  const [permissionDenied, setPermissionDenied] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const teardownMonitor = useCallback(() => {
    monitorRef.current?.teardown();
    monitorRef.current = null;
    setLevel(0);
  }, []);

  // Voice-activity monitor: an AnalyserNode RMS sampled on an interval feeds
  // the pure state machine. The max-duration timer runs even if Web Audio is
  // unavailable (manual stop + max cap only in that case).
  const startMonitor = useCallback((stream: MediaStream) => {
    let fired = false;
    let ctx: AudioContext | null = null;
    let source: MediaStreamAudioSourceNode | null = null;
    let interval: ReturnType<typeof setInterval> | null = null;
    let maxTimer: ReturnType<typeof setTimeout> | null = null;
    const teardown = () => {
      fired = true;
      if (interval) clearInterval(interval);
      if (maxTimer) clearTimeout(maxTimer);
      try { source?.disconnect(); } catch { /* already disconnected */ }
      if (ctx && ctx.state !== "closed") void ctx.close().catch(() => {});
      ctx = null;
      source = null;
    };
    const fire = (reason: MicAutoStopReason) => {
      if (fired) return;
      teardown();
      monitorRef.current = null;
      setLevel(0);
      onAutoStopRef.current?.(reason);
    };
    monitorRef.current = { teardown };
    maxTimer = setTimeout(() => fire("max"), MAX_RECORDING_MS + 250);

    const Ctor: typeof AudioContext | undefined =
      typeof AudioContext !== "undefined"
        ? AudioContext
        : (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return;
    try {
      ctx = new Ctor();
      source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      source.connect(analyser);
      const buffer = new Float32Array(analyser.fftSize);
      let vad = initialVoiceActivityState(Date.now());
      interval = setInterval(() => {
        if (fired) return;
        analyser.getFloatTimeDomainData(buffer);
        let sum = 0;
        for (let i = 0; i < buffer.length; i++) sum += buffer[i] * buffer[i];
        const rms = Math.sqrt(sum / buffer.length);
        setLevel(rmsToLevel(rms));
        const result = stepVoiceActivity(vad, { rms, nowMs: Date.now() });
        vad = result.state;
        if (result.action === "stop") fire("silence");
        else if (result.action === "max") fire("max");
        else if (result.action === "no_speech") fire("no_speech");
      }, ANALYSE_INTERVAL_MS);
    } catch {
      // Web Audio failed to initialise — manual stop + max timer only.
      if (interval) clearInterval(interval);
      try { source?.disconnect(); } catch { /* ignore */ }
      if (ctx && ctx.state !== "closed") void ctx.close().catch(() => {});
      ctx = null;
      source = null;
    }
  }, []);

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
      startMonitor(stream);
      setState("recording");
      return true;
    } catch (err) {
      const name = (err as { name?: string } | null)?.name;
      if (name === "NotAllowedError" || name === "SecurityError") micBlockedForSession = true;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      // NotAllowedError (permission denied), NotFoundError (no mic), or
      // any other getUserMedia failure — all treated the same: degrade to
      // typed input rather than surfacing a raw browser error.
      setPermissionDenied(true);
      setState("idle");
      return false;
    }
  }, [startMonitor]);

  const stop = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = recorderRef.current;
      if (!recorder || recorder.state === "inactive") {
        resolve(null);
        return;
      }
      teardownMonitor();
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
  }, [teardownMonitor]);

  const cancel = useCallback(() => {
    teardownMonitor();
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
  }, [teardownMonitor]);

  // Release the mic stream/recorder if the host component unmounts mid-recording.
  const cancelRef = useRef(cancel);
  cancelRef.current = cancel;
  useEffect(() => () => cancelRef.current(), []);

  return { state, level, permissionDenied, start, stop, cancel };
}
