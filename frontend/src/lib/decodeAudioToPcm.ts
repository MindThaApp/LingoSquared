// Whisper expects mono 16kHz PCM. The Web Audio API (AudioContext) only
// exists on the main thread, not inside a Worker — so decoding happens
// here, and only the resulting Float32Array (a transferable) crosses over
// to the transcription worker, not the compressed blob.
export async function decodeAudioToPcm16k(blob: Blob): Promise<Float32Array> {
  const AudioContextCtor =
    window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioContextCtor) {
    throw new Error("audio_decoding_unsupported");
  }
  const arrayBuffer = await blob.arrayBuffer();
  const audioContext = new AudioContextCtor({ sampleRate: 16000 });
  try {
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
