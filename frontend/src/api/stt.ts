const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Server-side fallback only — called when the client reports client-side
// WASM transcription isn't usable. Raw audio goes over the wire here (it
// doesn't for the client-side path), which is exactly why this is the
// fallback and not the default.
export async function transcribeViaServer(audioBlob: Blob, languageCode: string): Promise<string> {
  const { transcript } = await transcribeViaServerDetailed(audioBlob, languageCode, false);
  return transcript;
}

export type SpokenWord = {
  word: string;
  start: number;
  end: number;
  probability: number;
};

export type ServerTranscription = {
  transcript: string;
  words?: SpokenWord[];
};

// `detail=words` asks the backend for faster-whisper's per-word output.
// `probability` is the model's confidence in each word — the pronunciation
// signal. It is a CLARITY heuristic, not phoneme-level accent scoring, and
// the UI must not present it as one.
export async function transcribeViaServerDetailed(
  audioBlob: Blob,
  languageCode: string,
  withWords = true,
): Promise<ServerTranscription> {
  const token = localStorage.getItem("access_token");
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const form = new FormData();
  form.append("language_code", languageCode);
  form.append("audio", audioBlob, "recording");
  if (withWords) form.append("detail", "words");

  const response = await fetch(`${BASE_URL}/stt/transcribe`, {
    method: "POST",
    headers,
    body: form,
  });
  if (!response.ok) {
    throw new Error(`stt_transcribe_failed_${response.status}`);
  }
  return (await response.json()) as ServerTranscription;
}
