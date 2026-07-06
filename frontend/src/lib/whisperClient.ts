import { decodeAudioToPcm16k } from "./decodeAudioToPcm";

// Dari (prs) has no distinct Whisper training language — Farsi is the
// closest available hint. A real accuracy caveat (transcripts may lean
// Farsi spelling/vocabulary), not a bug; the backend fallback (app/
// services/stt.py) makes the identical choice for the same reason.
const WHISPER_LANGUAGE_HINT: Record<string, string> = {
  en: "en", nl: "nl", fr: "fr", de: "de", it: "it",
  es: "es", ru: "ru", zh: "zh", fa: "fa", prs: "fa",
};

// Feature-detect everything the client-side path needs BEFORE attempting
// it, so callers can skip straight to the server fallback instead of
// eating a slow failure. WebAssembly threads specifically need cross-
// origin isolation (SharedArrayBuffer) for full speed but the pipeline
// still runs (single-threaded, slower) without it — only true WebAssembly/
// Worker/AudioContext absence is disqualifying.
export function clientTranscriptionSupported(): boolean {
  return (
    typeof WebAssembly === "object" &&
    typeof Worker !== "undefined" &&
    (typeof AudioContext !== "undefined" ||
      typeof (window as unknown as { webkitAudioContext?: unknown }).webkitAudioContext !== "undefined")
  );
}

let worker: Worker | null = null;
let nextRequestId = 1;
const pending = new Map<number, { resolve: (text: string) => void; reject: (err: Error) => void }>();

function getWorker(): Worker {
  if (!worker) {
    worker = new Worker(new URL("../workers/whisperWorker.ts", import.meta.url), { type: "module" });
    worker.onmessage = (event: MessageEvent) => {
      const message = event.data;
      if (message?.type !== "result") return;
      const entry = pending.get(message.id);
      if (!entry) return;
      pending.delete(message.id);
      if (message.ok) entry.resolve(message.transcript);
      else entry.reject(new Error(message.error));
    };
    worker.onerror = (event) => {
      // A worker-level error (e.g. failed to even load the module) fails
      // every still-pending request rather than hanging them forever.
      for (const [id, entry] of pending) {
        entry.reject(new Error(event.message || "whisper_worker_error"));
        pending.delete(id);
      }
    };
  }
  return worker;
}

// Model load + first inference can genuinely take a while on a slow
// connection/device — the fp32 model (~150MB, see whisperWorker.ts for why
// fp32 specifically is required) is only downloaded once and then browser-
// cached, but that first download needs real headroom. Generous but
// finite, so a truly stuck load still falls back to the server path
// instead of leaving the learner staring at a spinner forever.
const TRANSCRIBE_TIMEOUT_MS = 90_000;

export async function transcribeClientSide(audioBlob: Blob, languageCode: string): Promise<string> {
  if (!clientTranscriptionSupported()) {
    throw new Error("client_transcription_unsupported");
  }
  const pcm = await decodeAudioToPcm16k(audioBlob);
  const language = WHISPER_LANGUAGE_HINT[languageCode] ?? languageCode;
  const id = nextRequestId++;
  const workerInstance = getWorker();

  return new Promise<string>((resolve, reject) => {
    const timeout = setTimeout(() => {
      pending.delete(id);
      reject(new Error("client_transcription_timed_out"));
    }, TRANSCRIBE_TIMEOUT_MS);

    pending.set(id, {
      resolve: (text) => {
        clearTimeout(timeout);
        resolve(text);
      },
      reject: (err) => {
        clearTimeout(timeout);
        reject(err);
      },
    });

    workerInstance.postMessage({ type: "transcribe", id, audio: pcm, language }, [pcm.buffer]);
  });
}
