// Whisper expects mono 16kHz PCM. The Web Audio API (AudioContext) only
// exists on the main thread, not inside a Worker — so decoding happens
// here, and only the resulting Float32Array (a transferable) crosses over
// to the transcription worker, not the compressed blob.

// Thrown when the browser ignores the requested 16kHz sample rate: prefixed
// webkitAudioContext ignores the constructor options bag entirely, and some
// devices silently clamp to the hardware rate (44.1/48kHz). Without this
// check the decoded PCM would be handed to Whisper labeled as 16kHz while
// actually being ~3x that rate — producing garbage transcripts with no
// error anywhere (the audio just sounds ~3x slow to the model). Throwing a
// clearly-named error here makes the caller's existing try/catch fall
// through to the server STT path instead of silently grading a garbage
// transcript as the learner's answer.
export class AudioSampleRateMismatchError extends Error {
  constructor(actualSampleRate: number) {
    super(
      `audio_sample_rate_mismatch: requested 16000Hz but AudioContext runs at ${actualSampleRate}Hz`,
    );
    this.name = "AudioSampleRateMismatchError";
  }
}

export async function decodeAudioToPcm16k(blob: Blob): Promise<Float32Array> {
  const AudioContextCtor =
    window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioContextCtor) {
    throw new Error("audio_decoding_unsupported");
  }
  const arrayBuffer = await blob.arrayBuffer();
  const audioContext = new AudioContextCtor({ sampleRate: 16000 });
  try {
    // Inside the try so the finally still closes the context on mismatch.
    if (audioContext.sampleRate !== 16000) {
      throw new AudioSampleRateMismatchError(audioContext.sampleRate);
    }
    const decoded = await audioContext.decodeAudioData(arrayBuffer);
    if (decoded.numberOfChannels === 1) {
      return decoded.getChannelData(0).slice();
    }
    const mixed = new Float32Array(decoded.length);
    for (let channel = 0; channel < decoded.numberOfChannels; channel++) {
      const data = decoded.getChannelData(channel);
      for (let i = 0; i < decoded.length; i++) {
        mixed[i] += data[i] / decoded.numberOfChannels;
      }
    }
    return mixed;
  } finally {
    void audioContext.close();
  }
}
