// Runs entirely off the main thread — WASM Whisper inference is heavy
// enough to freeze the UI otherwise. Talks to lib/whisperClient.ts via
// postMessage; never touches the network except to fetch the model
// weights themselves (cached by the browser after first load).
import { pipeline, env, type AutomaticSpeechRecognitionPipeline } from "@huggingface/transformers";

// Never let this fall back to trying local /models/ paths in a worker —
// there's nothing there; always fetch from the Hugging Face CDN (which is
// itself browser-cached across page loads).
env.allowLocalModels = false;

// onnx-community's export — actively maintained alongside current
// transformers.js versions (Xenova/* repos predate the v3 rewrite and
// behave identically for this bug, so this is not what fixed it — see
// below).
const MODEL_ID = "onnx-community/whisper-tiny";

// dtype MUST be "fp32" here — do not "optimize" this back to a quantized
// dtype without re-reading this. Verified live 2026-07-06: EVERY quantized
// merged-decoder variant of whisper-tiny (dtype "q8"/"int8", both Xenova's
// and onnx-community's exports) throws at session-creation time in
// onnxruntime-web ("Can't create a session... Missing required scale ...
// weight_transposed_DequantizeLinear" — a MatMulNBits/QDQ graph bug, not a
// stale export). "fp16" hits a DIFFERENT session-creation bug in the same
// runtime (LayerNormFusion: "Attempting to get index by a name which does
// not exist: InsertedPrecisionFreeCast_..."). Only "fp32" (no quantization,
// no precision-cast fusion) creates a working session — confirmed
// transcribing real synthesized speech correctly end-to-end. This is a
// genuine upstream onnxruntime-web/transformers.js compatibility ceiling
// for this model architecture at the currently pinned package version, not
// something fixable from this codebase. Costs ~150MB of one-time,
// browser-cached download instead of quantized dtypes' ~40-75MB — the
// real, accepted trade-off for a working client-side path today.
const WHISPER_DTYPE = "fp32";

type TranscribeRequest = {
  type: "transcribe";
  id: number;
  audio: Float32Array;
  language?: string;
};

type WorkerRequest = TranscribeRequest;

type TranscribeResponse =
  | { type: "ready" }
  | { type: "result"; id: number; ok: true; transcript: string }
  | { type: "result"; id: number; ok: false; error: string };

let transcriberPromise: Promise<AutomaticSpeechRecognitionPipeline> | null = null;

function getTranscriber() {
  if (!transcriberPromise) {
    // device: "wasm" so behavior is identical across every browser/device
    // that supports WebAssembly at all — WebGPU support is far less
    // universal, and the whole point of the client-side path is running
    // everywhere without a server round-trip.
    transcriberPromise = pipeline("automatic-speech-recognition", MODEL_ID, {
      dtype: WHISPER_DTYPE,
      device: "wasm",
    }) as Promise<AutomaticSpeechRecognitionPipeline>;
  }
  return transcriberPromise;
}

self.onmessage = async (event: MessageEvent<WorkerRequest>) => {
  const message = event.data;
  if (message.type !== "transcribe") return;
  const { id, audio, language } = message;
  try {
    const transcriber = await getTranscriber();
    const output = await transcriber(audio, {
      language,
      task: "transcribe",
      chunk_length_s: 30,
    });
    const result = Array.isArray(output) ? output[0] : output;
    const text = typeof result?.text === "string" ? result.text.trim() : "";
    const response: TranscribeResponse = { type: "result", id, ok: true, transcript: text };
    self.postMessage(response);
  } catch (err) {
    const response: TranscribeResponse = {
      type: "result",
      id,
      ok: false,
      error: err instanceof Error ? err.message : String(err),
    };
    self.postMessage(response);
  }
};
