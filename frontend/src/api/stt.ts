const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Server-side fallback only — called when the client reports client-side
// WASM transcription isn't usable. Raw audio goes over the wire here (it
// doesn't for the client-side path), which is exactly why this is the
// fallback and not the default.
export async function transcribeViaServer(audioBlob: Blob, languageCode: string): Promise<string> {
  const token = localStorage.getItem("access_token");
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const form = new FormData();
  form.append("language_code", languageCode);
  form.append("audio", audioBlob, "recording");

  const response = await fetch(`${BASE_URL}/stt/transcribe`, {
    method: "POST",
    headers,
    body: form,
  });
  if (!response.ok) {
    throw new Error(`stt_transcribe_failed_${response.status}`);
  }
  const body: { transcript: string } = await response.json();
  return body.transcript;
}
